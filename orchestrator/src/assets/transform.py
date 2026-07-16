import dagster as dg
import json

from collections.abc import Mapping, Iterable
from datetime import timedelta
from pathlib import Path
from typing import Any
from dagster_dbt import (
    DbtProject,
    DbtCliResource,
    dbt_assets,
    DagsterDbtTranslator,
)

from common.models.core import IngestionConfig
from assets.ingestion import IngestionAssetBuilder


DBT_PROJECT_PATH = Path(__file__).resolve().parents[2] / ".." / "transform"

dbt_project = DbtProject(
    project_dir=DBT_PROJECT_PATH,
    profiles_dir=DBT_PROJECT_PATH,
)
dbt_project.prepare_if_dev()


class CustomDagsterDbtTranslator(DagsterDbtTranslator):
    """Flatten dbt nodes to `{schema}_{name}` asset keys.

    - cleansed models  -> cleansed_noaa_ghcn_*
    - raw sources/seeds -> raw_noaa_ghcn_*   (matches the ingestion assets)
    """

    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> dg.AssetKey:
        schema = dbt_resource_props.get("schema")
        # Prefer alias (the relation name) over the dbt resource name, so models
        # renamed to avoid dbt name collisions still map to the intended key.
        name = dbt_resource_props.get("alias") or dbt_resource_props["name"]
        if schema:
            return dg.AssetKey(f"{schema}_{name}")
        return super().get_asset_key(dbt_resource_props)

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        return dbt_resource_props.get("schema")

    def get_automation_condition(
        self, dbt_resource_props: Mapping[str, Any]
    ) -> dg.AutomationCondition | None:
        # Run a cleansed model only when an upstream (raw ingestion / seed)
        # actually materialized new data — not on a blind schedule.
        return dg.AutomationCondition.eager()


translator = CustomDagsterDbtTranslator()


def _raw_partitions(
    ingestion_configs: list[IngestionConfig],
) -> dict[str, dg.PartitionsDefinition]:
    """raw ingestion asset key -> PartitionsDefinition, for every partitioned
    source table. dbt models inherit their raw parent's partitioning from this
    map, so the ingestion config (configuration/ingestion/*.yml) stays the single
    source of truth."""
    partitions: dict[str, dg.PartitionsDefinition] = {}
    for config in ingestion_configs:
        s3_config = config.s3_config
        if not s3_config:
            continue
        for table in s3_config.tables:
            partitions_def = IngestionAssetBuilder.build_partitions_def(table.partitions)
            if partitions_def is not None:
                partitions[f"raw_{config.name}_{table.name}"] = partitions_def
    return partitions


def _partitioned_cleansed_models(
    raw_partitions: Mapping[str, dg.PartitionsDefinition],
) -> list[tuple[str, dg.PartitionsDefinition]]:
    """Discover which dbt models are partitioned by reading the manifest: a model
    inherits the PartitionsDefinition of the raw source it reads from, if that
    source is partitioned in the ingestion config. No dataset names hardcoded.
    """
    manifest = json.loads(Path(dbt_project.manifest_path).read_text())
    # dbt source unique_id -> ingestion asset key (raw_<schema>_<name> style)
    source_key = {
        uid: f"{s['schema']}_{s['name']}"
        for uid, s in manifest["sources"].items()
    }

    result: list[tuple[str, dg.PartitionsDefinition]] = []
    for node in manifest["nodes"].values():
        if node["resource_type"] != "model":
            continue
        # Partition propagation is scoped to the cleansed layer, which reads the
        # raw sources directly (1:1 with the raw partitioning). Models in other
        # layers stay unpartitioned even if they descend from a partitioned raw.
        if not node.get("original_file_path", "").startswith("models/cleansed/"):
            continue
        pdefs = [
            raw_partitions[key]
            for parent in node["depends_on"]["nodes"]
            if (key := source_key.get(parent, "")) in raw_partitions
        ]
        if not pdefs:
            continue
        if any(pd != pdefs[0] for pd in pdefs[1:]):
            raise ValueError(
                f"Model '{node['name']}' reads sources with differing partitions"
            )
        result.append((node["name"], pdefs[0]))
    return result


def _build_cleansed_assets(
    select: str, partitions_def: dg.PartitionsDefinition, name: str
) -> dg.AssetsDefinition:
    @dbt_assets(
        manifest=dbt_project.manifest_path,
        dagster_dbt_translator=translator,
        select=select,
        partitions_def=partitions_def,
        name=name,
    )
    def _assets(context: dg.AssetExecutionContext, dbt: DbtCliResource) -> Iterable:
        window = context.partition_time_window
        start_ds = window.start.strftime("%Y-%m-%d")
        end_ds = (window.end - timedelta(days=1)).strftime("%Y-%m-%d")
        dbt_vars = json.dumps({"start_ds": start_ds, "end_ds": end_ds})
        yield from dbt.cli(["build", "--vars", dbt_vars], context=context).stream()

    return _assets


def build_transform_assets(
    ingestion_configs: list[IngestionConfig],
) -> list[dg.AssetsDefinition]:
    raw_partitions = _raw_partitions(ingestion_configs)
    partitioned_cleansed = _partitioned_cleansed_models(raw_partitions)

    # Bucket partitioned models by their PartitionsDefinition: each distinct
    # partitioning needs its own @dbt_assets (a multi-asset carries one def).
    buckets: list[tuple[dg.PartitionsDefinition, list[str]]] = []
    for model_name, pdef in partitioned_cleansed:
        for existing_pdef, names in buckets:
            if existing_pdef == pdef:
                names.append(model_name)
                break
        else:
            buckets.append((pdef, [model_name]))

    partitioned_cleansed_names = [name for name, _ in partitioned_cleansed]

    @dbt_assets(
        manifest=dbt_project.manifest_path,
        dagster_dbt_translator=translator,
        exclude=" ".join(partitioned_cleansed_names),
    )
    def transform_assets(
        context: dg.AssetExecutionContext, dbt: DbtCliResource
    ) -> Iterable:
        yield from dbt.cli(["build"], context=context).stream()

    assets: list[dg.AssetsDefinition] = [transform_assets]
    for i, (pdef, names) in enumerate(buckets):
        assets.append(
            _build_cleansed_assets(
                select=" ".join(names),
                partitions_def=pdef,
                name=f"transform_cleansed_assets_{i}",
            )
        )
    return assets
