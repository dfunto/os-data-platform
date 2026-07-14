# os-data-platform

Open source data platform built on Kubernetes with ingestion, transformation, and warehouse layers.

## Goal

Full data platform using only OSS: Kubernetes, S3, Apache Hudi, Spark, Dagster, Trino, ClickHouse, Kafka. dlt for API ingestion (the `api` source type).

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
      transform.py                      # dbt integration: dagster-dbt assets with custom translator
    resources/
      lakehouse.py                      # LakehouseResource (extends S3Resource): boto3 client to SeaweedFS
      warehouse.py                      # WarehouseResource: ClickHouse connection
  docker-compose.yml                    # Local dev: postgres, user_code, webserver, daemon
  dagster.yaml                          # Dagster instance config (postgres storage)
  workspace.yaml                        # gRPC server: host=user_code, port=3030
  pyproject.toml                        # Deps: dagster, dagster-dbt, dbt-clickhouse, common (path=../libs)
  Dockerfile                            # Builds dbt manifest via `dbt parse` at image build
  .env                                  # Local env vars (not committed secrets)
  .python-version                       # Python >= 3.12

transform/                              # dbt project (transformation layer)
  dbt_project.yml                       # dbt project config: cleansed models -> table, seeds -> raw schema
  profiles.yml                          # ClickHouse connection (env-var driven), no state backend
  macros/
    generate_schema_name.sql            # Use schema (raw/cleansed) verbatim, no target prefix
  models/
    sources.yml                         # raw.* external tables produced by ingestion
    cleansed/noaa_ghcn/                 # Cleansed models (table / view / incremental)
      noaa_ghcn_countries.sql           #   table (FULL)
      noaa_ghcn_observations.sql        #   incremental, insert_overwrite by observation_year
      ...
  seeds/noaa_ghcn/                      # Flag lookup CSVs -> raw schema
  pyproject.toml                        # Deps: dbt-core, dbt-clickhouse
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
3. **Cleansed** (`cleansed_*` assets) — dbt models that transform raw tables into cleansed tables

## Orchestrator (Dagster)

- Python package in `orchestrator/`, requires Python >= 3.12
- Deps on `common` library via `libs/` (path dependency)
- Entry point: `src/definitions.py` — loads `UserConfig` from `./configuration`, builds ingestion + transform assets
- Ingestion: `IngestionAssetBuilder.get_builder(config)` dispatches by `source_type` (S3, API)
- S3 ingestion: reads from source S3 bucket, copies files to SeaweedFS lakehouse (`lakehouse-raw` bucket)
- Transform: `dagster-dbt` integration via `build_transform_assets()` in `assets/transform.py`
  - Custom `CustomDagsterDbtTranslator` maps dbt nodes to `{schema}_{alias}` asset keys (e.g. `raw.table` source -> `raw_table`) to link dbt deps to ingestion assets
  - Attaches `AutomationCondition.eager()` per model so cleansed runs only when an upstream materializes
  - Two `@dbt_assets`: unpartitioned (everything) + yearly-partitioned (`noaa_ghcn_observations`), the latter passing `start_ds`/`end_ds` dbt vars from the partition key
- Credentials: fetched from K8s secrets at runtime (configured per source in YAML)
- Dagster served via gRPC on port 3030
- Docker image: `dadutra2/os-data-platform-orchestrator:latest`
- Local dev: `docker-compose.yml` (postgres + user_code + webserver + daemon), mounts `../configuration` and `../transform`

## Transform (dbt)

- dbt project in `transform/`, requires Python >= 3.12
- Adapter: `dbt-clickhouse` (ClickHouse for execution + storage); dbt is stateless — partition/backfill tracking is owned by Dagster
- Connection via `profiles.yml`, env-var driven: `CLICKHOUSE_ENDPOINT_URL`, `CLICKHOUSE_HTTP_PORT`, `CLICKHOUSE_PASSWORD`
- `macros/generate_schema_name.sql` uses the schema (`raw`/`cleansed`) verbatim so keys line up with ingestion
- Models in `models/cleansed/` read from `raw.*` sources (and seeds) and write to `cleansed.*`:
  - table (countries/states/stations/inventory), view (flag lookups over seeds), incremental `insert_overwrite` partitioned by `observation_year` (observations)
- Seeds (`seeds/noaa_ghcn/*.csv`) load flag lookups into the `raw` schema
- Integrated into Dagster via `dagster-dbt` — cleansed assets depend on raw ingestion assets
- Can run standalone from `transform/`: `dbt seed`, `dbt run`, `dbt build` (observations needs `--vars '{start_ds, end_ds}'`)

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
