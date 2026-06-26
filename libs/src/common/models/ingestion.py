import base64
from enum import Enum
from functools import cached_property
from pydantic import BaseModel, computed_field


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


