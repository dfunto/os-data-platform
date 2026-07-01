import base64
from functools import cached_property

from pydantic import BaseModel, model_validator, computed_field

from common.models.ingestion import ClickHouseFileFormat, ColumnDefinition, IngestionTableConfig


class IngestionS3TableConfig(IngestionTableConfig):
    prefix: str
    file_format: ClickHouseFileFormat
    full_refresh: bool = False
    columns: list[ColumnDefinition] | None = None
    settings: dict[str, str] | None = None

    def get_source_prefix(self, partition_params: dict[str, str] | None = None) -> str:
        base = self.prefix.removesuffix("/*").removesuffix("*")
        if partition_params:
            suffix = "/".join(f"{k}={v}" for k, v in partition_params.items())
            return f"{base}{suffix}"
        return base

    def get_target_prefix(self, source_name: str, partition_params: dict[str, str] | None = None) -> str:
        base = f"{source_name}/{self.name}"
        if partition_params:
            suffix = "/".join(f"{k}={v}" for k, v in partition_params.items())
            return f"{base}/{suffix}"
        return base


class IngestionS3Config(BaseModel):
    bucket: str
    disable_auth: bool = False
    full_refresh: bool = False
    k8s_secret: str | None = None
    k8s_secret_aws_key: str | None = None
    k8s_secret_aws_secret: str | None = None
    tables: list[IngestionS3TableConfig]

    @model_validator(mode="after")
    def validate_auth_config(self):
        if not self.disable_auth:
            missing = [f for f in ("k8s_secret", "k8s_secret_aws_key", "k8s_secret_aws_secret")
                       if getattr(self, f) is None]
            if missing:
                raise ValueError(f"When disable_auth is false, these fields are required: {', '.join(missing)}")
        return self

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
        if not self.k8s_secret_aws_key:
            raise ValueError("Missing s3_config property 'k8s_secret_aws_key'")
        return self.k8s_secret_data[self.k8s_secret_aws_key]

    @computed_field
    @property
    def aws_secret_access_key(self) -> str:
        if not self.k8s_secret_aws_secret:
            raise ValueError("Missing s3_config property 'k8s_secret_aws_secret'")
        return self.k8s_secret_data[self.k8s_secret_aws_secret]
