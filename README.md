# Open Source Data Platform

> **Work in Progress** — This project is under active development. Ingestion and transformation layers are functional. Scheduling, monitoring, and curated layer capabilities are not yet implemented.

An open-source data platform built entirely on Kubernetes using free and open-source software. Designed for teams that want full ownership of their data stack without vendor lock-in.


## Roadmap

- Ingest API data
- Ingest CDC data
- Ingest realtime data
- Realtime data transformation
- Realtime dashboard
- Machine learning capability


## Architecture

```mermaid
graph TB
    subgraph Sources
        S3["Source S3 Buckets"]
        API["APIs / SaaS / CDC"]
    end

    subgraph K8s["Kubernetes Cluster"]
        subgraph Orchestration
            Dagster["Dagster<br/><i>orchestrator</i><br/>webserver / daemon / user code"]
        end

        subgraph Storage
            SeaweedFS["SeaweedFS<br/><i>lakehouse</i><br/>lakehouse-raw / cleansed / curated"]
        end

        subgraph Warehouse
            ClickHouse["ClickHouse<br/><i>warehouse</i><br/>raw DB → cleansed DB → curated DB"]
        end

        subgraph Reporting
            Superset["Apache Superset<br/><i>reporting</i><br/>dashboards / SQL editor"]
        end

        subgraph Metadata
            Postgres["PostgreSQL<br/><i>metadata</i>"]
        end
    end

    subgraph Transform
        dbt["dbt<br/><i>transform</i><br/>cleansed / curated models"]
    end

    S3 -- "S3 copy<br/>(Dagster asset)" --> SeaweedFS
    API -- "dlt pipeline<br/>(Dagster asset)" --> Dagster
    Dagster -- "Copies files" --> SeaweedFS
    Dagster -- "CREATE TABLE<br/>(SQL)" --> ClickHouse
    Dagster -- "dlt load<br/>(REST → raw)" --> ClickHouse
    SeaweedFS -- "S3 engine<br/>(reads in-place)" --> ClickHouse
    Dagster -- "dagster-dbt" --> dbt
    dbt -- "raw → cleansed<br/>(SQL)" --> ClickHouse
    Superset -- "Queries" --> ClickHouse
    Postgres -. "metadata" .-> Dagster
    Postgres -. "metadata" .-> Superset
```

### Data Flow

1. **Ingestion** - Two paths based on source type:
   - **File sources (S3)**: Dagster copies files byte-for-byte from source S3 buckets into SeaweedFS `lakehouse-raw` bucket
   - **API sources**: Dagster runs `dlt` pipelines that fetch from REST APIs (auth, pagination) and load directly into the ClickHouse `raw` database
2. **Raw table creation** - For file sources, Dagster creates ClickHouse tables using the S3 engine, pointing directly at raw parquet files in SeaweedFS. API sources are materialized straight into `raw` tables by `dlt`.
3. **Transformation** - dbt models (orchestrated by Dagster via `dagster-dbt`) transform data through `raw` -> `cleansed` -> `curated` databases in ClickHouse

### Lakehouse Layers

| Layer | SeaweedFS Bucket | ClickHouse DB | Purpose |
|-------|-----------------|---------------|---------|
| Raw | `lakehouse-raw` | `raw` | Source files as-is, indefinite retention |
| Cleansed | `lakehouse-cleansed` | `cleansed` | Validated, deduplicated, typed |
| Curated | `lakehouse-curated` | `curated` | Business-ready, aggregated |

