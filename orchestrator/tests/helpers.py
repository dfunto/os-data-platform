from pathlib import Path

import pytest

from common.models.core import IngestionConfig
from common.models.ingestion import ClickHouseFileFormat
from common.models.ingestion_s3 import IngestionS3TableConfig


def _s3_table(
    name: str = "observations",
    prefix: str = "data/",
    full_refresh: bool = True,
    partitions: list | None = None,
) -> IngestionS3TableConfig:
    return IngestionS3TableConfig(
        name=name,
        prefix=prefix,
        file_format=ClickHouseFileFormat.PARQUET,
        full_refresh=full_refresh,
        partitions=partitions,
    )


def _ingestion_config(
    name: str = "noaa_ghcn",
    tables: list | None = None,
    tmp_path: Path | None = None,
) -> IngestionConfig:
    file_path = (tmp_path or Path("/tmp")) / f"{name}.yml"
    return IngestionConfig(
        file_path=file_path,
        name=name,
        source_type="s3",
        s3_config={
            "bucket": "test-bucket",
            "disable_auth": True,
            "tables": [
                {
                    "name": t.name,
                    "prefix": t.prefix,
                    "file_format": t.file_format.value,
                    "full_refresh": t.full_refresh,
                    "partitions": [p.model_dump() for p in t.partitions] if t.partitions else None,
                }
                for t in (tables or [_s3_table()])
            ],
        },
    )


TIME_PARTITION = {
    "type": "time",
    "name": "YEAR",
    "start": "2024-01-01",
    "cron": "0 0 1 1 *",
    "format": "%Y",
}

STATIC_PARTITION = {
    "type": "static",
    "name": "REGION",
    "values": ["NA", "EU"],
}
