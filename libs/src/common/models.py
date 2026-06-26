import base64
from abc import ABC
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import ClassVar
from pydantic import BaseModel, computed_field, model_validator


class CapabilityConfig(BaseModel, ABC):
    file_path: Path
    capability_name: ClassVar[str]


class LakehouseLayer(Enum):
    RAW = "raw"
    CLEANSED = "cleansed"
    CURATED = "curated"

    @property
    def bucket(self):
        return f"lakehouse-{self.value}"


class IngestionSourceType(Enum):
    S3 = "s3"
    AIRBYTE = "airbyte"


class IngestionS3TableConfig(BaseModel):
    name: str
    prefix: str
    file_format: str


class IngestionS3Config(BaseModel):
    bucket: str
    k8s_secret: str
    k8s_secret_aws_key: str
    k8s_secret_aws_secret: str
    tables: list[IngestionS3TableConfig]

    @computed_field
    @cached_property
    def k8s_secret_data(self) -> dict[str, str]:
        from kubernetes import client, config

        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
            configuration = client.Configuration.get_default_copy()
            configuration.host = configuration.host.replace("127.0.0.1", "host.docker.internal")
            configuration.verify_ssl = False
            client.Configuration.set_default(configuration)

        namespace, name = self.k8s_secret.split("/")
        secret = client.CoreV1Api().read_namespaced_secret(name, namespace)
        return {k: base64.b64decode(v).decode() for k, v in secret.data.items()}

    @computed_field
    @property
    def aws_access_key_id(self) -> str:
        return self.k8s_secret_data[self.k8s_secret_aws_key]

    @computed_field
    @property
    def aws_secret_access_key(self) -> str:
        return self.k8s_secret_data[self.k8s_secret_aws_secret]


class IngestionConfig(CapabilityConfig):
    capability_name: ClassVar[str] = "ingestion"
    name: str
    source_type: IngestionSourceType
    s3_config: IngestionS3Config | None = None
    airbyte_config: dict | None = None

    @model_validator(mode="after")
    def validate_config_matches_source(self):
        config_map = {
            IngestionSourceType.S3: "s3_config",
            IngestionSourceType.AIRBYTE: "airbyte_config",
        }
        field = config_map[self.source_type]
        if getattr(self, field) is None:
            raise ValueError(f"source_type '{self.source_type.value}' requires {field}")
        return self

    @computed_field
    def application(self) -> str:
        return self.file_path.stem
