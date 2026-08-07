#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLUSTER_NAME="devops-assignment"
CALICO_VERSION="v3.28.0"

if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "kind cluster '$CLUSTER_NAME' already exists, skipping creation."
else
  echo "Creating kind cluster '$CLUSTER_NAME' (default CNI disabled)..."
  kind create cluster --name "$CLUSTER_NAME" --config "$ROOT_DIR/kind-config.yaml"

  echo "Installing Calico so NetworkPolicy is actually enforced..."
  kubectl apply -f "https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/calico.yaml"

  echo "Waiting for Calico to become ready (this can take a minute or two)..."
  kubectl -n kube-system rollout status daemonset/calico-node --timeout=180s
  kubectl -n kube-system rollout status deployment/calico-kube-controllers --timeout=180s

  echo "Waiting for nodes to report Ready..."
  kubectl wait --for=condition=Ready nodes --all --timeout=180s
fi

kubectl cluster-info --context "kind-$CLUSTER_NAME"
