from assets.ingestion_s3 import S3IngestionAssetBuilder

_BASE_VARS = dict(
    source_name="noaa_ghcn",
    table_name="noaa_ghcn_observations",
    temp_table_name="noaa_ghcn_observations_abc12345",
    prefix="noaa_ghcn/observations/**",
    file_format="Parquet",
    columns=None,
    settings=None,
    full_refresh=False,
    ingested_at="2024-01-01T00:00:00",
    partition_columns=["YEAR"],
    partition_values=["2024"],
)


class TestGetLoadStatements:
    def test_always_produces_four_statements(self):
        stmts = S3IngestionAssetBuilder._get_load_statements(_BASE_VARS)
        assert len(stmts) == 4

    def test_statement_order_create_copy_swap_drop(self):
        stmts = S3IngestionAssetBuilder._get_load_statements(_BASE_VARS)
        templates = [s.template for s in stmts]
        assert templates[0] == "ingestion/create_table_from_file.sql"
        assert templates[1] == "common/copy_table.sql"
        assert templates[3] == "common/drop_table.sql"

    def test_partitioned_uses_swap_partitions_template(self):
        stmts = S3IngestionAssetBuilder._get_load_statements({**_BASE_VARS, "partition_values": ["2024"]})
        assert stmts[2].template == "common/swap_partitions.sql"

    def test_non_partitioned_uses_swap_tables_template(self):
        stmts = S3IngestionAssetBuilder._get_load_statements({**_BASE_VARS, "partition_values": []})
        assert stmts[2].template == "common/swap_tables.sql"

    def test_temp_table_created_in_temp_database(self):
        stmts = S3IngestionAssetBuilder._get_load_statements(_BASE_VARS)
        create_vars = stmts[0].vars
        assert create_vars["database"] == "temp"
        assert create_vars["table_name"] == _BASE_VARS["temp_table_name"]

    def test_copy_schema_uses_temp_as_source_and_raw_as_target(self):
        stmts = S3IngestionAssetBuilder._get_load_statements(_BASE_VARS)
        copy_vars = stmts[1].vars
        assert copy_vars["source_database"] == "temp"
        assert copy_vars["target_database"] == "raw"
        assert copy_vars["target_table_name"] == _BASE_VARS["table_name"]

    def test_temp_table_dropped_at_end(self):
        stmts = S3IngestionAssetBuilder._get_load_statements(_BASE_VARS)
        drop_vars = stmts[3].vars
        assert drop_vars["database"] == "temp"
        assert drop_vars["table_name"] == _BASE_VARS["temp_table_name"]
