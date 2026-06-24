import re
import pulumi_kubernetes as k8s

from abc import ABC

from common.user_config import UserConfig


SECRET_PATTERN = re.compile(r"^secret:(.+)/(.+)/(.+)$")


class BaseStack(ABC):

    _secret_cache: dict = {}

    def __init__(
        self,
        workspace_id: str,
        user_config: UserConfig
    ):
        self.workspace_id = workspace_id
        self.user_config = user_config

    @staticmethod
    def _read_k8s_secret(namespace: str, secret_name: str, secret_key: str):
        cache_key = f"{namespace}/{secret_name}"
        if cache_key not in BaseStack._secret_cache:
            BaseStack._secret_cache[cache_key] = k8s.core.v1.Secret.get(
                resource_name=secret_name,
                id=cache_key
            )
        secret = BaseStack._secret_cache[cache_key]
        return secret.data[secret_key].apply(
            lambda v: __import__("base64").b64decode(v).decode("utf-8")
        )

    @staticmethod
    def resolve_secrets(data):
        if isinstance(data, str):
            if match := SECRET_PATTERN.match(data):
                return BaseStack._read_k8s_secret(*match.groups())
            return data
        if isinstance(data, dict):
            return {k: BaseStack.resolve_secrets(v) for k, v in data.items()}
        if isinstance(data, list):
            return [BaseStack.resolve_secrets(v) for v in data]
        return data
