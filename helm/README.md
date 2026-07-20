# Helm Deployment

Full Kubernetes deployment runbook for the data platform. All services deploy into the `os-data-platform` namespace.

## Services Overview

| Release | Chart | Purpose | Values |
|---------|-------|---------|--------|
| `metadata` | `bitnami/postgresql` | Shared PostgreSQL metadata store (Dagster + Superset) | `metadata/values.yaml` |
| `storage` | Custom (wraps `seaweedfs`) | S3-compatible object storage (lakehouse) | `storage/values.yaml` |
| `orchestrator` | `dagster/dagster` v1.13.5 | Pipeline orchestration (webserver + daemon + user code) | `orchestrator/values.yaml` |
| `operators` | Custom (wraps `clickhouse-operator-helm`) | ClickHouse Kubernetes operator CRDs | `operators/values.yaml` |
| `warehouse` | Custom | ClickHouse cluster + Keeper + init jobs | `warehouse/values.yaml` |
| `reporting` | `superset/superset` | BI dashboards (Apache Superset) | `reporting/values.yaml` |

## Architecture on K8s

```mermaid
graph LR
    subgraph ns["os-data-platform namespace"]
        direction TB
        subgraph meta["metadata"]
            PG["metadata-postgresql<br/><i>dagster DB + superset DB</i>"]
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
    D_web --> D_code
    D_daemon --> D_code
    D_code -.-> PG
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

```shell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add dagster https://dagster-io.github.io/helm
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

# 4. Orchestrator (optional)
helm install orchestrator dagster/dagster --version 1.13.5 -f helm/orchestrator/values.yaml -n os-data-platform

# 5. Reporting (optional)
helm install reporting superset/superset -f helm/reporting/values.yaml -n os-data-platform
```

## 5. Access UIs

Forward all services to localhost (also accessible from docker-compose containers via `extra_hosts`):

```shell
make forward
```

| Service | URL |
|---------|-----|
| Superset | http://localhost:8088 |
| SeaweedFS S3 | http://localhost:8333 |
| ClickHouse HTTP | http://localhost:8123 |
| ClickHouse native | localhost:9000 |

Stop all forwards:

```shell
make forward-stop
```

## Chart Details

### metadata (PostgreSQL)

Uses `bitnami/postgresql`. Creates databases via init SQL: `dagster` and `superset`. Shared `platform` user. 8Gi persistent volume.

### storage (SeaweedFS)

Wrapper chart around `seaweedfs` v4.35.0. Runs master, volume, filer, and S3 gateway (port 8333). S3 auth enabled via secret. Auto-creates the `lakehouse-raw` bucket.

### orchestrator (Dagster)

Uses official `dagster/dagster` v1.13.5 chart. Disables bundled PostgreSQL (uses shared metadata DB). User deployment pulls `dadutra2/os-data-platform-orchestrator:latest`, runs gRPC code server on port 3030. Gets SeaweedFS and DB credentials via K8s secrets.

### operators (ClickHouse Operator)

Wrapper chart installing `clickhouse-operator-helm` v0.0.6. Disables cert-manager, webhook, and metrics for simplicity.

### warehouse (ClickHouse)

Custom chart deploying:
- **ClickHouseCluster** CR - 1 shard, 1 replica, 10Gi storage, S3 named collection (`seaweedfs`) mounted via ConfigMap
- **KeeperCluster** CR - 1 replica for coordination
- **Init Job** - Helm post-install hook that runs `CREATE DATABASE IF NOT EXISTS raw/cleansed/curated/reporting`
- **ConfigMap** - S3 named collection XML pointing ClickHouse at SeaweedFS endpoint

### reporting (Superset)

Uses official `superset/superset` chart. Disables bundled PostgreSQL (uses shared metadata DB). Bundles Redis for Celery broker/caching. Installs `clickhouse-connect` and `psycopg2-binary` via bootstrap script into `/tmp/extra-packages`. DB URI and secret key injected from `reporting-superset-secret`. Default admin: `admin` / `admin`.

## Downloading Charts Locally (Optional)

```shell
helm pull {repo} --version {version} --untar --untardir ./helm/charts
```
