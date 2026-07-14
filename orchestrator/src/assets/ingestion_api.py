import tempfile
from typing import Literal

import requests
import dlt
import dagster as dg
from dlt.destinations.impl.clickhouse.configuration import ClickHouseCredentials

from assets.ingestion import IngestionAssetBuilder
from common.models.ingestion_api import IngestionApiTableConfig
from resources.warehouse import WarehouseResource


def _fetch_paginated(url: str, params: dict) -> list[dict]:
    page = 1
    all_records = []
    while True:
        resp = requests.get(
            url,
            params={"format": "json", "per_page": 1000, "page": page, **params},
        ).json()
        meta, records = resp[0], resp[1] or []
        all_records.extend(records)
        if page >= meta["pages"]:
            break
        page += 1
    return all_records


class ApiIngestionAssetBuilder(IngestionAssetBuilder):

    def build(self) -> list[dg.AssetsDefinition]:
        return [self._build_asset(table) for table in self.config.api_config.tables]

    @staticmethod
    def _build_credentials(warehouse: WarehouseResource) -> ClickHouseCredentials:
        # dlt's clickhouse destination defaults to secure=1, forcing native TLS on the
        # native port and HTTPS (8443) for the HTTP load step. Drive TLS from the
        # warehouse resource (off for plain HTTP).
        credentials = ClickHouseCredentials()
        credentials.host = warehouse.host
        credentials.port = warehouse.port
        credentials.http_port = warehouse.http_port
        credentials.username = warehouse.user
        credentials.password = warehouse.password
        credentials.database = "raw"
        credentials.secure = 1 if warehouse.secure else 0
        return credentials

    def _build_asset(self, table: IngestionApiTableConfig) -> dg.AssetsDefinition:
        source_name = self.config.name
        partitions_def = self.build_partitions_def(table)
        write_disposition: Literal["replace", "append"] = (
            "replace" if table.full_refresh else "append"
        )

        @dg.asset(
            name=f"raw_{source_name}_{table.name}",
            group_name=self.group_name,
            partitions_def=partitions_def,
        )
        def run_api_pipeline(context: dg.AssetExecutionContext, warehouse: WarehouseResource):
            # Request params may reference the run's partition keys via placeholders,
            # e.g. {"date": "{YEAR}"} formatted from the resolved partition key.
            partition_params = self.resolve_partition_keys(context, table)
            request_params = {k: v.format(**partition_params) for k, v in table.params.items()}

            @dlt.resource(name=f"{source_name}_{table.name}", primary_key=table.primary_key)
            def _resource():
                yield _fetch_paginated(table.url, params=request_params)

            credentials = self._build_credentials(warehouse)
            # ClickHouse has no schemas; dlt emulates a dataset by prefixing table names
            # with `{dataset_name}{separator}`. The `raw` layer is the credentials database,
            # so use an empty dataset + separator to land tables flat as `raw.<table>`.
            destination = dlt.destinations.clickhouse(
                credentials=credentials, dataset_table_separator=""
            )
            # Isolate dlt's local state per run so concurrent partition backfills of the
            # same table don't share (and corrupt) a working dir; state is ephemeral.
            pipeline = dlt.pipeline(
                pipeline_name=f"{source_name}_{table.name}_{context.run_id[:8]}",
                destination=destination,
                dataset_name="",
                pipelines_dir=tempfile.mkdtemp(),
            )
            info = pipeline.run(_resource(), write_disposition=write_disposition)
            context.log.info(str(info))
            return dg.Output(
                value=None,
                metadata={"load_packages": len(info.load_packages)},
            )

        return run_api_pipeline
