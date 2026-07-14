import re
from abc import ABC
from enum import Enum
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, computed_field, field_validator, model_validator
from common.models.ingestion import IngestionSourceType
from common.models.ingestion_s3 import IngestionS3Config
from common.models.ingestion_api import IngestionApiConfig


class SQLTemplate(BaseModel):
    template: str
    vars: dict[str, object]


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


class IngestionConfig(CapabilityConfig):
    capability_name: ClassVar[str] = "ingestion"
    name: str
    description: str | None = None
    source_type: IngestionSourceType
    s3_config: IngestionS3Config | None = None
    api_config: IngestionApiConfig | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9_]+", v):
            raise ValueError(f"name must contain only lowercase letters, numbers, and underscores, got: '{v}'")
        return v

    @model_validator(mode="after")
    def validate_config_matches_source(self):
        config_map = {
            IngestionSourceType.S3: "s3_config",
            IngestionSourceType.API: "api_config",
        }
        field = config_map[self.source_type]
        if getattr(self, field) is None:
            raise ValueError(f"source_type '{self.source_type.value}' requires {field}")
        return self

    @computed_field
    def application(self) -> str:
        return self.file_path.stem