import pulumi

from common.user_config import UserConfig
from stack.ingestion import IngestionStack


def main():
    pulumi_config = pulumi.Config()
    workspace_id = pulumi_config.require("workspaceId")
    user_config = UserConfig(config_dir="../configuration")
    stack_config = {
        "user_config": user_config,
        "workspace_id": workspace_id
    }
    IngestionStack(**stack_config).register()


if __name__ == "__main__":
    main()
