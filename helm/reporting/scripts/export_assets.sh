#!/usr/bin/env bash
# Export all Superset assets (databases, datasets, charts, dashboards) from a
# running instance into this chart's assets/ dir as a reviewable YAML tree.
#
# This refreshes the git source of truth. The assets ConfigMap is rendered from
# assets/ on the next `helm upgrade`, so redeploy to apply changes.
#
# Usage:
#   helm/reporting/scripts/export_assets.sh
#
# Env overrides:
#   NAMESPACE   k8s namespace           (default: os-data-platform)
#   SERVICE     superset service name   (default: reporting-superset)
#   PORT        local port-forward port (default: 8088)
#   USERNAME    admin user              (default: admin)
#   PASSWORD    admin password          (default: admin)
set -euo pipefail

NAMESPACE="${NAMESPACE:-os-data-platform}"
SERVICE="${SERVICE:-reporting-superset}"
PORT="${PORT:-8088}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/assets"
BASE="http://localhost:${PORT}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"; [ -n "${PF_PID:-}" ] && kill "$PF_PID" 2>/dev/null || true' EXIT

echo "==> port-forward svc/${SERVICE} ${PORT}:8088 (ns ${NAMESPACE})"
kubectl port-forward "svc/${SERVICE}" "${PORT}:8088" -n "${NAMESPACE}" >/dev/null 2>&1 &
PF_PID=$!
# wait for the port-forward to accept connections
for _ in $(seq 1 20); do
  curl -sf "${BASE}/health" >/dev/null 2>&1 && break
  sleep 1
done

echo "==> login as ${USERNAME}"
TOKEN="$(curl -s -X POST "${BASE}/api/v1/security/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\",\"provider\":\"db\",\"refresh\":true}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
[ -n "$TOKEN" ] || { echo "ERROR: login failed" >&2; exit 1; }

echo "==> export assets bundle"
# trailing slash required; endpoint 308-redirects otherwise
curl -sL -X GET "${BASE}/api/v1/assets/export/" \
  -H "Authorization: Bearer ${TOKEN}" \
  -o "${tmp}/assets.zip" -w 'http:%{http_code}\n'

unzip -oq "${tmp}/assets.zip" -d "${tmp}/unzip"
# bundle is nested under a timestamped dir: assets_export_YYYYMMDDThhmmss/
root="$(find "${tmp}/unzip" -maxdepth 1 -type d -name 'assets_export_*' | head -1)"
[ -n "$root" ] || { echo "ERROR: unexpected bundle layout" >&2; exit 1; }

echo "==> refresh ${ASSETS_DIR}"
rm -rf "${ASSETS_DIR}"
mkdir -p "${ASSETS_DIR}"
# lowercase + underscore-only, preserving "/" (dirs) and "." (extension)
norm() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's#[^a-z0-9._/]#_#g'; }
# copy tree, stripping Superset's "_<id>" filename suffix and normalizing names
cp "${root}/metadata.yaml" "${ASSETS_DIR}/metadata.yaml"
while IFS= read -r -d '' f; do
  rel="${f#"${root}/"}"
  dir="$(norm "$(dirname "$rel")")"
  base="$(basename "$rel" .yaml)"
  base="$(norm "${base%_[0-9]*}")"    # drop trailing _<id>, then normalize
  mkdir -p "${ASSETS_DIR}/${dir}"
  cp "$f" "${ASSETS_DIR}/${dir}/${base}.yaml"
done < <(find "${root}" -mindepth 2 -type f -name '*.yaml' -print0)

echo "==> done. tree:"
( cd "${ASSETS_DIR}/.." && find assets -type f | sort )
echo
echo "Next: helm upgrade --install reporting helm/reporting -n os-data-platform"