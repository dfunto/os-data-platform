from abc import ABC
from pathlib import Path
from typing import ClassVar, Literal
from croniter import croniter
from pydantic import BaseModel, field_validator, computed_field


class CapabilityConfig(BaseModel, ABC):
    file_path: Path
    capability_name: ClassVar[str]


class S3Source(BaseModel):
    type: Literal["s3"]
    bucket: str
    prefix: str


class Triggers(BaseModel):
    schedule: str

    @field_validator("schedule")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not croniter.is_valid(v):
            raise ValueError(f"invalid cron expression: {v!r}")
        return v


class IngestionConfig(CapabilityConfig):
    capability_name: ClassVar[str] = "ingestion"
    name: str
    source: S3Source
    triggers: Triggers

    @computed_field
    def application(self) -> str:
        return self.file_path.stem
