from pydantic import BaseModel

from common.models.ingestion import IngestionTableConfig


class PageNumberPaginatorConfig(BaseModel):
    type: str = "page_number"
    page_param: str = "page"
    base_page: int = 1
    total_path: str | None = None  # JSONPath to total page count; None -> stop on empty page
    data_selector: str | None = None  # JSONPath to the records within the response


class IngestionApiTableConfig(IngestionTableConfig):
    url: str
    primary_key: str | list[str] | None = None
    params: dict[str, str] = {}
    pagination: PageNumberPaginatorConfig | None = None  # None -> let dlt auto-detect


class IngestionApiConfig(BaseModel):
    # Concurrency pool shared by all of this source's assets (tables + partitions) so
    # backfills can't exceed the API's rate limit. Defaults to the source name; the slot
    # count is set on the instance (`dagster instance concurrency set <pool> <n>`).
    pool: str | None = None
    tables: list[IngestionApiTableConfig]