import pytest
from pydantic import ValidationError

from common.models.ingestion import IngestionTableConfig


class TestIncrementalRequiresPartitions:
    def test_incremental_without_partitions_fails(self):
        with pytest.raises(ValidationError, match="incremental load requires partitions"):
            IngestionTableConfig(name="observations", full_refresh=False)


class TestPartitionColumns:
    def test_mixed_partition_types_preserves_order(self):
        # Order determines how partition path segments are joined in get_source_prefix.
        table = IngestionTableConfig(
            name="observations",
            full_refresh=False,
            partitions=[
                {"type": "time", "name": "YEAR", "start": "2024-01-01", "cron": "0 0 1 1 *", "format": "%Y"},
                {"type": "static", "name": "ELEMENT", "values": ["TMAX", "TMIN"]},
            ],
        )
        assert table.partition_columns == ["YEAR", "ELEMENT"]
