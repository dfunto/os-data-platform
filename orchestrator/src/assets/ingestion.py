import dagster as dg

from abc import ABC, abstractmethod
from pathlib import Path
from common.models.ingestion import IngestionSourceType
from common.models.core import IngestionConfig


SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


class IngestionAssetBuilder(ABC):

    def __init__(self, config: IngestionConfig):
        self.config = config

    @classmethod
    def get_builder(cls, config: IngestionConfig) -> 'IngestionAssetBuilder':
        if config.source_type == IngestionSourceType.S3:
            from assets.ingestion_s3 import S3IngestionAssetBuilder
            return S3IngestionAssetBuilder(config)
        else:
            raise NotImplementedError(f"Source type not implemented {config.source_type}")

    @staticmethod
    def read_sql(relative_path: str, **params) -> str:
        from jinja2 import Template
        path = SQL_DIR / relative_path
        return Template(path.read_text()).render(**params)

    @abstractmethod
    def build(self) -> list[dg.AssetsDefinition]:
        pass
