# os-data-platform

Open source data platform built on Kubernetes. Currently only orchestration layer exists.

## Goal

Full data platform using only OSS: Kubernetes, S3, Apache Hudi, Spark, Dagster, Trino, ClickHouse, Kafka. Airbyte for ingestion (TBD).

## Repo Structure

```
helm/                        # Helm values for K8s deployments
  orchestrator/values.yaml   # Dagster deployment values
  README.md                  # Helm deploy commands

orchestrator/                # Dagster user code
  src/definitions.py         # Dagster assets, jobs, schedules
  workspace.yaml             # Points dagster to gRPC server (host: user_code, port: 3030)
  pyproject.toml             # Python deps: dagster, dagster-postgres, dagster-k8s, dagster-webserver
  .python-version            # Python >= 3.12
```

## Orchestrator (Dagster)

- Python package in `orchestrator/`, requires Python >= 3.12
- Assets defined in `src/definitions.py`: `raw_orders` -> `orders` pipeline, daily at 6am
- Dagster served via gRPC on port 3030
- Docker image: `dadutra2/os-data-platform-orchestrator:latest`

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

## Roadmap

- [x] Dagster setup
- [ ] CDC Ingestion