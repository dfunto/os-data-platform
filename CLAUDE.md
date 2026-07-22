# os-data-platform

Open source data platform built on Kubernetes with ingestion, transformation, and warehouse layers.

## Goal

Full data platform using only OSS: Kubernetes, S3, Apache Hudi, Spark, Dagster, Trino, ClickHouse, Kafka. dlt for API ingestion (the `api` source type). Cube Core as the governed semantic layer over `curated` for an English-to-SQL agent.

## Repo Structure

```
configuration/                          # User-defined YAML configs (mounted into orchestrator container)
  ingestion/
    source1.yml                         # Per-source ingestion config (name, source_type, s3_config, tables)

orchestrator/                           # Dagster user code
  src/
    definitions.py                      # Entry point: loads UserConfig, builds ingestion + transform assets, registers Definitions
    common/                             # In-tree "common" package (config models + loader)
      models/                           # Pydantic models: IngestionConfig, IngestionS3Config, IngestionApiConfig, LakehouseLayer, etc.
      user_config.py                    # UserConfig class: loads YAML configs from configuration/ dir by capability
    assets/
      ingestion.py                      # IngestionAssetBuilder (ABC) + factory get_builder()
      ingestion_s3.py                   # S3IngestionAssetBuilder: copies S3 files to SeaweedFS lakehouse
      ingestion_api.py                  # ApiIngestionAssetBuilder: dlt REST pipelines -> ClickHouse raw
      transform.py                      # dbt integration: dagster-dbt assets with custom translator
    resources/
      lakehouse.py                      # LakehouseResource (extends S3Resource): boto3 client to SeaweedFS
      warehouse.py                      # WarehouseResource: ClickHouse connection
  tests/                                # Unit tests (models, config loader, asset builders)
  docker-compose.yml                    # Local dev: postgres, user_code, webserver, daemon
  dagster.yaml                          # Dagster instance config (postgres storage)
  workspace.yaml                        # gRPC server: host=user_code, port=3030
  pyproject.toml                        # Deps: dagster, dagster-dbt, dbt-clickhouse, dlt, pydantic
  Dockerfile                            # Builds dbt manifest via `dbt parse` at image build
  .env                                  # Local env vars (not committed secrets)
  .python-version                       # Python >= 3.12

transform/                              # dbt project (transformation layer)
  dbt_project.yml                       # dbt project config: cleansed/curated/reporting -> table, seeds -> raw schema
  profiles.yml                          # ClickHouse connection (env-var driven), no state backend
  macros/
    generate_schema_name.sql            # Use schema (raw/cleansed/curated/reporting) verbatim, no target prefix
  models/
    sources.yml                         # raw.* external tables produced by ingestion
    cleansed/noaa_ghcn/                 # Cleansed models (table / view / incremental)
      noaa_ghcn_countries.sql           #   table (FULL)
      noaa_ghcn_observations.sql        #   incremental, insert_overwrite by observation_year
      ...
    curated/noaa_ghcn/                  # Denormalized facts (curated_*.sql, aliased noaa_ghcn_*)
      curated_noaa_ghcn_stations.sql    #   station dim + country/state names
      curated_noaa_ghcn_observations.sql#   obs-grain OBT, normalized value, all rows + quality_flag
      curated_noaa_ghcn_station_year.sql#   per-station-year rollup (two-stage first stage)
    reporting/noaa_ghcn/                # Aggregated marts over curated (Superset reads these)
  seeds/noaa_ghcn/                      # Flag lookup CSVs -> raw schema
  pyproject.toml                        # Deps: dbt-core, dbt-clickhouse
  .python-version                       # Python >= 3.12

semantic/                               # Cube Core semantic layer (governed query layer over curated)
  cube.js                               # Cube config (env-driven)
  model/cubes/                          # Data model: station_year, stations, observations cubes
  Dockerfile                            # FROM cubejs/cube + baked model
  docker-compose.yml                    # Local dev (needs `make forward`)
  .env.example                          # CLICKHOUSE_* + CUBEJS_* env

helm/                                   # Helm charts and values for K8s
  orchestrator/values.yaml              # Dagster Helm values
  warehouse/                            # ClickHouse warehouse chart
    Chart.yaml
    values.yaml                         # ClickHouse config: shards, replicas, initSQL (raw/cleansed/curated/reporting DBs)
    templates/
      clickhouse-cluster.yaml           # ClickHouseCluster CR with S3 named collection mount
      keeper-cluster.yaml               # ClickHouse Keeper cluster
      lakehouse-config.yaml             # ConfigMap: S3 named collection XML (seaweedfs -> SeaweedFS endpoint)
      warehouse-init-job.yaml           # Helm hook Job: runs initSQL via clickhouse-client
      _helpers.tpl
  semantic/                             # Cube Core chart (Deployment + Service, api-only)
  README.md
```

