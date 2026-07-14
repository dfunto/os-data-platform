import pytest
from pydantic import ValidationError

from common.models.ingestion import ClickHouseFileFormat
from common.models.ingestion_s3 import IngestionS3Config, IngestionS3TableConfig


def _table(prefix: str, full_refresh: bool = True, extra_partitions: list | None = None) -> IngestionS3TableConfig:
    partitions = None
    if not full_refresh:
        partitions = [
            {"type": "time", "name": "YEAR", "start": "2024-01-01", "cron": "0 0 1 1 *", "format": "%Y"},
            *(extra_partitions or []),
        ]
    return IngestionS3TableConfig(
        name="observations",
        prefix=prefix,
        file_format=ClickHouseFileFormat.PARQUET,
        full_refresh=full_refresh,
        partitions=partitions,
    )


class TestGetSourcePrefix:
    def test_glob_star_stripped(self):
        # "parquet/by_year/*" strips to "parquet/by_year" - no trailing slash.
        assert _table("parquet/by_year/*").get_source_prefix() == "parquet/by_year"

    def test_double_glob_only_partially_stripped(self):
        # "/**" doesn't match removesuffix("/*"), so only one "*" removed -> still has glob.
        # Use single "/*" or trailing slash - "/**" is not fully handled.
        assert _table("parquet/by_year/**").get_source_prefix() == "parquet/by_year/*"

    def test_trailing_slash_with_partitions(self):
        # Safe pattern: trailing slash + partition params = correct path.
        table = _table("parquet/by_year/", full_refresh=False)
        assert table.get_source_prefix({"YEAR": "2024"}) == "parquet/by_year/YEAR=2024"

    def test_glob_star_with_partitions_missing_separator(self):
        # "parquet/by_year/*" strips to "parquet/by_year" then suffix appended directly:
        # "parquet/by_year" + "YEAR=2024" = "parquet/by_yearYEAR=2024".
        # Use trailing slash in prefix when partitions are present.
        table = _table("parquet/by_year/*", full_refresh=False)
        assert table.get_source_prefix({"YEAR": "2024"}) == "parquet/by_yearYEAR=2024"

    def test_multi_key_partitions_joined_with_slash(self):
        table = _table(
            "data/sales/",
            full_refresh=False,
            extra_partitions=[{"type": "static", "name": "REGION", "values": ["NA"]}],
        )
        assert table.get_source_prefix({"YEAR": "2024", "REGION": "NA"}) == "data/sales/YEAR=2024/REGION=NA"


class TestGetTargetPrefix:
    def test_with_partition_params(self):
        table = _table("parquet/by_year/", full_refresh=False)
        assert table.get_target_prefix("noaa_ghcn", {"YEAR": "2024"}) == "noaa_ghcn/observations/YEAR=2024"

    def test_multi_key_partitions(self):
        table = _table(
            "data/",
            full_refresh=False,
            extra_partitions=[{"type": "static", "name": "REGION", "values": ["NA"]}],
        )
        assert table.get_target_prefix("src", {"YEAR": "2024", "REGION": "NA"}) == "src/observations/YEAR=2024/REGION=NA"


class TestS3ConfigAuthValidation:
    def test_disable_auth_requires_no_k8s_fields(self):
        config = IngestionS3Config(
            bucket="noaa-ghcn-pds",
            disable_auth=True,
            tables=[{"name": "t", "prefix": "data/", "file_format": "Parquet", "full_refresh": True}],
        )
        assert config.disable_auth is True

    def test_all_missing_k8s_fields_listed_in_error(self):
        # Error must name every missing field at once, not just the first.
        with pytest.raises(ValidationError) as exc_info:
            IngestionS3Config(
                bucket="my-bucket",
                tables=[{"name": "t", "prefix": "data/", "file_format": "Parquet", "full_refresh": True}],
            )
        error_msg = str(exc_info.value)
        assert "k8s_secret" in error_msg
        assert "k8s_secret_aws_key" in error_msg
        assert "k8s_secret_aws_secret" in error_msg
