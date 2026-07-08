"""SQL template rendering contracts.

Tests verify the Jinja templates produce structurally correct SQL fragments
so template changes that break the load pipeline are caught before deploy.
"""
from assets.ingestion import IngestionAssetBuilder

read = IngestionAssetBuilder.read_sql

_BASE_CREATE = dict(
    database="temp",
    table_name="my_table",
    replace=True,
    prefix="noaa_ghcn/observations/**",
    file_format="Parquet",
    columns=None,
    ingested_at="2024-01-01T00:00:00",
    partition_columns=[],
    settings=None,
    schema_only=False,
)


class TestCreateTableFromFileSql:
    def test_no_columns_uses_select_star(self):
        sql = read("ingestion/create_table_from_file.sql", **_BASE_CREATE)
        assert "SELECT" in sql
        assert "*" in sql

    def test_partition_columns_adds_partition_by_clause(self):
        sql = read("ingestion/create_table_from_file.sql", **{**_BASE_CREATE, "partition_columns": ["YEAR"]})
        assert "PARTITION BY" in sql
        assert "YEAR" in sql

    def test_no_partition_columns_omits_partition_by(self):
        sql = read("ingestion/create_table_from_file.sql", **_BASE_CREATE)
        assert "PARTITION BY" not in sql

    def test_replace_true_uses_create_or_replace(self):
        sql = read("ingestion/create_table_from_file.sql", **_BASE_CREATE)
        assert "CREATE OR REPLACE TABLE" in sql

    def test_settings_rendered_in_output(self):
        sql = read("ingestion/create_table_from_file.sql", **{**_BASE_CREATE, "settings": {"input_format_parquet_skip_columns_with_unsupported_types_in_schema_inference": "1"}})
        assert "SETTINGS" in sql
        assert "input_format_parquet_skip_columns_with_unsupported_types_in_schema_inference" in sql


class TestSwapPartitionsSql:
    def test_renders_replace_partition(self):
        sql = read(
            "common/swap_partitions.sql",
            source_database="temp",
            source_table_name="noaa_ghcn_observations_abc12345",
            target_database="raw",
            target_table_name="noaa_ghcn_observations",
            partition_values=["2024"],
        )
        assert "REPLACE PARTITION" in sql
        assert "2024" in sql
        assert "raw" in sql
        assert "temp" in sql

    def test_multi_value_partition_comma_separated(self):
        sql = read(
            "common/swap_partitions.sql",
            source_database="temp",
            source_table_name="t_tmp",
            target_database="raw",
            target_table_name="t",
            partition_values=["2024", "NA"],
        )
        assert "2024" in sql
        assert "NA" in sql


class TestCopyTableSql:
    def test_schema_only_creates_if_not_exists(self):
        sql = read(
            "common/copy_table.sql",
            schema_only=True,
            source_database="temp",
            source_table_name="t_tmp",
            target_database="raw",
            target_table_name="t",
        )
        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert "SELECT" not in sql


class TestDropTableSql:
    def test_drops_with_if_exists(self):
        sql = read("common/drop_table.sql", database="temp", table_name="t_tmp")
        assert "DROP TABLE IF EXISTS" in sql
        assert "temp" in sql
        assert "t_tmp" in sql
