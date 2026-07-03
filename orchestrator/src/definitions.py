import dagster as dg
from dagster_dbt import DbtCliResource

from common.user_config import UserConfig
from assets.ingestion import IngestionAssetBuilder
from assets.transform import build_transform_assets, dbt_project
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
    "dbt": DbtCliResource(project_dir=dbt_project),
}

automation_sensor = dg.AutomationConditionSensorDefinition(
    "automation_condition_sensor",
    target=dg.AssetSelection.all(),
    default_status=dg.DefaultSensorStatus.RUNNING,
)

defs = dg.Definitions(
    assets=[
        *ingestion_assets,
        *transform_assets
    ],
    sensors=[automation_sensor],
    resources=resources,
)