## Tech Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Orchestration | [Dagster](https://dagster.io) | Pipeline scheduling, asset management, observability |
| Transformation | [dbt](https://www.getdbt.com) | SQL-based data transformations (ClickHouse adapter) |
| Warehouse | [ClickHouse](https://clickhouse.com) | Columnar OLAP database with S3 engine |
| Object Storage | [SeaweedFS](https://github.com/seaweedfs/seaweedfs) | S3-compatible distributed storage (lakehouse) |
| Ingestion | [dlt](https://dlthub.com) | Config-driven REST API ingestion (`api` source type), loads into ClickHouse |
| Reporting | [Apache Superset](https://superset.apache.org) | BI dashboards, SQL editor, chart explorer |
| Metadata DB | [PostgreSQL](https://postgresql.org) | Shared metadata store for Dagster and Superset |
| Deployment | [Kubernetes](https://kubernetes.io) + [Helm](https://helm.sh) | Container orchestration and declarative deployment |
| Shared Library | Python / [Pydantic](https://docs.pydantic.dev) | Config models, validation, K8s secret loading |

## Project Structure

```
os-data-platform/
├── configuration/                  # User-defined YAML configs (mounted into containers)
│   └── ingestion/
│       └── source1.yml             # Per-source ingestion config
│
├── libs/                           # Shared Python library ("common" package)
│   ├── src/common/
│   │   ├── models/
│   │   │   ├── core.py             # IngestionConfig, LakehouseLayer, CapabilityConfig
│   │   │   └── ingestion.py        # S3-specific models, K8s secret resolution
│   │   └── user_config.py          # Loads YAML configs by capability type
│   ├── tests/
│   └── pyproject.toml
│
├── orchestrator/                   # Dagster user code
│   ├── src/
│   │   ├── definitions.py          # Entry point: builds ingestion + transform assets, registers Definitions
│   │   ├── assets/
│   │   │   ├── ingestion.py        # Abstract builder + factory (dispatches by source_type)
│   │   │   ├── ingestion_s3.py     # S3 ingestion: copy to lakehouse + create raw table
│   │   │   ├── ingestion_api.py    # API ingestion: dlt REST pipelines -> ClickHouse raw
│   │   │   └── transform.py        # dbt integration: dagster-dbt assets with custom translator
│   │   ├── resources/
│   │   │   ├── lakehouse.py        # SeaweedFS S3 client (extends dagster-aws S3Resource)
│   │   │   └── warehouse.py        # ClickHouse client (extends dagster-clickhouse)
│   │   └── sql/
│   │       └── ingestion/
│   │           └── create_raw_table.sql  # Jinja2 template for ClickHouse S3 engine tables
│   ├── docker-compose.yml          # Local dev environment
│   ├── Dockerfile
│   └── pyproject.toml
│
├── transform/                      # dbt project (transformation layer)
│   ├── dbt_project.yml             # dbt config: cleansed -> table, seeds -> raw schema
│   ├── profiles.yml                # ClickHouse connection (env-var driven)
│   ├── macros/                     # generate_schema_name (raw/cleansed verbatim)
│   ├── models/
│   │   ├── sources.yml             # raw.* external tables from ingestion
│   │   └── cleansed/noaa_ghcn/     # Cleansed models (table / view / incremental)
│   ├── seeds/                      # Flag lookup CSVs -> raw schema
│   └── pyproject.toml
│
├── helm/                           # Helm charts and values for K8s deployment
│   ├── metadata/values.yaml        # PostgreSQL (bitnami)
│   ├── storage/                    # SeaweedFS chart wrapper
│   ├── orchestrator/values.yaml    # Dagster (official chart)
│   ├── operators/                  # ClickHouse operator
│   ├── warehouse/                  # ClickHouse cluster (custom chart)
│   ├── reporting/values.yaml       # Apache Superset
│   └── README.md                   # Full deployment runbook
│
├── CLAUDE.md                       # AI assistant context
├── LICENSE                         # GPLv3
└── .gitignore
```

## Quick Start

### Prerequisites

- Python >= 3.12
- Docker + Docker Compose (local dev)
- Kubernetes cluster + Helm (production)

### Kubernetes Deployment

See [helm/README.md](helm/README.md) for the full deployment runbook including secrets setup and install order.

### Local Development

You need the kubernetes deployments done in order to run any data pipelines

```shell
cd orchestrator

# Start all Dagster services (postgres, user_code, webserver, daemon)
docker-compose up -d

# Dagster UI at http://localhost:3000

# Validate definitions
docker-compose exec user_code dagster definitions validate -m src.definitions

# Materialize a specific asset
docker-compose exec user_code dagster asset materialize --select ingest_source1_table1 -m src.definitions
```

## Configuration

Ingestion sources are defined as YAML files in `configuration/ingestion/`. Each file describes one source:

```yaml
# configuration/ingestion/source1.yml
name: source1
source_type: "s3"
s3_config:
  bucket: my-source-bucket
  k8s_secret: "os-data-platform/my-aws-secret"
  k8s_secret_aws_key: "key"
  k8s_secret_aws_secret: "secret"
  tables:
    - name: table1
      prefix: "source1/table1/**"
      file_format: parquet
```

Dagster auto-discovers these configs at startup and generates assets per table:
- `ingest_{source}_{table}` - copies files from source S3 to SeaweedFS raw bucket
- `raw_{source}_{table}` - creates a ClickHouse table pointing at the raw files via S3 engine
- `cleansed_{source}_{table}` - dbt models that transform raw tables into cleansed tables (auto-discovered from `transform/models/`)

## Design Decisions

### Ingestion Strategy: dlt for APIs, Direct Copy for Files

**Decision:** Use `dlt` pipelines (the `api` source type) for REST API sources.
Use direct S3 copy + ClickHouse S3 engine for file-based sources.

**Context:** File-based and API sources have opposite needs.
File sources are already accessible parquet in S3 and should be preserved as-is.
API sources need HTTP fetching, pagination, and typing before they can be queried, and there is no source file to preserve.

**Rationale:**
- **Raw layer preservation:** For files, the raw layer should stay as close to original as possible, so a byte-for-byte copy is used rather than any deserialize/re-serialize step.
- **Right tool for the job:** `dlt` handles auth, pagination, and schema inference for REST APIs with a small, config-driven footprint (no separate service to run).
- **No unnecessary hops:** API data has no source file worth staging in SeaweedFS, so `dlt` loads it straight into the ClickHouse `raw` database.
- **Config-driven:** Adding an API source is pure YAML (`url`, `primary_key`, request `params`); no per-source Python is required.

**Consequences:**
- Two ingestion paths to orchestrate, both as Dagster assets built by `IngestionAssetBuilder` and dispatched by `source_type`.
- File sources: Dagster copies to the raw bucket, and ClickHouse reads the parquet in-place via the S3 engine / named collection.
- API sources: Dagster runs a `dlt` pipeline that loads directly into ClickHouse `raw` (dlt is the internal load engine; the platform exposes it as the `api` source type).

### Raw Layer as Safety Net

**Decision:** All ingestion (file-based or connector-based) lands in a raw S3 bucket with indefinite retention before loading to ClickHouse.

**Context:** Source systems may have short data retention. Schema changes or pipeline failures can prevent data from loading into the warehouse. Without a raw layer, data loss is permanent.

**Rationale:**
- Decouples ingestion from transformation -- if ClickHouse load fails, raw data is safe.
- Engineers have time to investigate and fix schema issues without data loss pressure.
- Enables replay and backfill from raw at any time.
- Provides audit trail of what arrived and when.

**Consequences:**
- Additional S3 storage cost (acceptable trade-off for data safety).
- Pipeline pattern: `source -> raw S3 -> validate/transform -> ClickHouse`.

### Config-Driven Asset Generation

**Decision:** Define ingestion sources as YAML files. Dagster generates assets dynamically at startup from these configs.

**Rationale:**
- Adding a new source requires zero Python code -- just a YAML file.
- Builder pattern (`IngestionAssetBuilder`) dispatches to the right implementation by `source_type`.
- Pydantic models validate config structure before any asset runs.
- Credentials are resolved at runtime from K8s secrets, never stored in YAML.

### SeaweedFS over MinIO

**Decision:** Use SeaweedFS as the S3-compatible object store instead of MinIO.

**Rationale:**
- SeaweedFS handles small-to-medium file workloads efficiently with its volume-based architecture.
- Dagster connects via the standard S3 API -- the backing store is transparent.
- Avoids MinIO licensing concerns for production use.

### ClickHouse S3 Engine for Raw Tables

**Decision:** Raw ClickHouse tables use the S3 engine with named collections to read directly from SeaweedFS.

**Rationale:**
- No data duplication -- ClickHouse reads parquet files in-place from the lakehouse.
- Named collection (`seaweedfs`) centralizes S3 endpoint and credentials as a ClickHouse config.
- Schema changes in source files are handled by recreating the table definition, not re-ingesting data.
- Jinja2 SQL templates (`create_raw_table.sql`) keep table creation DRY and parameterized.

## License

[GPLv3](LICENSE)