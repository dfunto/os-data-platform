import boto3
import dagster as dg

from common.models import IngestionConfig, IngestionSourceType, IngestionS3Config, IngestionS3TableConfig
from resources.lakehouse import LakehouseResource


def _get_client(s3_config: IngestionS3Config):
    return boto3.client(
        "s3",
        aws_access_key_id=s3_config.aws_access_key_id,
        aws_secret_access_key=s3_config.aws_secret_access_key,
    )


def _copy_s3_table(context, s3_config: IngestionS3Config, table: IngestionS3TableConfig, lakehouse: LakehouseResource):
    src_client = _get_client(s3_config)
    dst_client = lakehouse.get_client()
    total_copied = 0

    prefix = table.prefix.rstrip("/*")
    context.log.info(f"Listing {s3_config.bucket}/{prefix}")
    paginator = src_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=s3_config.bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            context.log.info(f"Copying {key}")
            data = src_client.get_object(Bucket=s3_config.bucket, Key=key)["Body"].read()
            dst_client.put_object(Bucket="lakehouse-raw", Key=key, Body=data)
            total_copied += 1

    return total_copied


def build_ingestion_assets(config: IngestionConfig) -> list[dg.AssetsDefinition]:
    if config.source_type == IngestionSourceType.S3:
        s3_config = config.s3_config
        if not s3_config:
            raise ValueError("s3_config is required for S3 ingestion")

        def _make_asset(table: IngestionS3TableConfig):
            @dg.asset(name=f"ingest_{config.name}_{table.name}")
            def _asset(context: dg.AssetExecutionContext, lakehouse: LakehouseResource):
                context.log.info(f"Ingesting {config.name}/{table.name}")
                total = _copy_s3_table(context, s3_config, table, lakehouse)
                return {"rows": total}
            return _asset

        return [_make_asset(table) for table in s3_config.tables]

    raise ValueError(f"Source type not implemented {config.source_type}")
