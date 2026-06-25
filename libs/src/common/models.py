from abc import ABC
from enum import Enum
from pathlib import Path
from typing import ClassVar
from pydantic import BaseModel, computed_field


class CapabilityConfig(BaseModel, ABC):
    file_path: Path
    capability_name: ClassVar[str]


class IngestionSourceType(Enum):
    S3 = "s3"


class IngestionConfig(CapabilityConfig):
    capability_name: ClassVar[str] = "ingestion"
    name: str
    source_type: IngestionSourceType
    config: dict

    @computed_field
    def application(self) -> str:
        return self.file_path.stem
