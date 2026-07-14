import dagster as dg
import sqlparse

from abc import ABC, abstractmethod
from jinja2 import Template
from pathlib import Path
from common.models.ingestion import (
    IngestionSourceType,
    IngestionTableConfig,
    TimePartition,
    StaticPartition,
)
from common.models.core import IngestionConfig


SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


class IngestionAssetBuilder(ABC):

    def __init__(self, config: IngestionConfig):
        self.config = config
        self.group_name = "raw"

    @classmethod
    def get_builder(cls, config: IngestionConfig) -> 'IngestionAssetBuilder':
        if config.source_type == IngestionSourceType.S3:
            from assets.ingestion_s3 import S3IngestionAssetBuilder
            return S3IngestionAssetBuilder(config)
        if config.source_type == IngestionSourceType.API:
            from assets.ingestion_api import ApiIngestionAssetBuilder
            return ApiIngestionAssetBuilder(config)
        raise NotImplementedError(f"Source type not implemented {config.source_type}")

    @staticmethod
    def read_sql(relative_path: str, **params) -> str:
        path = SQL_DIR / relative_path
        sql = Template(path.read_text()).render(**params)
        return sqlparse.format(sql, reindent=True)

    @staticmethod
    def _get_dagster_partition(p: TimePartition | StaticPartition) -> dg.PartitionsDefinition:
        if isinstance(p, TimePartition):
            return dg.TimeWindowPartitionsDefinition(
                start=p.start.strftime(p.format),
                cron_schedule=p.cron,
                fmt=p.format,
                end_offset=1,
            )
        return dg.StaticPartitionsDefinition(p.values)

    @classmethod
    def build_partitions_def(
        cls,
        table: IngestionTableConfig,
    ) -> dg.PartitionsDefinition | None:
        partitions = table.partitions
        if not partitions:
            return None

        if len(partitions) == 1:
            return cls._get_dagster_partition(partitions[0])

        return dg.MultiPartitionsDefinition({
            p.name: cls._get_dagster_partition(p) for p in partitions
        })

    @staticmethod
    def resolve_partition_keys(
        context: dg.AssetExecutionContext,
        table: IngestionTableConfig,
    ) -> dict[str, str]:
        if not table.partitions:
            return {}

        if not context.has_partition_key:
            raise ValueError(f"Table '{table.name}' has partitions configured but no partition key was provided")

        partition_key = context.partition_key
        if isinstance(partition_key, dg.MultiPartitionKey):
            return dict(partition_key.keys_by_dimension)
        return {table.partitions[0].name: partition_key}

    @abstractmethod
    def build(self) -> list[dg.AssetsDefinition]:
        pass
