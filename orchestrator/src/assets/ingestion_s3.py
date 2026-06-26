import boto3
import dagster as dg

from botocore.client import BaseClient
from functools import cached_property
from assets.ingestion import IngestionAssetBuilder
from common.models.ingestion import IngestionS3TableConfig
from common.models.core import  LakehouseLayer
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
        return boto3.client(
            "s3",
            aws_access_key_id=self.s3_config.aws_access_key_id,
            aws_secret_access_key=self.s3_config.aws_secret_access_key,
        )

    def _build_assets(self, table: IngestionS3TableConfig) -> list[dg.AssetsDefinition]:
        source_name = self.config.name

        @dg.asset(name=f"ingest_{source_name}_{table.name}")
        def ingest_s3(context: dg.AssetExecutionContext, lakehouse: LakehouseResource):
            context.log.info(f"Ingesting source: {source_name} table: {table.name}")
            total = self._copy_s3_table(context, table, lakehouse)
            return {"files": total}

        @dg.asset(name=f"raw_{source_name}_{table.name}", deps=[ingest_s3])
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
        lakehouse: LakehouseResource
    ) -> int:
        lakehouse_client = lakehouse.get_client()
        total_copied = 0

        prefix = table.prefix.rstrip("/*")
        context.log.info(f"Listing {self.s3_config.bucket}/{prefix}")
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.s3_config.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                context.log.info(f"Copying {key}")
                data = self._client.get_object(Bucket=self.s3_config.bucket, Key=key)["Body"].read()
                lakehouse_client.put_object(Bucket=LakehouseLayer.RAW.bucket, Key=key, Body=data)
                total_copied += 1

        return total_copied

    def _run_sql(
        self,
        context: dg.AssetExecutionContext,
        table: IngestionS3TableConfig,
        warehouse: WarehouseResource
    ) -> bool:
        with warehouse.get_connection() as client:
            sql = self.read_sql(
                "ingestion/create_raw_table.sql",
                source_name=self.config.name,
                table_name=table.name,
                prefix=table.prefix.rstrip("/*"),
            )
            context.log.info(f"Running sql query: {sql}")
            client.execute(query=sql)
        return True
