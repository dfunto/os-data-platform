import pytest
from pathlib import Path
from pydantic import ValidationError

from common.models.core import IngestionConfig, LakehouseLayer


def _s3_config():
    return {
        "bucket": "test-bucket",
        "disable_auth": True,
        "tables": [
            {"name": "t", "prefix": "data/", "file_format": "Parquet", "full_refresh": True}
        ],
    }


class TestNameValidation:
    def test_rejects_hyphens(self, tmp_path):
        # Filenames use hyphens (noaa-ghcn.yml) but name must use underscores.
        with pytest.raises(ValidationError, match="name must contain only lowercase"):
            IngestionConfig(
                file_path=tmp_path / "source.yml",
                name="noaa-ghcn",
                source_type="s3",
                s3_config=_s3_config(),
            )


class TestSourceTypeConfigMismatch:
    def test_s3_source_requires_s3_config(self, tmp_path):
        with pytest.raises(ValidationError, match="source_type 's3' requires s3_config"):
            IngestionConfig(file_path=tmp_path / "source.yml", name="my_source", source_type="s3")

    def test_airbyte_source_requires_airbyte_config(self, tmp_path):
        with pytest.raises(ValidationError, match="source_type 'airbyte' requires airbyte_config"):
            IngestionConfig(file_path=tmp_path / "source.yml", name="my_source", source_type="airbyte")


class TestApplicationField:
    def test_application_differs_from_name(self, tmp_path):
        # noaa-ghcn.yml -> application="noaa-ghcn", name="noaa_ghcn".
        # Orchestrator uses config.name for all asset/table naming, not application.
        config = IngestionConfig(
            file_path=tmp_path / "noaa-ghcn.yml",
            name="noaa_ghcn",
            source_type="s3",
            s3_config=_s3_config(),
        )
        assert config.application == "noaa-ghcn"
        assert config.name == "noaa_ghcn"


def test_lakehouse_bucket_name():
    assert LakehouseLayer.RAW.bucket == "lakehouse-raw"
