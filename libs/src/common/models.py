from abc import ABC
from pathlib import Path
from typing import ClassVar
from pydantic import BaseModel, computed_field


class CapabilityConfig(BaseModel, ABC):
    file_path: Path
    capability_name: ClassVar[str]


class IngestionConfig(CapabilityConfig):
    capability_name: ClassVar[str] = "ingestion"
    name: str
    source_type: str
    config: dict

    @computed_field
    def application(self) -> str:
        return self.file_path.stem
