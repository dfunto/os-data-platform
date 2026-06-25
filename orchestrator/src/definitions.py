import dagster as dg

from assets.ingestion import build_ingestion_asset
from common.user_config import UserConfig


user_config = UserConfig(config_dir="./configuration")
assets = [
    *[build_ingestion_asset(config) for config in user_config.ingestion]
]
defs = dg.Definitions(assets=assets)
