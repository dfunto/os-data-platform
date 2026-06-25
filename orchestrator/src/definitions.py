import dagster as dg

from common.user_config import UserConfig
from assets.ingestion import build_ingestion_asset
from resources.lakehouse import LakehouseResource


user_config = UserConfig(config_dir="./configuration")
assets: list[dg.AssetsDefinition] = [
    *[build_ingestion_asset(config) for config in user_config.ingestion]
]
resources: dict[str, dg.ConfigurableResource] = {
    "raw": LakehouseResource(layer="raw")
}

defs = dg.Definitions(
    assets=assets,
    resources=resources
)
