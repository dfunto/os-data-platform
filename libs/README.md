# Common Library (`libs`)

Shared Python library providing Pydantic configuration models and YAML config loading for the platform. Published as the `common` package.

## What It Does

1. **Defines data models** - Pydantic models for ingestion configs, lakehouse layers, source types
2. **Loads user configuration** - Reads YAML files from `configuration/` directory, validates them, and returns typed config objects
3. **Resolves K8s secrets** - S3 ingestion configs reference Kubernetes secrets by name; credentials are fetched at runtime

## Structure

```
libs/
├── src/common/
│   ├── __init__.py
│   ├── models/
│   │   ├── core.py             # CapabilityConfig, LakehouseLayer, IngestionConfig
│   │   └── ingestion.py        # IngestionSourceType, IngestionS3Config, IngestionS3TableConfig
│   └── user_config.py          # UserConfig: loads YAML configs by capability
├── tests/
│   ├── test_config.py
│   └── fixtures/ingestion/example.yml
└── pyproject.toml
```

## Key Models

### `IngestionConfig` (core.py)

Top-level config for one ingestion source. Dispatches to source-specific config based on `source_type`.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Source identifier |
| `source_type` | `IngestionSourceType` | `s3` or `airbyte` |
| `s3_config` | `IngestionS3Config` | Required when `source_type = s3` |
| `airbyte_config` | `dict` | Reserved for Airbyte (not yet implemented) |
| `file_path` | `Path` | Auto-set from YAML file location |
| `application` | `str` (computed) | Stem of the YAML filename |

### `IngestionS3Config` (ingestion.py)

S3-specific config with K8s secret resolution for credentials.

| Field | Type | Description |
|-------|------|-------------|
| `bucket` | `str` | Source S3 bucket name |
| `k8s_secret` | `str` | K8s secret reference (`namespace/name`) |
| `k8s_secret_aws_key` | `str` | Key within the secret for access key ID |
| `k8s_secret_aws_secret` | `str` | Key within the secret for secret access key |
| `tables` | `list[IngestionS3TableConfig]` | Tables to ingest |

Credentials (`aws_access_key_id`, `aws_secret_access_key`) are computed fields that read from the K8s secret at access time. Supports both in-cluster and local kubeconfig.

### `LakehouseLayer` (core.py)

Enum mapping layer names to SeaweedFS bucket names:
- `RAW` -> `lakehouse-raw`
- `CLEANSED` -> `lakehouse-cleansed`
- `CURATED` -> `lakehouse-curated`

### `UserConfig` (user_config.py)

Loads all YAML files under `configuration/{capability}/` and returns validated Pydantic model instances. Currently supports `ingestion` capability. New capabilities are added by creating a new `CapabilityConfig` subclass with a `capability_name`.

## Usage

```python
from common.user_config import UserConfig
from common.models.core import IngestionConfig

config = UserConfig(config_dir="./configuration")

for ingestion in config.ingestion:
    print(ingestion.name, ingestion.source_type)
    if ingestion.s3_config:
        for table in ingestion.s3_config.tables:
            print(f"  {table.name}: {table.prefix}")
```

## Development

```shell
cd libs

# Install with dev deps
pip install -e ".[dev]"

# Run tests
pytest
```

## Dependencies

- `pydantic` - model validation
- `pyyaml` - YAML parsing
- `kubernetes` - K8s API client for secret resolution
- `croniter` - cron expression support
