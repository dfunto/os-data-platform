# os-data-platform

Open source data platform built on Kubernetes with ingestion, transformation, and warehouse layers.

## Goal

Full data platform using only OSS: Kubernetes, S3, Apache Hudi, Spark, Dagster, Trino, ClickHouse, Kafka. Airbyte for ingestion (TBD).

## Repo Structure

```
configuration/                          # User-defined YAML configs (mounted into orchestrator container)
  ingestion/
    source1.yml                         # Per-source ingestion config (name, source_type, s3_config, tables)

libs/                                   # Shared Python library ("common" package)
  src/common/
    __init__.py
    models.py                           # Pydantic models: IngestionConfig, IngestionS3Config, IngestionS3TableConfig, LakehouseLayer, etc.
    user_config.py                      # UserConfig class: loads YAML configs from configuration/ dir by capability
  tests/
    fixtures/ingestion/example.yml
    test_config.py
  pyproject.toml

orchestrator/                           # Dagster user code
  src/
    definitions.py                      # Entry point: loads UserConfig, builds ingestion + transform assets, registers Definitions
    assets/
      ingestion.py                      # IngestionAssetBuilder (ABC) + factory get_builder()
      ingestion_s3.py                   # S3IngestionAssetBuilder: copies S3 files to SeaweedFS lakehouse
      transform.py                      # SQLMesh integration: dagster-sqlmesh assets with custom translator
    resources/
      lakehouse.py                      # LakehouseResource (extends S3Resource): boto3 client to SeaweedFS
      warehouse.py                      # WarehouseResource: ClickHouse connection
  docker-compose.yml                    # Local dev: postgres, user_code, webserver, daemon
  dagster.yaml                          # Dagster instance config (postgres storage)
  workspace.yaml                        # gRPC server: host=user_code, port=3030
  pyproject.toml                        # Deps: dagster, dagster-sqlmesh, sqlmesh[clickhouse], common (path=../libs)
  Dockerfile
  .env                                  # Local env vars (not committed secrets)
  .python-version                       # Python >= 3.12

transform/                              # SQLMesh project (transformation layer)
  config.yaml                           # SQLMesh config: ClickHouse connection + Postgres state backend
  models/
    cleansed/                           # Cleansed layer models (FULL kind, reading from raw.*)
      noaa_ghcn_countries.sql
      noaa_ghcn_states.sql
      noaa_ghcn_stations.sql
      noaa_ghcn_inventory.sql
  pyproject.toml                        # Deps: sqlmesh[clickhouse], psycopg2-binary
  .python-version                       # Python >= 3.12

helm/                                   # Helm charts and values for K8s
  orchestrator/values.yaml              # Dagster Helm values
  warehouse/                            # ClickHouse warehouse chart
    Chart.yaml
    values.yaml                         # ClickHouse config: shards, replicas, initSQL (raw/cleansed/curated DBs)
    templates/
      clickhouse-cluster.yaml           # ClickHouseCluster CR with S3 named collection mount
      keeper-cluster.yaml               # ClickHouse Keeper cluster
      lakehouse-config.yaml             # ConfigMap: S3 named collection XML (seaweedfs -> SeaweedFS endpoint)
      warehouse-init-job.yaml           # Helm hook Job: runs initSQL via clickhouse-client
      _helpers.tpl
  README.md
```

## Asset Pipeline

The platform defines three asset groups forming a lineage:

1. **Ingestion** (`ingest_*` assets) — copies files from source S3 buckets into SeaweedFS lakehouse
2. **Raw** (`raw_*` assets) — creates ClickHouse tables from ingested files
3. **Cleansed** (`cleansed_*` assets) — SQLMesh models that transform raw tables into cleansed tables

## Orchestrator (Dagster)

- Python package in `orchestrator/`, requires Python >= 3.12
- Deps on `common` library via `libs/` (path dependency)
- Entry point: `src/definitions.py` — loads `UserConfig` from `./configuration`, builds ingestion + transform assets
- Ingestion: `IngestionAssetBuilder.get_builder(config)` dispatches by `source_type` (S3, Airbyte)
- S3 ingestion: reads from source S3 bucket, copies files to SeaweedFS lakehouse (`lakehouse-raw` bucket)
- Transform: `dagster-sqlmesh` integration via `build_transform_assets()` in `assets/transform.py`
  - Custom `SQLMeshDagsterTranslator` flattens FQNs (e.g., `raw.table` -> `raw_table`) to link SQLMesh deps to ingestion assets
  - Custom `SQLMeshContextConfig` subclass provides the translator
  - Runs against SQLMesh `prod` environment
- Credentials: fetched from K8s secrets at runtime (configured per source in YAML)
- Dagster served via gRPC on port 3030
- Docker image: `dadutra2/os-data-platform-orchestrator:latest`
- Local dev: `docker-compose.yml` (postgres + user_code + webserver + daemon), mounts `../configuration` and `../transform`

## Transform (SQLMesh)

- SQLMesh project in `transform/`, requires Python >= 3.12
- Dialect: ClickHouse
- Gateway: `clickhouse` (ClickHouse for execution, Postgres for state)
- Connection hosts configurable via env vars: `SQLMESH_CLICKHOUSE_HOST`, `SQLMESH_POSTGRES_HOST` (default: `localhost`)
- State DB password via `OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD`
- Models in `models/cleansed/` read from `raw.*` tables and write to `cleansed.*`
- Integrated into Dagster via `dagster-sqlmesh` — cleansed assets depend on raw ingestion assets
- Can run standalone: `sqlmesh plan` / `sqlmesh run` from `transform/` directory

## Helm / K8s Deployment

Namespace: `os-data-platform`

Deploy command:
```shell
helm install dagster dagster/dagster -f helm/orchestrator/values.yaml -n os-data-platform --create-namespace
```

Key values in `helm/orchestrator/values.yaml`:
- Bundled PostgreSQL enabled (user/pass/db: `dagster`)
- Secret: `dagster-postgresql-secret`
- User deployment: image `dadutra2/os-data-platform-orchestrator:latest`, gRPC args point to `src/definitions.py`
- Webserver: 1 replica, ingress disabled
- Daemon: enabled
- Telemetry: disabled

Access UI:
```shell
kubectl port-forward svc/dagster-dagster-webserver 3000:80 -n dagster
# UI at http://localhost:3000
```

## Warehouse (ClickHouse)

- Deployed via custom Helm chart in `helm/warehouse/`
- Uses ClickHouse Operator (`clickhouse.com/v1alpha1` CRDs)
- S3 named collection `seaweedfs` configured via ConfigMap (points to SeaweedFS S3 endpoint)
- Init SQL creates databases: `raw`, `cleansed`, `curated`
- Keeper cluster for coordination
