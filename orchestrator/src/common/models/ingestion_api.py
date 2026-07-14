from pydantic import BaseModel

from common.models.ingestion import IngestionTableConfig


class IngestionApiTableConfig(IngestionTableConfig):
    url: str
    primary_key: str | list[str] | None = None
    params: dict[str, str] = {}


class IngestionApiConfig(BaseModel):
    tables: list[IngestionApiTableConfig]
