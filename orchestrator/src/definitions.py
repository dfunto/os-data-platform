import dagster as dg
from dagster_sqlmesh import SQLMeshResource

from common.user_config import UserConfig
from assets.ingestion import IngestionAssetBuilder
from assets.transform import build_transform_assets
from resources.lakehouse import LakehouseResource
from resources.warehouse import WarehouseResource

user_config = UserConfig(config_dir="./configuration")
ingestion_assets: list[dg.AssetsDefinition] = [
    asset
    for config in user_config.ingestion
    for asset in IngestionAssetBuilder.get_builder(config).build()
]
transform_assets = build_transform_assets()

resources: dict[str, dg.ConfigurableResource] = {
    "lakehouse": LakehouseResource(),
    "warehouse": WarehouseResource(),
    "sqlmesh": SQLMeshResource(),
}

defs = dg.Definitions(
    assets=[
        *ingestion_assets,
        transform_assets
    ],
    resources=resources,
)
