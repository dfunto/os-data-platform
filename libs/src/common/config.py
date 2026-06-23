import yaml

from functools import cached_property
from pathlib import Path
from typing import TypeVar

from common.models import IngestionConfig, CapabilityConfig


T = TypeVar("T", bound=CapabilityConfig)


class Config:

    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)
        if not self.config_dir.is_dir():
            raise ValueError(f"config_dir not found: {config_dir}")

    @cached_property
    def ingestion(self) -> list[IngestionConfig]:
        return self._load_capability(config_class=IngestionConfig)

    def _load_capability(self, config_class: type[T]) -> list[T]:
        config = []
        capability: str = config_class.capability_name
        for file in self.config_dir.rglob(f"{capability}/*.y*ml"):
            data = yaml.safe_load(file.read_text())
            if not data or capability not in data:
                continue

            config.extend([
                config_class(**{
                    "file_path": file,
                    **entry
                })
                for entry in data[capability]
            ])
        return config
