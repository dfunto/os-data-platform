import dagster as dg

from assets.ingestion import IngestionAssetBuilder
from assets.ingestion_s3 import S3IngestionAssetBuilder
from common.models.ingestion_s3 import IngestionS3TableConfig
from common.models.ingestion import ClickHouseFileFormat

from helpers import TIME_PARTITION, STATIC_PARTITION, _s3_table, _ingestion_config


def _incremental_table(extra_partitions: list | None = None) -> IngestionS3TableConfig:
    return _s3_table(
        full_refresh=False,
        partitions=[TIME_PARTITION, *(extra_partitions or [])],
    )


class TestBuildPartitionsDef:
    def test_no_partitions_returns_none(self):
        table = _s3_table(full_refresh=True)
        assert IngestionAssetBuilder.build_partitions_def(table.partitions) is None

    def test_single_time_partition_is_time_window(self):
        table = _incremental_table()
        result = IngestionAssetBuilder.build_partitions_def(table.partitions)
        assert isinstance(result, dg.TimeWindowPartitionsDefinition)
        assert result.fmt == "%Y"

    def test_single_static_partition_is_static(self):
        table = _s3_table(
            full_refresh=False,
            partitions=[STATIC_PARTITION],
        )
        result = IngestionAssetBuilder.build_partitions_def(table.partitions)
        assert isinstance(result, dg.StaticPartitionsDefinition)
        assert set(result.get_partition_keys()) == {"NA", "EU"}

    def test_multi_partition_wraps_both_dimensions(self):
        table = _incremental_table(extra_partitions=[STATIC_PARTITION])
        result = IngestionAssetBuilder.build_partitions_def(table.partitions)
        assert isinstance(result, dg.MultiPartitionsDefinition)
        dims = {name: type(pdef) for name, pdef in result.partitions_defs}
        assert dims["YEAR"] is dg.TimeWindowPartitionsDefinition
        assert dims["REGION"] is dg.StaticPartitionsDefinition


class TestGetBuilder:
    def test_s3_source_returns_s3_builder(self):
        config = _ingestion_config()
        builder = IngestionAssetBuilder.get_builder(config)
        assert isinstance(builder, S3IngestionAssetBuilder)


class TestBuildAssets:
    def test_creates_ingest_and_raw_assets_per_table(self):
        config = _ingestion_config()
        assets = S3IngestionAssetBuilder(config).build()
        assert len(assets) == 2
        keys = {str(a.key) for a in assets}
        assert any("ingest_noaa_ghcn_observations" in k for k in keys)
        assert any("raw_noaa_ghcn_observations" in k for k in keys)

    def test_two_tables_produce_four_assets(self):
        tables = [_s3_table("t1"), _s3_table("t2")]
        config = _ingestion_config(tables=tables)
        assets = S3IngestionAssetBuilder(config).build()
        assert len(assets) == 4

    def test_partitioned_table_attaches_partitions_def(self):
        table = _s3_table(full_refresh=False, partitions=[TIME_PARTITION])
        config = _ingestion_config(tables=[table])
        assets = S3IngestionAssetBuilder(config).build()
        ingest_asset = next(a for a in assets if "ingest_" in str(a.key))
        assert ingest_asset.partitions_def is not None
