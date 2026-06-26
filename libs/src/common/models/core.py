from abc import ABC
from enum import Enum

from pathlib import Path
from typing import ClassVar
from pydantic import BaseModel, model_validator, computed_field

from common.models.ingestion import IngestionSourceType, IngestionS3Config


class CapabilityConfig(BaseModel, ABC):
    file_path: Path
    capability_name: ClassVar[str]


class LakehouseLayer(Enum):
    RAW = "raw"
    CLEANSED = "cleansed"
    CURATED = "curated"

    @property
    def bucket(self):
        return f"lakehouse-{self.value}"


class ClickHouseFileFormat(Enum):
  PARQUET = "Parquet"
  CSV = "CSV"
  CSV_WITH_NAMES = "CSVWithNames"
  TSV = "TabSeparated"
  JSON_EACH_ROW = "JSONEachRow"
  AVRO = "Avro"
  ORC = "ORC"
  ARROW = "Arrow"


class IngestionConfig(CapabilityConfig):
    capability_name: ClassVar[str] = "ingestion"
    name: str
    source_type: IngestionSourceType
    s3_config: IngestionS3Config | None = None
    airbyte_config: dict | None = None

    @model_validator(mode="after")
    def validate_config_matches_source(self):
        config_map = {
            IngestionSourceType.S3: "s3_config",
            IngestionSourceType.AIRBYTE: "airbyte_config",
        }
        field = config_map[self.source_type]
        if getattr(self, field) is None:
            raise ValueError(f"source_type '{self.source_type.value}' requires {field}")
        return self

    @computed_field
    def application(self) -> str:
        return self.file_path.stem