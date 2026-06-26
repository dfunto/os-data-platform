import boto3
import dagster as dg
from botocore.client import BaseClient
from functools import cached_property

from assets.ingestion import IngestionAssetBuilder
from common.models import IngestionS3TableConfig, LakehouseLayer
from resources.lakehouse import LakehouseResource


class S3IngestionAssetBuilder(IngestionAssetBuilder):

    def build(self) -> list[dg.AssetsDefinition]:
        return [
            self._build_asset(table)
            for table in self.s3_config.tables
        ]

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

    def _build_asset(self, table: IngestionS3TableConfig):
        source_name = self.config.name
        @dg.asset(name=f"ingest_{source_name}_{table.name}")
        def asset(context: dg.AssetExecutionContext, lakehouse: LakehouseResource):
            context.log.info(f"Ingesting source: {source_name} table: {table.name}")
            total = self._copy_s3_table(context, table, lakehouse)
            return {"files": total}
        return asset

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