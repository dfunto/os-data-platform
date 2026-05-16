# Helm

## Add repos

```shell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add dagster https://dagster-io.github.io/helm
helm repo add airbyte https://airbytehq.github.io/helm-charts
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
export OS_DATA_PLATFORM_METADATA_DB_ADMIN_PASSWORD=admin
export OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD=platform
```

Create Kubernetes secret with them
```shell
kubectl create secret generic metadata-db-postgresql-secret \
    --from-literal=admin-password=$OS_DATA_PLATFORM_METADATA_DB_ADMIN_PASSWORD \
    --from-literal=platform-password=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD \
    -n os-data-platform
```

## Deploy services

Order matters
```shell
helm install metadata bitnami/postgresql -f helm/metadata/values.yaml -n os-data-platform
helm install orchestrator dagster/dagster -f helm/orchestrator/values.yaml -n os-data-platform
helm install ingestor airbyte/airbyte --version 1.7.8 -f helm/ingestor/values.yaml -n os-data-platform
```

## Accessing UI

```shell
# Dagster (http://localhost:3000)
kubectl port-forward svc/orchestrator-dagster-webserver 3000:80 -n os-data-platform

# Airbyte (http://localhost:3001)
kubectl port-forward svc/ingestor-airbyte-webapp-svc 3001:80 -n os-data-platform
```
