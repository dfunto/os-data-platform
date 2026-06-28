import base64
from enum import Enum
from functools import cached_property
from pydantic import BaseModel, computed_field, model_validator


class IngestionSourceType(Enum):
    S3 = "s3"
    AIRBYTE = "airbyte"


class ClickHouseFileFormat(Enum):
    PARQUET = "Parquet"
    CSV = "CSV"
    CSV_WITH_NAMES = "CSVWithNames"
    TSV = "TabSeparated"
    JSON_EACH_ROW = "JSONEachRow"
    AVRO = "Avro"
    ORC = "ORC"
    ARROW = "Arrow"
    REGEXP = "Regexp"
    LINE_AS_STRING = "LineAsString"


class ColumnDefinition(BaseModel):
    name: str
    type: str = "String"
    expression: str | None = None


class IngestionS3TableConfig(BaseModel):
    name: str
    description: str | None = None
    prefix: str
    file_format: ClickHouseFileFormat
    full_refresh: bool = False
    columns: list[ColumnDefinition] | None = None
    settings: dict[str, str] | None = None


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
        return self.k8s_secret_data[self.k8s_secret_aws_key]

    @computed_field
    @property
    def aws_secret_access_key(self) -> str:
        return self.k8s_secret_data[self.k8s_secret_aws_secret]


