# Helm Orchestrator Design

**Date:** 2026-05-13
**Status:** Approved

## Overview

Deploy Dagster orchestrator to Kubernetes using the official `dagster/dagster` Helm chart with a custom `values.yaml`. Targets Docker Desktop local K8s. PostgreSQL runs bundled via chart subchart. Webserver accessed via `kubectl port-forward`.

## Repository Structure

```
os-data-platform/
  helm/
    orchestrator/
      values.yaml          ← Helm overrides (image, postgres, user code)
  orchestrator/
    Dockerfile             ← builds dadutra2/os-data-platform-orchestrator:latest
    src/
      definitions.py
    docker-compose.yml     ← local dev only
```

## Components

### User Code Server
- Image: `dadutra2/os-data-platform-orchestrator:latest` (public DockerHub)
- Command: `dagster code-server start -h 0.0.0.0 -p 3030 -f src/definitions.py`
- Defined under `dagsterUserDeployments` in `values.yaml`

### Webserver
- Provided by Dagster Helm chart
- Exposed via `kubectl port-forward` on port 3000
- No ingress configured

### Daemon
- Provided by Dagster Helm chart
- Handles schedules, sensors, run queuing

### PostgreSQL
- Bundled via chart's PostgreSQL subchart
- Stores Dagster metadata (run history, asset catalog)
- Credentials managed via K8s Secret created by the chart

### Dagster Instance Config
- Telemetry disabled
- Storage backend: PostgreSQL
- Injected via `dagsterHome` in `values.yaml`

## Deploy Workflow

```bash
# Add Helm repo (once)
helm repo add dagster https://dagster-io.github.io/helm

# Install
helm install dagster dagster/dagster \
  -f helm/orchestrator/values.yaml \
  -n dagster --create-namespace

# Access UI
kubectl port-forward svc/dagster-dagster-webserver 3000:80 -n dagster

# Upgrade after image push
helm upgrade dagster dagster/dagster \
  -f helm/orchestrator/values.yaml \
  -n dagster
```

## Out of Scope

- Container registry setup (DockerHub manual push)
- Ingress / TLS
- Resource limits / HPA
- Multi-environment (dev/staging/prod) separation
- Secrets management (Vault, External Secrets)