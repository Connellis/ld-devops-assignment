#!/usr/bin/env bash
set -euo pipefail

echo "===== app1-client logs (should show repeated 200s) ====="
kubectl -n client logs deployment/app1-client --tail=10

echo
echo "===== app2-server logs (should show handled requests) ====="
kubectl -n server logs deployment/app2-server --tail=10

echo
echo "===== direct check via port-forward ====="
kubectl -n server port-forward svc/app2-server 18000:8000 >/tmp/port-forward.log 2>&1 &
PF_PID=$!
trap 'kill "$PF_PID" 2>/dev/null || true' EXIT

echo "Waiting for the port-forward to become ready..."
port_forward_ready=false
for _ in $(seq 1 30); do
  if curl --silent --fail --max-time 1 http://localhost:18000/healthz >/dev/null; then
    port_forward_ready=true
    break
  fi
  sleep 1
done
if [[ "$port_forward_ready" != true ]]; then
  echo "Port-forward did not become ready within 30 seconds." >&2
  cat /tmp/port-forward.log >&2
  exit 1
fi

SECRET="$(kubectl -n server get secret server-auth -o jsonpath='{.data.SHARED_SECRET}' | base64 -d)"
echo -n "GET /work with correct secret -> "
curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-API-Key: $SECRET" http://localhost:18000/work
echo -n "GET /work with WRONG secret   -> "
curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-API-Key: wrong" http://localhost:18000/work

echo
echo "===== NetworkPolicy isolation check (should fail / time out) ====="
echo "Attempting to reach app2-server from a throwaway pod OUTSIDE the client namespace..."
kubectl run netpol-check --rm -i --restart=Never --image=curlimages/curl:8.10.1 \
  --namespace=default --quiet -- \
  curl -s -m 5 -o /dev/null -w "HTTP %{http_code}\n" http://app2-server.server.svc.cluster.local:8000/work \
  || echo "(no response - NetworkPolicy is correctly blocking this pod)"
