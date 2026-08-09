#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE_NAME="devops-assignment"

# Reuse the local .env secret if present, otherwise generate one on the fly.
if [[ -f "$ROOT_DIR/.env" ]]; then
  # shellcheck disable=SC1090
  source "$ROOT_DIR/.env"
fi
SHARED_SECRET="${SHARED_SECRET:-$(openssl rand -hex 32)}"

helm upgrade --install "$RELEASE_NAME" "$ROOT_DIR/helm/devops-assignment" \
  --namespace default \
  --create-namespace \
  --set global.sharedSecret="$SHARED_SECRET" \
  --set server.image.repository=app2-server \
  --set server.image.tag=local \
  --set server.image.pullPolicy=IfNotPresent \
  --set client.image.repository=app1-client \
  --set client.image.tag=local \
  --set client.image.pullPolicy=IfNotPresent \
  --wait --timeout 180s

echo "Deployed. Run scripts/smoke-test.sh to verify."