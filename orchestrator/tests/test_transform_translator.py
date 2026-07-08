import dagster as dg

from assets.transform import CustomDagsterDbtTranslator, _raw_partitions
from assets.ingestion import IngestionAssetBuilder

from helpers import TIME_PARTITION, _s3_table, _ingestion_config


translator = CustomDagsterDbtTranslator()


class TestCustomDagsterDbtTranslator:
    def test_asset_key_uses_schema_and_alias(self):
        key = translator.get_asset_key({"schema": "cleansed", "alias": "noaa_ghcn_countries", "name": "countries"})
        assert key == dg.AssetKey("cleansed_noaa_ghcn_countries")

    def test_asset_key_falls_back_to_name_when_no_alias(self):
        key = translator.get_asset_key({"schema": "raw", "name": "noaa_ghcn_observations"})
        assert key == dg.AssetKey("raw_noaa_ghcn_observations")

    def test_group_name_is_schema(self):
        assert translator.get_group_name({"schema": "cleansed"}) == "cleansed"
        assert translator.get_group_name({"schema": "raw"}) == "raw"

    def test_automation_condition_is_eager(self):
        condition = translator.get_automation_condition({})
        assert condition == dg.AutomationCondition.eager()


class TestRawPartitions:
    def test_partitioned_table_included_with_correct_key(self):
        table = _s3_table(full_refresh=False, partitions=[TIME_PARTITION])
        config = _ingestion_config(name="noaa_ghcn", tables=[table])
        partitions = _raw_partitions([config])
        assert "raw_noaa_ghcn_observations" in partitions
        assert isinstance(partitions["raw_noaa_ghcn_observations"], dg.TimeWindowPartitionsDefinition)

    def test_full_refresh_table_excluded(self):
        table = _s3_table(full_refresh=True)
        config = _ingestion_config(tables=[table])
        partitions = _raw_partitions([config])
        assert len(partitions) == 0

    def test_multiple_sources_each_produce_own_key(self):
        t1 = _s3_table("obs", full_refresh=False, partitions=[TIME_PARTITION])
        t2 = _s3_table("obs", full_refresh=False, partitions=[TIME_PARTITION])
        c1 = _ingestion_config(name="source_a", tables=[t1])
        c2 = _ingestion_config(name="source_b", tables=[t2])
        partitions = _raw_partitions([c1, c2])
        assert "raw_source_a_obs" in partitions
        assert "raw_source_b_obs" in partitions
