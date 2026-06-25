import dagster as dg

from common.models import IngestionConfig, IngestionSourceType
from resources.s3 import S3Resource


def _copy_s3_to_s3(context, config: IngestionConfig, source_s3: S3Resource, landing_s3: S3Resource):
    src_client = source_s3.get_client()
    dst_client = landing_s3.get_client()
    source_bucket = config.config["bucket"]
    total_copied = 0

    for stream in config.config["streams"]:
        for glob in stream["globs"]:
            prefix = glob.rstrip("/*")
            context.log.info(f"Listing {source_bucket}/{prefix}")
            paginator = src_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=source_bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    context.log.info(f"Copying {key}")
                    data = src_client.get_object(Bucket=source_bucket, Key=key)["Body"].read()
                    dst_client.put_object(Bucket="landing", Key=key, Body=data)
                    total_copied += 1

    return total_copied


def build_ingestion_asset(config: IngestionConfig):
    @dg.asset(name=f"ingest_{config.name}")
    def _asset(context: dg.AssetExecutionContext, source_s3: S3Resource, landing_s3: S3Resource):
        context.log.info(f"Ingesting {config.source_type}: {config.name}")

        if config.source_type == IngestionSourceType.S3:
            total = _copy_s3_to_s3(context, config, source_s3, landing_s3)
            return {"rows": total}

        raise ValueError(f"Unsupported source type: {config.source_type}")

    return _asset
