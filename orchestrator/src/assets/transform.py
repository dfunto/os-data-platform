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


DBT_PROJECT_PATH = Path(__file__).resolve().parents[2] / ".." / "transform"

# The one incremental / partitioned model. Everything else is unpartitioned.
OBSERVATIONS_SELECT = "noaa_ghcn_observations"

# Yearly partitions, matching the observations ingestion asset
# (configuration/ingestion/noaa-ghcn.yml -> observations: time partition, %Y).
observations_partitions = dg.TimeWindowPartitionsDefinition(
    start="2024-01-01",
    cron_schedule="0 0 1 1 *",
    fmt="%Y-%m-%d",
    end_offset=1,
)

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


def build_transform_assets() -> list[dg.AssetsDefinition]:
    @dbt_assets(
        manifest=dbt_project.manifest_path,
        dagster_dbt_translator=translator,
        exclude=OBSERVATIONS_SELECT,
    )
    def transform_assets(
        context: dg.AssetExecutionContext, dbt: DbtCliResource
    ) -> Iterable:
        yield from dbt.cli(["build"], context=context).stream()

    @dbt_assets(
        manifest=dbt_project.manifest_path,
        dagster_dbt_translator=translator,
        select=OBSERVATIONS_SELECT,
        partitions_def=observations_partitions,
    )
    def transform_partitioned_assets(
        context: dg.AssetExecutionContext, dbt: DbtCliResource
    ) -> Iterable:
        window = context.partition_time_window
        start_ds = window.start.strftime("%Y-%m-%d")
        end_ds = (window.end - timedelta(days=1)).strftime("%Y-%m-%d")
        dbt_vars = json.dumps({"start_ds": start_ds, "end_ds": end_ds})
        yield from dbt.cli(
            ["build", "--vars", dbt_vars], context=context
        ).stream()

    return [transform_assets, transform_partitioned_assets]
