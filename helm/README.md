# Helm

## Add repos

```shell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add dagster https://dagster-io.github.io/helm
helm repo add airbyte https://airbytehq.github.io/helm-charts
helm repo add rustfs https://charts.rustfs.com
helm repo update
```

## Config Kubernetes Context

```shell
kubectl create namespace os-data-platform
kubectl config set-context --current --namespace=os-data-platform
```

## Define Metadata DB Credentials

Define credentials
```shell
export OS_DATA_PLATFORM_METADATA_DB_ADMIN_PASSWORD=<add_admin_password_here>
export OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD=<add_platform_user_password_here>
```

Create Kubernetes secret with them
```shell
# Metadata Postgres Database
kubectl create secret generic metadata-db-postgresql-secret \
    --from-literal=admin-password=$OS_DATA_PLATFORM_METADATA_DB_ADMIN_PASSWORD \
    --from-literal=platform-password=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD

kubectl annotate secret metadata-db-postgresql-secret \
  meta.helm.sh/release-name=metadata \
  meta.helm.sh/release-namespace=os-data-platform \
  --overwrite

kubectl label secret metadata-db-postgresql-secret \
    app.kubernetes.io/managed-by-

# Orchestrator (Dagster)
kubectl create secret generic orchestrator-postgresql-secret \
    --from-literal=postgresql-password=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD
    
# Ingestor (Airbyte)
kubectl create secret generic ingestor-postgresql-secret \
    --from-literal=platform-password=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD

# Storage (RustFS)
export OS_DATA_PLATFORM_STORAGE_ACCESS_KEY=<access_key>
export OS_DATA_PLATFORM_STORAGE_SECRET_KEY=<secret_key>

kubectl create secret generic storage-rustfs-secret \
    --from-literal=root-user=$OS_DATA_PLATFORM_STORAGE_ACCESS_KEY \
    --from-literal=root-password=$OS_DATA_PLATFORM_STORAGE_SECRET_KEY
```

## Deploy services

Order matters
```shell
helm install metadata bitnami/postgresql -f helm/metadata/values.yaml -n os-data-platform
helm install orchestrator dagster/dagster --version 1.13.5 -f helm/orchestrator/values.yaml -n os-data-platform
helm install ingestor airbyte/airbyte --version 1.7.8 -f helm/ingestor/values.yaml -n os-data-platform
helm install storage rustfs/rustfs -f helm/storage/values.yaml -n os-data-platform
```

## Accessing UI

```shell
# Dagster (http://localhost:3000)
kubectl port-forward svc/orchestrator-dagster-webserver 3000:80 -n os-data-platform

# Airbyte (http://localhost:3001)
kubectl port-forward svc/ingestor-airbyte-webapp-svc 3001:80 -n os-data-platform

# RustFS console (http://localhost:9001)
kubectl port-forward svc/storage-rustfs-console 9001:9001 -n os-data-platform
```


## Downloading charts locally (Optional)

```shell
helm pull dagster/dagster --version 1.13.5 --untar --untardir ./helm/charts
helm pull airbyte/airbyte --version 1.7.8 --untar --untardir ./helm/charts
```
