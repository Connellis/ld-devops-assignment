#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLUSTER_NAME="devops-assignment"

docker build -t app2-server:local "$ROOT_DIR/apps/server"
docker build -t app1-client:local "$ROOT_DIR/apps/client"

# kind has no registry - load the local images straight into the node.
# CI replaces this with a push to GHCR.
kind load docker-image app2-server:local --name "$CLUSTER_NAME"
kind load docker-image app1-client:local --name "$CLUSTER_NAME"

echo "Built and loaded app2-server:local and app1-client:local into kind."