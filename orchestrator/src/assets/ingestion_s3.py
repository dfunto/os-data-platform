import boto3
import dagster as dg

from datetime import datetime

from botocore import UNSIGNED
from botocore.client import BaseClient
from botocore.config import Config
from functools import cached_property
from assets.ingestion import IngestionAssetBuilder
from common.models.ingestion_s3 import IngestionS3TableConfig
from common.models.core import LakehouseLayer, SQLTemplate
from resources.lakehouse import LakehouseResource
from resources.warehouse import WarehouseResource


class S3IngestionAssetBuilder(IngestionAssetBuilder):

    def build(self) -> list[dg.AssetsDefinition]:
        assets = []
        for table in self.s3_config.tables:
            assets.extend(
                self._build_assets(table)
            )
        return assets

    @cached_property
    def s3_config(self):
        if not self.config.s3_config:
            raise ValueError(f"Missing s3_config for ingestion source {self.config.name}")
        return self.config.s3_config

    @cached_property
    def _client(self) -> BaseClient:
        if self.s3_config.disable_auth:
            return boto3.client("s3", config=Config(signature_version=UNSIGNED))
        return boto3.client(
            "s3",
            aws_access_key_id=self.s3_config.aws_access_key_id,
            aws_secret_access_key=self.s3_config.aws_secret_access_key,
        )

    def _build_assets(self, table: IngestionS3TableConfig) -> list[dg.AssetsDefinition]:
        source_name = self.config.name
        partitions_def = self.build_partitions_def(table)

        @dg.asset(name=f"ingest_{source_name}_{table.name}", group_name="ingestion", partitions_def=partitions_def)
        def ingest_s3(context: dg.AssetExecutionContext, lakehouse: LakehouseResource):
            context.log.info(f"Ingesting source: {source_name} table: {table.name}")
            total = self._copy_s3_table(context, table, lakehouse)
            return {"files": total}

        @dg.asset(name=f"raw_{source_name}_{table.name}", deps=[ingest_s3], group_name="ingestion", partitions_def=partitions_def)
        def create_raw_table(context: dg.AssetExecutionContext, warehouse: WarehouseResource):
            context.log.info(f"Creating raw table: {source_name} table: {table.name}")
            result = self._run_sql(context, table, warehouse)
            return {"result": result}

        return [
            ingest_s3,
            create_raw_table
        ]

    def _copy_s3_table(
        self,
        context: dg.AssetExecutionContext,
        table: IngestionS3TableConfig,
        lakehouse: LakehouseResource,
    ) -> int:
        lakehouse_client = lakehouse.get_client()
        total_copied = 0
        partition_params = self.resolve_partition_keys(context, table)

        source_prefix = table.get_source_prefix(partition_params)
        target_prefix = table.get_target_prefix(self.config.name, partition_params)
        context.log.info(f"Listing {self.s3_config.bucket}/{source_prefix}")
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.s3_config.bucket, Prefix=source_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                context.log.info(f"Copying {key}")
                data = self._client.get_object(Bucket=self.s3_config.bucket, Key=key)["Body"].read()
                relative_key = key[len(source_prefix):].lstrip("/") or key.rsplit("/", 1)[-1]
                lakehouse_client.put_object(Bucket=LakehouseLayer.RAW.bucket, Key=f"{target_prefix}/{relative_key}", Body=data)
                total_copied += 1

        return total_copied

    def _run_sql(
        self,
        context: dg.AssetExecutionContext,
        table: IngestionS3TableConfig,
        warehouse: WarehouseResource,
    ) -> bool:
        launch_time = context.instance.get_run_stats(context.run_id).launch_time
        if not launch_time:
            raise ValueError("Could not fetch run launch time")
        partition_params = self.resolve_partition_keys(context, table)

        template_vars = dict(
            source_name=self.config.name,
            table_name=table.name,
            prefix=f"{table.get_target_prefix(self.config.name, partition_params)}/**",
            file_format=table.file_format.value,
            columns=table.columns,
            settings=table.settings,
            full_refresh=table.full_refresh,
            ingested_at=datetime.fromtimestamp(launch_time).isoformat()
        )
        with warehouse.get_connection() as client:
            statements = (
                self._get_full_refresh_statements(template_vars)
                if table.full_refresh
                else self._get_incremental_load_statements(template_vars)
            )
            executed = []
            for statement in statements:
                sql = self.read_sql(
                    relative_path=statement.template,
                    **statement.vars
                )
                context.log.info(f"Running sql: {sql}")
                client.execute(query=sql)
                executed.append(f"{sql};")
            context.add_output_metadata({
                "sql": dg.MetadataValue.md(f"```sql\n{'\n\n'.join(executed)}\n```")
            })
        return True

    @staticmethod
    def _get_full_refresh_statements(template_vars: dict) -> list[SQLTemplate]:
        return [
            SQLTemplate(
                template="ingestion/create_table_from_file.sql",
                vars={**template_vars, "database": "temp"},
            ),
            SQLTemplate(
                template="common/copy_table.sql",
                vars={**template_vars, "source_database": "temp", "target_database": "raw", "schema_only": True},
            ),
            SQLTemplate(
                template="common/swap_tables.sql",
                vars={**template_vars, "source_database": "temp", "target_database": "raw"},
            ),
            SQLTemplate(
                template="common/drop_table.sql",
                vars={**template_vars, "database": "temp"},
            ),
        ]

    @staticmethod
    def _get_incremental_load_statements(template_vars: dict) -> list[SQLTemplate]:
        return [
            SQLTemplate(
                template="ingestion/create_table_from_file.sql",
                vars={**template_vars, "database": "raw", "schema_only": True},
            ),
            SQLTemplate(
                template="ingestion/insert_from_file.sql",
                vars={**template_vars, "database": "raw"},
            ),
        ]
