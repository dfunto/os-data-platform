from abc import ABC, abstractmethod

import dagster as dg


from common.models import IngestionConfig, IngestionSourceType


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

    @abstractmethod
    def build(self) -> list[dg.AssetsDefinition]:
        pass