## Asset Pipeline

The platform defines asset groups forming a lineage:

1. **Ingestion** (`ingest_*` assets) — copies files from source S3 buckets into SeaweedFS lakehouse
2. **Raw** (`raw_*` assets) — creates ClickHouse tables from ingested files
3. **Cleansed** (`cleansed_*` assets) — dbt models that clean/type raw tables (staging, per-source)
4. **Curated** (`curated_*` assets) — dbt models: denormalized, non-aggregated facts; units normalized once (÷10 tenths, SNOW-exception). Source for reporting and the semantic layer
5. **Reporting** (`reporting_*` assets) — dbt models: aggregated business marts read directly by Superset

## Orchestrator (Dagster)

- Python package in `orchestrator/`, requires Python >= 3.12
- `common` package (config models + loader) lives in-tree at `src/common`
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
- `macros/generate_schema_name.sql` uses the schema (`raw`/`cleansed`/`curated`/`reporting`) verbatim so keys line up with ingestion
- Layers: `cleansed` (staging) → `curated` (denormalized facts) → `reporting` (aggregated marts)
- Models in `models/cleansed/` read from `raw.*` sources (and seeds) and write to `cleansed.*`:
  - table (countries/states/stations/inventory), view (flag lookups over seeds), incremental `insert_overwrite` partitioned by `observation_year` (observations)
- Models in `models/curated/noaa_ghcn/` are denormalized facts (`curated_*.sql` files, aliased to `noaa_ghcn_*` since names collide with cleansed):
  - `noaa_ghcn_stations` (station dim + country/state names), `noaa_ghcn_observations` (obs-grain OBT, `observation_value_normalized` bakes ÷10 / SNOW-exception, all rows kept with `quality_flag`), `noaa_ghcn_station_year` (per-station-year rollup = first stage of the two-stage averages)
- Models in `models/reporting/noaa_ghcn/` are trivial aggregations over curated facts (the 4 marts Superset reads); no unit or multi-stage logic lives here
- Seeds (`seeds/noaa_ghcn/*.csv`) load flag lookups into the `raw` schema
- Integrated into Dagster via `dagster-dbt` — cleansed assets depend on raw ingestion assets; curated → reporting chain via dbt refs
- Can run standalone from `transform/`: `dbt seed`, `dbt run`, `dbt build` (observations needs `--vars '{start_ds, end_ds}'`)

## Semantic Layer (Cube)

- Cube Core in `semantic/`, the governed query layer over the `curated` schema for the English-to-SQL agent (agent selects governed measures/dimensions; Cube compiles to ClickHouse SQL and fails closed on anything unmodelled)
- Data model in `semantic/model/cubes/` (single source of truth): `station_year` (governed climate metrics = cross-station second stage of the two-stage averages), `stations` (coverage/geo), `observations` (obs-grain detail, normalized value)
- Reads `curated.*` read-only; **never writes** to ClickHouse (dbt is the only writer). MVP is api-only (no Cube Store / pre-aggregations)
- Access via the SQL API (Postgres wire, port 15432) and REST (4000); connection/env in `semantic/.env.example`
- Deployed as a custom image (`dadutra2/os-data-platform-semantic:latest`, `FROM cubejs/cube` + baked model) via `helm/semantic`; local dev via `semantic/docker-compose.yml` (needs `make forward`)
- Design: `docs/superpowers/specs/2026-07-20-semantic-layer-cube-design.md`

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
- Init SQL creates databases: `raw`, `cleansed`, `curated`, `reporting`
- Keeper cluster for coordination
