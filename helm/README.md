# Helm Deployment

Full Kubernetes deployment runbook for the data platform. All services deploy into the `os-data-platform` namespace.

## Services Overview

| Release | Chart | Purpose | Values |
|---------|-------|---------|--------|
| `metadata` | `bitnami/postgresql` | Shared PostgreSQL for Dagster + Airbyte metadata | `metadata/values.yaml` |
| `storage` | Custom (wraps `seaweedfs`) | S3-compatible object storage (lakehouse) | `storage/values.yaml` |
| `orchestrator` | `dagster/dagster` v1.13.5 | Pipeline orchestration (webserver + daemon + user code) | `orchestrator/values.yaml` |
| `ingestor` | `airbyte-v2/airbyte` | Connector-based ingestion (API/SaaS/CDC) | `ingestor/values.yaml` |
| `operators` | Custom (wraps `clickhouse-operator-helm`) | ClickHouse Kubernetes operator CRDs | `operators/values.yaml` |
| `warehouse` | Custom | ClickHouse cluster + Keeper + init jobs | `warehouse/values.yaml` |
| `reporting` | `superset/superset` | BI dashboards (Apache Superset) | `reporting/values.yaml` |

## Architecture on K8s

```mermaid
graph LR
    subgraph ns["os-data-platform namespace"]
        direction TB
        subgraph meta["metadata"]
            PG["metadata-postgresql<br/><i>dagster DB + airbyte DB</i>"]
        end

        subgraph stor["storage"]
            SW_master["seaweedfs-master"]
            SW_vol["seaweedfs-volume"]
            SW_filer["seaweedfs-filer"]
            SW_s3["seaweedfs-s3<br/><i>:8333</i>"]
        end

        subgraph orch["orchestrator"]
            D_web["dagster-webserver"]
            D_daemon["dagster-daemon"]
            D_code["dagster-user-code<br/><i>gRPC :3030</i>"]
        end

        subgraph ing["ingestor"]
            A_srv["airbyte-server"]
            A_wrk["airbyte-worker"]
            A_web["airbyte-webapp"]
        end

        subgraph wh["warehouse"]
            CH_op["clickhouse-operator"]
            CH["clickhouse-cluster<br/><i>S3 engine → SeaweedFS</i>"]
            CH_keep["clickhouse-keeper"]
        end

        subgraph rpt["reporting"]
            SS["superset<br/><i>:8088</i>"]
            SS_redis["superset-redis"]
            SS_worker["superset-worker"]
        end
    end

    D_code --> SW_s3
    D_code --> CH
    A_wrk --> SW_s3
    D_web --> D_code
    D_daemon --> D_code
    D_code -.-> PG
    A_srv -.-> PG
    CH_op --> CH
    CH --> SW_s3
    SS --> CH
    SS -.-> PG
    SS_worker --> SS_redis
```

## Prerequisites

- Kubernetes cluster
- `helm` CLI
- `kubectl` configured for target cluster

## 1. Add Helm Repos

> **Note:** Airbyte v2 chart was referenced from GitHub directly because the published v2 chart was not yet released as of Jun 2026. V2 was necessary to disable the bundled MinIO (we use SeaweedFS instead).

```shell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add dagster https://dagster-io.github.io/helm
helm repo add airbyte-v2 "git+https://github.com/airbytehq/airbyte-platform@charts/v2?ref=v2.0.0"
helm repo add seaweedfs https://seaweedfs.github.io/seaweedfs/helm
helm repo add superset https://apache.github.io/superset
helm repo update
```

## 2. Create Namespace

```shell
kubectl create namespace os-data-platform
kubectl config set-context --current --namespace=os-data-platform
```

## 3. Create Secrets

Set credentials and environment variables (direnv recommended):

```shell
export OS_DATA_PLATFORM_METADATA_DB_ADMIN_PASSWORD=<admin_password>
export OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD=<platform_password>
export OS_DATA_PLATFORM_STORAGE_ROOT_PASSWORD=<seaweedfs_password>
export OS_DATA_PLATFORM_ENVIRONMENT=dev
export PULUMI_DISABLE_TELEMETRY=1
export PULUMI_CONFIG_PASSPHRASE=""
```

Then create all required K8s secrets:

