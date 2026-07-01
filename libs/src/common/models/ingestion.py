from enum import Enum
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, model_validator


class IngestionSourceType(Enum):
    S3 = "s3"
    AIRBYTE = "airbyte"


class ClickHouseFileFormat(Enum):
    PARQUET = "Parquet"
    CSV = "CSV"
    CSV_WITH_NAMES = "CSVWithNames"
    TSV = "TabSeparated"
    JSON_EACH_ROW = "JSONEachRow"
    AVRO = "Avro"
    ORC = "ORC"
    ARROW = "Arrow"
    REGEXP = "Regexp"
    LINE_AS_STRING = "LineAsString"


class ColumnDefinition(BaseModel):
    name: str
    type: str = "String"
    expression: str | None = None


class TimePartition(BaseModel):
    type: Literal["time"] = "time"
    name: str
    start: datetime
    cron: str
    format: str


class StaticPartition(BaseModel):
    type: Literal["static"] = "static"
    name: str
    values: list[str]


PartitionDef = Annotated[
    TimePartition | StaticPartition,
    Discriminator("type"),
]


class IngestionTableConfig(BaseModel):
    name: str
    description: str | None = None
    full_refresh: bool = False
    partitions: list[PartitionDef] | None = None

    @model_validator(mode="after")
    def validate_incremental_requires_partitions(self):
        if not self.full_refresh and not self.partitions:
            raise ValueError(f"Table '{self.name}': incremental load requires partitions")
        return self

    @property
    def partition_columns(self) -> list[str]:
        if not self.partitions:
            return []
        return [p.name for p in self.partitions]
