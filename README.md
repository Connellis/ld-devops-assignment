# App1 / App2 DevOps Assignment

This repository contains two small FastAPI services:

- **App2 (server)** exposes `GET /work` and checks the `X-API-Key` header.
- **App1 (client)** polls App2 periodically and logs the response status.

Both services are containerized and deployed with Helm to Kubernetes. The deployment uses separate namespaces, NetworkPolicies, resource limits, and a shared secret for authentication.

## Prerequisites

Install Docker Desktop, [kind](https://kind.sigs.k8s.io/), kubectl, Helm, OpenSSL, and curl.

## Run locally

From the repository root:

```bash
make init
make kind-up
make build-and-load
make deploy
make smoke-test
```

These commands generate a local secret, create a two-node kind cluster with Calico, build and load the images, install the Helm release, and run the smoke tests.

Inspect the running services with:

```bash
kubectl get all -n server
kubectl get all -n client
kubectl -n server logs -f deployment/app2-server
kubectl -n client logs -f deployment/app1-client
```

Remove the local cluster with:

```bash
make teardown
```

## Deploy with registry images (production-style)

The local workflow above builds and loads images directly into kind. In a production-like setup, images are built, pushed to a registry (GHCR), and pulled by the cluster. This is the same flow the CI pipeline uses.

### 1. Build and push images to GHCR

```bash
docker build -t ghcr.io/<your-username>/ld-devops-assignment/server:main apps/server
docker build -t ghcr.io/<your-username>/ld-devops-assignment/client:main apps/client

docker push ghcr.io/<your-username>/ld-devops-assignment/server:main
docker push ghcr.io/<your-username>/ld-devops-assignment/client:main
```

Or push via the CI pipeline — pushes to `main` automatically build and publish both images to GHCR.

### 2. Create the cluster

```bash
make kind-up
```

### 3. Create the GHCR pull secret

kind needs credentials to pull private GHCR images. Create a Personal Access Token (PAT) with `read:packages` scope, then:

```bash
for namespace in server client; do
  kubectl -n "$namespace" create secret docker-registry ghcr-pull \
    --docker-server=ghcr.io \
    --docker-username=<your-github-username> \
    --docker-password=<your-PAT> \
    --dry-run=client -o yaml | kubectl apply -f -
done
```

### 4. Deploy with Helm

```bash
SHARED_SECRET="$(openssl rand -hex 32)"

helm upgrade --install devops-assignment helm/devops-assignment \
  --namespace default --create-namespace \
  --set global.sharedSecret="$SHARED_SECRET" \
  --set server.image.repository=ghcr.io/<your-username>/ld-devops-assignment/server \
  --set server.image.tag=main \
  --set client.image.repository=ghcr.io/<your-username>/ld-devops-assignment/client \
  --set client.image.tag=main \
  --set global.imagePullSecrets[0].name=ghcr-pull \
  --wait --timeout 180s
```

### 5. Verify

```bash
./scripts/smoke-test.sh
```

## Tests and linting

```bash
make lint
make test
```

For local application development, create a virtual environment in the application directory and install its development requirements:

```bash
cd apps/server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Repeat the same steps in `apps/client` when needed.

## GitHub Actions

### CI (`.github/workflows/ci.yml`)

Pull requests and pushes to `main` run linting and tests. Pushes to `main` also build and publish both images to GHCR, scan them with Trivy, upload the scan results, and sign the images with Cosign using GitHub OIDC.

Trivy checks for HIGH and CRITICAL vulnerabilities. The workflow currently uses `exit-code: "0"`, so findings are reported but do not fail the build. Set it to `"1"` to block delivery when such findings are present.

### Deploy & Verify (`.github/workflows/deploy-verify.yml`)

On every push to `main`, this workflow creates a fresh kind cluster on the GitHub runner, installs Calico, deploys the GHCR images with Helm, and runs the smoke tests.

The cluster is temporary and is removed with the runner after the job finishes. This workflow verifies the deployment; it is not a permanent production environment.

## GitHub repository secret

Add this Actions secret under **Settings → Secrets and variables → Actions**:

| Name | Value |
| --- | --- |
| `SHARED_SECRET` | A random value, for example `openssl rand -hex 32` |

The workflows use the automatically provided `GITHUB_TOKEN` for GHCR access.

## Troubleshooting

### Pods are not ready

```bash
kubectl get pods -A
kubectl get events -A --sort-by=.lastTimestamp
```

For local deployments, check that Calico is ready:

```bash
kubectl -n kube-system get pods | grep calico
```

### `ImagePullBackOff`

For local kind deployments, rebuild and load the images:

```bash
make build-and-load
make deploy
```

For GitHub Actions, check that the image build completed and that the workflow has `packages: read` permission.

### Client requests are failing

```bash
kubectl -n client logs deployment/app1-client
kubectl -n server logs deployment/app2-server
```

The correct secret should produce `200` responses. A missing or incorrect `X-API-Key` should produce `401`.

### Network isolation test succeeds unexpectedly

The smoke test expects a pod in the `default` namespace to be unable to reach App2. Check that Calico is installed and ready; kind's default CNI does not enforce NetworkPolicies.

## Repository layout

```text
apps/server/        App2 FastAPI service
apps/client/        App1 polling service
helm/               Helm chart and Kubernetes resources
scripts/             Local cluster, deployment, and smoke-test scripts
.github/workflows/  CI and Deploy & Verify workflows