```shell
# Metadata Postgres Database
kubectl create secret generic metadata-db-postgresql-secret \
    --from-literal=admin-password=$OS_DATA_PLATFORM_METADATA_DB_ADMIN_PASSWORD \
    --from-literal=platform-password=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD

kubectl annotate secret metadata-db-postgresql-secret \
    meta.helm.sh/release-name=metadata \
    meta.helm.sh/release-namespace=os-data-platform \
    --overwrite

kubectl label secret metadata-db-postgresql-secret app.kubernetes.io/managed-by-

# Storage (SeaweedFS S3)
kubectl create secret generic storage-seaweedfs-secret \
    --from-literal=SEAWEEDFS_S3_ACCESS_KEY_ID=admin \
    --from-literal=SEAWEEDFS_S3_SECRET_ACCESS_KEY=$OS_DATA_PLATFORM_STORAGE_ROOT_PASSWORD \
    --from-literal=seaweedfs_s3_config='{"identities":[{"name":"admin","credentials":[{"accessKey":"admin","secretKey":"'$OS_DATA_PLATFORM_STORAGE_ROOT_PASSWORD'"}],"actions":["Admin","Read","Write"]}]}'

# Orchestrator (Dagster)
kubectl create secret generic orchestrator-postgresql-secret \
    --from-literal=postgresql-password=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD

kubectl annotate secret orchestrator-postgresql-secret \
    meta.helm.sh/release-name=orchestrator \
    meta.helm.sh/release-namespace=os-data-platform

kubectl label secret orchestrator-postgresql-secret \
    app.kubernetes.io/managed-by=Helm

# Ingestor (Airbyte)
kubectl create secret generic ingestor-postgresql-secret \
    --from-literal=DATABASE_USER=platform \
    --from-literal=DATABASE_PASSWORD=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD

# Reporting (Superset)
kubectl create secret generic reporting-superset-secret \
    --from-literal=SUPERSET_SECRET_KEY=$(openssl rand -base64 42) \
    --from-literal=SUPERSET_DATABASE_URI=postgresql+psycopg2://platform:$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD@metadata-postgresql:5432/superset
```

## 4. Deploy Services

Order matters -- each service depends on the ones above it.

```shell
# 1. Metadata database
helm install metadata bitnami/postgresql -f helm/metadata/values.yaml -n os-data-platform

# 2. Object storage
helm dependency update helm/storage
helm install storage ./helm/storage -n os-data-platform

# 3. Warehouse
helm install operators ./helm/operators -n os-data-platform
helm dependency update helm/warehouse
helm install warehouse ./helm/warehouse -f helm/warehouse/values.yaml -n os-data-platform

# 5. Orchestrator (optional)
helm install orchestrator dagster/dagster --version 1.13.5 -f helm/orchestrator/values.yaml -n os-data-platform

# 6. Ingestor (optional)
helm install ingestor airbyte-v2/airbyte -f helm/ingestor/values.yaml -n os-data-platform

# 5. Reporting (optional)
helm install reporting superset/superset -f helm/reporting/values.yaml -n os-data-platform
```

## 5. Access UIs

```shell
# Dagster (http://localhost:3000)
kubectl port-forward svc/orchestrator-dagster-webserver 3000:80 -n os-data-platform

# Airbyte (http://localhost:3001)
kubectl port-forward svc/ingestor-airbyte-webapp-svc 3001:80 -n os-data-platform

# SeaweedFS master (http://localhost:9333)
kubectl port-forward svc/storage-seaweedfs-master 9333:9333 -n os-data-platform

# Superset (http://localhost:8088)
kubectl port-forward svc/reporting-superset 8088:8088 -n os-data-platform
```

## Chart Details

### metadata (PostgreSQL)

Uses `bitnami/postgresql`. Creates two databases via init SQL: `dagster` and `airbyte`. Shared `platform` user for both. 8Gi persistent volume.

### storage (SeaweedFS)

Wrapper chart around `seaweedfs` v4.35.0. Runs master, volume, filer, and S3 gateway (port 8333). S3 auth enabled via secret. Auto-creates buckets: `lakehouse-raw` and `os-data-platform-ingestor`.

### orchestrator (Dagster)

Uses official `dagster/dagster` v1.13.5 chart. Disables bundled PostgreSQL (uses shared metadata DB). User deployment pulls `dadutra2/os-data-platform-orchestrator:latest`, runs gRPC code server on port 3030. Gets SeaweedFS and DB credentials via K8s secrets.

### ingestor (Airbyte)

Uses Airbyte v2 community chart. Disables bundled PostgreSQL and MinIO. Points at shared metadata DB and SeaweedFS for state/log storage. Default admin: `admin@airbyte.io` / `admin`.

### operators (ClickHouse Operator)

Wrapper chart installing `clickhouse-operator-helm` v0.0.6. Disables cert-manager, webhook, and metrics for simplicity.

### warehouse (ClickHouse)

Custom chart deploying:
- **ClickHouseCluster** CR - 1 shard, 1 replica, 10Gi storage, S3 named collection (`seaweedfs`) mounted via ConfigMap
- **KeeperCluster** CR - 1 replica for coordination
- **Init Job** - Helm post-install hook that runs `CREATE DATABASE IF NOT EXISTS raw/cleansed/curated`
- **ConfigMap** - S3 named collection XML pointing ClickHouse at SeaweedFS endpoint

### reporting (Superset)

Uses official `superset/superset` chart. Disables bundled PostgreSQL (uses shared metadata DB). Bundles Redis for Celery broker/caching. Installs `clickhouse-connect` and `psycopg2-binary` via bootstrap script into `/tmp/extra-packages`. DB URI and secret key injected from `reporting-superset-secret`. Default admin: `admin` / `admin`.

## Downloading Charts Locally (Optional)

```shell
helm pull dagster/dagster --version 1.13.5 --untar --untardir ./helm/charts
helm pull airbyte/airbyte --version 1.7.8 --untar --untardir ./helm/charts
```
