# Helm

## Add repos

> **Important!**
> In Jun.2026 Airbyte v2 helm chart was not yet released, for this reason the github repo was referenced directly
> V2 chart was necessary to disable the bundled MinIO given that we're using SeaweedFS

```shell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add dagster https://dagster-io.github.io/helm
helm repo add airbyte-v2 "git+https://github.com/airbytehq/airbyte-platform@charts/v2?ref=v2.0.0"
helm repo add seaweedfs https://seaweedfs.github.io/seaweedfs/helm 
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

kubectl label secret metadata-db-postgresql-secret app.kubernetes.io/managed-by-

# Storage (SeaweedFS S3)
kubectl create secret generic storage-seaweedfs-secret \
    --from-literal=SEAWEEDFS_S3_ACCESS_KEY_ID=admin \
    --from-literal=SEAWEEDFS_S3_SECRET_ACCESS_KEY=$OS_DATA_PLATFORM_STORAGE_ROOT_PASSWORD \
    --from-literal=seaweedfs_s3_config='{"identities":[{"name":"admin","credentials":[{"accessKey":"admin","secretKey":"'$OS_DATA_PLATFORM_STORAGE_ROOT_PASSWORD'"}],"actions":["Admin","Read","Write"]}]}'

# Orchestrator (Dagster)
kubectl create secret generic orchestrator-postgresql-secret --from-literal=postgresql-password=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD

# Ingestor (Airbyte)
kubectl create secret generic ingestor-postgresql-secret \
    --from-literal=DATABASE_USER=platform \
    --from-literal=DATABASE_PASSWORD=$OS_DATA_PLATFORM_METADATA_DB_PLATFORM_PASSWORD

```

## Deploy services

Order matters
```shell
helm install metadata bitnami/postgresql -f helm/metadata/values.yaml -n os-data-platform
helm dependency update helm/storage
helm install storage ./helm/storage -n os-data-platform
helm install orchestrator dagster/dagster --version 1.13.5 -f helm/orchestrator/values.yaml -n os-data-platform
helm install ingestor airbyte-v2/airbyte -f helm/ingestor/values.yaml -n os-data-platform 

```

## Accessing UI

```shell
# Dagster (http://localhost:3000)
kubectl port-forward svc/orchestrator-dagster-webserver 3000:80 -n os-data-platform

# Airbyte (http://localhost:3001)
kubectl port-forward svc/ingestor-airbyte-webapp-svc 3001:80 -n os-data-platform

# SeaweedFS master UI (http://localhost:9333)
kubectl port-forward svc/storage-seaweedfs-master 9333:9333 -n os-data-platform
```


## Downloading charts locally (Optional)

```shell
helm pull dagster/dagster --version 1.13.5 --untar --untardir ./helm/charts
helm pull airbyte/airbyte --version 1.7.8 --untar --untardir ./helm/charts
```
