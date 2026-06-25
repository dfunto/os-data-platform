import dagster as dg

from common.user_config import UserConfig
from assets.ingestion import build_ingestion_assets
from resources.lakehouse import LakehouseResource


user_config = UserConfig(config_dir="./configuration")
assets: list[dg.AssetsDefinition] = [
    asset
    for config in user_config.ingestion
    for asset in build_ingestion_assets(config)
]
resources: dict[str, dg.ConfigurableResource] = {
    "lakehouse": LakehouseResource()
}

defs = dg.Definitions(
    assets=assets,
    resources=resources
)
