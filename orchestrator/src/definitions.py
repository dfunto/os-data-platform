import dagster as dg

from common.user_config import UserConfig
from assets.ingestion import IngestionAssetBuilder
from resources.lakehouse import LakehouseResource
from resources.warehouse import WarehouseResource

user_config = UserConfig(config_dir="./configuration")
assets: list[dg.AssetsDefinition] = [
    asset
    for config in user_config.ingestion
    for asset in IngestionAssetBuilder.get_builder(config).build()
]
resources: dict[str, dg.ConfigurableResource] = {
    "lakehouse": LakehouseResource(),
    "warehouse": WarehouseResource()
}

defs = dg.Definitions(
    assets=assets,
    resources=resources,
)
