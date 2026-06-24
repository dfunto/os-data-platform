import pytest

from pathlib import Path
from common.user_config import UserConfig


FIXTURES_DIR = str(Path(__file__).parent / "fixtures")


class TestConfig:

    @pytest.fixture
    def config(self):
        return UserConfig(config_dir=FIXTURES_DIR)

    def test_loads_ingestion_configs(self, config: UserConfig):
        assert len(config.ingestion) == 1

    def test_empty_config_dir(self, tmp_path: Path):
        (tmp_path / "ingestion").mkdir()
        config = UserConfig(config_dir=str(tmp_path))
        assert config.ingestion == []
