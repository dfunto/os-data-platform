import pytest

from pathlib import Path
from common.config import Config


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestConfig:

    @pytest.fixture
    def config(self):
        return Config(config_dir=FIXTURES_DIR)

    def test_loads_ingestion_configs(self, config: Config):
        assert len(config.ingestion) == 1
        print(config.ingestion)

    def test_empty_config_dir(self, tmp_path: Path):
        (tmp_path / "ingestion").mkdir()
        config = Config(config_dir=tmp_path)
        assert config.ingestion == []
