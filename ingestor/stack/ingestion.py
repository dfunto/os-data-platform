import json
import pulumi

import pulumi_airbyte as airbyte

from stack.base import BaseStack


class IngestionStack(BaseStack):

    def parse_configuration(self, source_type: str, config: dict):
        resolved = self.resolve_secrets(config)
        return pulumi.Output.all(**resolved).apply(
            lambda args: json.dumps({"sourceType": source_type, **args})
        )

    def register(self):
        for ingestion in self.user_config.ingestion:
            source_name = f"source_{ingestion.name}"
            airbyte.Source(
                source_name,
                name=source_name,
                workspace_id=self.workspace_id,
                configuration=self.parse_configuration(
                    source_type=ingestion.source_type,
                    config=ingestion.config
                )
            )
