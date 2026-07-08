import pytest

from pathlib import Path
from common.user_config import UserConfig


FIXTURES_DIR = str(Path(__file__).parent / "fixtures")

_S3_TABLE = {"name": "t", "prefix": "data/", "file_format": "Parquet", "full_refresh": True}

_S3_YAML = """
name: my_source
source_type: "s3"
s3_config:
  bucket: test-bucket
  disable_auth: true
  tables:
    - name: t
      prefix: "data/"
      file_format: Parquet
      full_refresh: true
"""


class TestUserConfigLoading:
    @pytest.fixture
    def config(self):
        return UserConfig(config_dir=FIXTURES_DIR)

    def test_loads_ingestion_configs(self, config: UserConfig):
        assert len(config.ingestion) == 1

    def test_empty_config_dir(self, tmp_path: Path):
        (tmp_path / "ingestion").mkdir()
        config = UserConfig(config_dir=str(tmp_path))
        assert config.ingestion == []

    def test_application_field_from_filename_stem(self, tmp_path: Path):
        ingestion_dir = tmp_path / "ingestion"
        ingestion_dir.mkdir()
        (ingestion_dir / "noaa-ghcn.yml").write_text(_S3_YAML.replace("my_source", "noaa_ghcn"))

        config = UserConfig(config_dir=str(tmp_path))
        [ingestion] = config.ingestion
        assert ingestion.application == "noaa-ghcn"

    def test_discovers_yaml_extension(self, tmp_path: Path):
        ingestion_dir = tmp_path / "ingestion"
        ingestion_dir.mkdir()
        (ingestion_dir / "source_a.yml").write_text(_S3_YAML.replace("my_source", "source_a"))
        (ingestion_dir / "source_b.yaml").write_text(_S3_YAML.replace("my_source", "source_b"))

        config = UserConfig(config_dir=str(tmp_path))
        names = {c.name for c in config.ingestion}
        assert names == {"source_a", "source_b"}

    def test_skips_empty_yaml_files(self, tmp_path: Path):
        ingestion_dir = tmp_path / "ingestion"
        ingestion_dir.mkdir()
        (ingestion_dir / "empty.yml").write_text("")
        (ingestion_dir / "real.yml").write_text(_S3_YAML)

        config = UserConfig(config_dir=str(tmp_path))
        assert len(config.ingestion) == 1
        assert config.ingestion[0].name == "my_source"