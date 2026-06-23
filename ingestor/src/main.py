import json
import pulumi
import pulumi_airbyte as airbyte

from common.config import Config

pulumi_config = pulumi.Config()
workspace_id = pulumi_config.require("workspaceId")

config = Config(config_dir="../configuration")


s3_source = airbyte.Source(
    "source_naturalearth",
    name="naturalearth",
    workspace_id=workspace_id,
    configuration=json.dumps({
      "configuration": {
        "format": {
          "filetype": "parquet",
        },
        "bucket": "naturalearth",
        "streams": [
          {
            "name": "cultural",
            "globs": ["10m_cultural/**"],
            "format": {
              "filetype": "parquet",
            },
            "validation_policy": "Emit Record",
            "days_to_sync_if_history_is_full": 3,
          }
        ],
        "delivery_method": {
          "delivery_type": "use_records_transfer"
        },
      }
    })
)