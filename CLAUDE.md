# os-data-platform

Open source data platform built on Kubernetes. Currently only orchestration layer exists.

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
    definitions.py                      # Entry point: loads UserConfig, builds assets from config, registers Definitions
    assets/
      ingestion.py                      # IngestionAssetBuilder (ABC) + factory get_builder()
      ingestion_s3.py                   # S3IngestionAssetBuilder: copies S3 files to SeaweedFS lakehouse
    resources/
      lakehouse.py                      # LakehouseResource (extends S3Resource): boto3 client to SeaweedFS
  docker-compose.yml                    # Local dev: postgres, user_code, webserver, daemon
  dagster.yaml                          # Dagster instance config (postgres storage)
  workspace.yaml                        # gRPC server: host=user_code, port=3030
  pyproject.toml                        # Deps: dagster, dagster-postgres, dagster-k8s, dagster-aws, common (path=../libs)
  Dockerfile
  .env                                  # Local env vars (not committed secrets)
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

## Orchestrator (Dagster)

- Python package in `orchestrator/`, requires Python >= 3.12
- Deps on `common` library via `libs/` (path dependency)
- Entry point: `src/definitions.py` — loads `UserConfig` from `./configuration`, builds assets via builder pattern
- Builder pattern: `IngestionAssetBuilder.get_builder(config)` dispatches by `source_type` (S3, Airbyte)
- S3 ingestion: reads from source S3 bucket, copies files to SeaweedFS lakehouse (`lakehouse-raw` bucket)
- Credentials: fetched from K8s secrets at runtime (configured per source in YAML)
- Dagster served via gRPC on port 3030
- Docker image: `dadutra2/os-data-platform-orchestrator:latest`
- Local dev: `docker-compose.yml` (postgres + user_code + webserver + daemon), mounts `../configuration`

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
