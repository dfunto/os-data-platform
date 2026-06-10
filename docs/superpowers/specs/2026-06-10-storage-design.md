# Storage Layer Design

**Date:** 2026-06-10
**Status:** Approved

## Summary

Add RustFS as S3-compatible object storage deployed via Helm into the `os-data-platform` namespace. Single-node (standalone) deployment. Primary use: Airbyte ingestor raw data landing zone.

## Solution

**RustFS** — Apache 2.0, S3-compatible, official Helm chart at `charts.rustfs.com`. Chosen over archived MinIO community edition. Chart version 0.7.0, app version 1.0.0-beta.7 (beta software, appropriate for this OSS platform).

## Files

```
helm/
  storage/
    values.yaml     # RustFS standalone Helm values
  README.md         # Updated: repo add, secret creation, deploy command, port-forward
```

## Helm Values (`helm/storage/values.yaml`)

- **Mode:** standalone (single Deployment + single PVC)
- **Auth:** via pre-created K8s secret `storage-rustfs-secret` (keys: `root-user`, `root-password`)
- **Persistence:** 20Gi
- **Buckets:** `os-data-platform-ingestor`
- **Ingress:** disabled (access via port-forward)
- **Resources:** 100m/128Mi requests, 500m/512Mi limits

## Secret

```shell
kubectl create secret generic storage-rustfs-secret \
    --from-literal=root-user=$OS_DATA_PLATFORM_STORAGE_ACCESS_KEY \
    --from-literal=root-password=$OS_DATA_PLATFORM_STORAGE_SECRET_KEY
```

Follows same credential pattern as `metadata-db-postgresql-secret`, `orchestrator-postgresql-secret`, `ingestor-postgresql-secret`.

## Deploy Command

```shell
helm install storage rustfs/rustfs -f helm/storage/values.yaml -n os-data-platform
```

Deploy after `metadata` (no hard dependency, but consistent with platform boot order).

## Access

```shell
# RustFS console (http://localhost:9001)
kubectl port-forward svc/storage-rustfs-console 9001:9001 -n os-data-platform
```

S3 API endpoint for Airbyte: `http://storage-rustfs:9000`

## Integration with Airbyte

Airbyte S3 destination connector points to:
- **Endpoint:** `http://storage-rustfs:9000`
- **Access Key / Secret:** from `storage-rustfs-secret`
- **Bucket:** `os-data-platform-ingestor`

## README Changes

1. Add `helm repo add rustfs https://charts.rustfs.com` to "Add repos" section
2. Add storage secret creation block to "Define Credentials" section
3. Add `helm install storage ...` to "Deploy services" section (after ingestor line)
4. Add port-forward entry to "Accessing UI" section