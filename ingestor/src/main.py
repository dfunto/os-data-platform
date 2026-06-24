import json
import pulumi
import pulumi_airbyte as airbyte

from common.config import Config

pulumi_config = pulumi.Config()
workspace_id = pulumi_config.require("workspaceId")

config = Config(config_dir="../configuration")


s3_source = airbyte.Source(
    "source_source1",
    name="table1",
    workspace_id=workspace_id,
    configuration=json.dumps({
      "configuration": {
        "format": {
          "filetype": "parquet",
        },
        "bucket": "temp-test-oss-data-platform",
        "streams": [
          {
            "name": "source1_table1",
            "globs": ["source1/table1/**"],
            "format": {
              "filetype": "parquet",
            },
          }
        ]
      }
    })
)