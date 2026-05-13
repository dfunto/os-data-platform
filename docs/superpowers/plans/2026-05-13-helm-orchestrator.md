# Helm Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy Dagster orchestrator to Docker Desktop Kubernetes using the official Dagster Helm chart with a custom `values.yaml`.

**Architecture:** Single `values.yaml` overrides the official `dagster/dagster` Helm chart. PostgreSQL runs as bundled subchart. User code server uses `dadutra2/os-data-platform-orchestrator:latest` from DockerHub. Webserver accessed via `kubectl port-forward`.

**Tech Stack:** Helm 3, dagster/dagster Helm chart, Kubernetes (Docker Desktop), PostgreSQL (bitnami subchart)

---

### Task 1: Create `helm/orchestrator/values.yaml`

**Files:**
- Create: `helm/orchestrator/values.yaml`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p helm/orchestrator
```

- [ ] **Step 2: Write `values.yaml`**

Create `helm/orchestrator/values.yaml` with this exact content:

```yaml
global:
  postgresqlSecretName: dagster-postgresql-secret

postgresql:
  enabled: true
  auth:
    username: dagster
    password: dagster
    database: dagster

dagster-user-deployments:
  enabled: true
  enableSubchart: true
  deployments:
    - name: orchestrator
      image:
        repository: dadutra2/os-data-platform-orchestrator
        tag: latest
        pullPolicy: Always
      dagsterApiGrpcArgs:
        - "--python-file"
        - "src/definitions.py"
      port: 3030
      envSecrets:
        - name: dagster-postgresql-secret

dagsterWebserver:
  replicaCount: 1

dagsterDaemon:
  enabled: true

ingress:
  enabled: false

dagsterHome: |
  telemetry:
    enabled: false
```

- [ ] **Step 3: Commit**

```bash
git add helm/orchestrator/values.yaml
git commit -m "feat: add Helm values for Dagster orchestrator deployment"
```

---

### Task 2: Verify chart renders correctly (dry run)

**Files:**
- Read: `helm/orchestrator/values.yaml`

- [ ] **Step 1: Add Dagster Helm repo**

```bash
helm repo add dagster https://dagster-io.github.io/helm
helm repo update
```

Expected output includes: `Successfully got an update from the "dagster" chart repository`

- [ ] **Step 2: Lint the values**

```bash
helm lint dagster/dagster -f helm/orchestrator/values.yaml
```

Expected: `1 chart(s) linted, 0 chart(s) failed`

- [ ] **Step 3: Template render (dry run)**

```bash
helm template dagster dagster/dagster -f helm/orchestrator/values.yaml -n dagster | grep -E "kind:|name:"
```

Expected output includes:
```
kind: Deployment
...
kind: Service
...
kind: StatefulSet   # PostgreSQL
```

Verify these names appear:
- `dagster-dagster-webserver`
- `dagster-dagster-daemon`
- `orchestrator` (user code deployment)
- `dagster-postgresql`

---

### Task 3: Deploy to Docker Desktop Kubernetes

**Prerequisites:** Docker Desktop running with Kubernetes enabled. Confirm with:
```bash
kubectl config current-context
```
Expected: `docker-desktop`

- [ ] **Step 1: Create namespace and deploy**

```bash
helm install dagster dagster/dagster \
  -f helm/orchestrator/values.yaml \
  -n dagster --create-namespace
```

Expected: `STATUS: deployed`

- [ ] **Step 2: Wait for pods to be ready**

```bash
kubectl get pods -n dagster --watch
```

Wait until all pods show `Running` or `Completed`. Expected pods:
- `dagster-dagster-webserver-*` → Running
- `dagster-dagster-daemon-*` → Running
- `orchestrator-*` → Running
- `dagster-postgresql-0` → Running

Ctrl+C once all Running.

- [ ] **Step 3: Verify user code server loaded**

```bash
kubectl logs -n dagster -l deployment=orchestrator --tail=20
```

Expected output includes:
```
Starting Dagster code proxy server for file src/definitions.py on port 3030
```

- [ ] **Step 4: Port-forward webserver**

```bash
kubectl port-forward svc/dagster-dagster-webserver 3000:80 -n dagster
```

Open `http://localhost:3000` in browser. Confirm:
- UI loads
- Assets tab shows `raw_orders` and `orders` assets
- Schedules tab shows `orders_schedule`

- [ ] **Step 5: Commit docs note**

```bash
git add docs/superpowers/plans/2026-05-13-helm-orchestrator.md
git commit -m "docs: add Helm orchestrator implementation plan"
```

---

### Task 4: Upgrade workflow verification

- [ ] **Step 1: Make a trivial change to definitions.py**

In `orchestrator/src/definitions.py`, add a log line to `raw_orders`:

```python
@asset
def raw_orders(context: AssetExecutionContext):
    """Ingest raw orders data from source."""
    context.log.info("Ingesting raw orders...")
    context.log.info("Version 2")  # add this line
    return {"rows": 0}
```

- [ ] **Step 2: Build and push new image**

```bash
docker build -t dadutra2/os-data-platform-orchestrator:latest orchestrator/
docker push dadutra2/os-data-platform-orchestrator:latest
```

- [ ] **Step 3: Upgrade Helm release**

```bash
helm upgrade dagster dagster/dagster \
  -f helm/orchestrator/values.yaml \
  -n dagster
```

Expected: `Release "dagster" has been upgraded. STATUS: deployed`

- [ ] **Step 4: Rollout restart user code deployment**

Helm upgrade won't re-pull `latest` tag automatically. Force pod restart:

```bash
kubectl rollout restart deployment/orchestrator -n dagster
kubectl rollout status deployment/orchestrator -n dagster
```

Expected: `deployment "orchestrator" successfully rolled out`

- [ ] **Step 5: Verify new code loaded**

```bash
kubectl logs -n dagster -l deployment=orchestrator --tail=20
```

Confirm pod restarted with new image (check timestamp).