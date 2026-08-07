# App1 / App2 — DevOps Assignment

Two small Python services deployed with production-grade DevOps practices:

- **App2 (server)** — FastAPI, one endpoint (`/work`), requires a shared-secret
  header, logs every request as structured JSON, returns `200`.
- **App1 (client)** — FastAPI + a background polling loop, calls App2 on an
  interval, logs the target address and response code as structured JSON.

Everything is containerized, deployed to a local Kubernetes cluster (kind) with
namespace isolation, and wired into a CI/CD pipeline that builds, scans, signs,
and pushes images to GHCR, then deploys and verifies them against an ephemeral
cluster.

---

## 0. Prerequisites

| Tool | Purpose | Notes |
|---|---|---|
| Docker Desktop | Build images, run kind | macOS or WSL2 backend both work |
| [`kind`](https://kind.sigs.k8s.io/) | Local Kubernetes | `go install sigs.k8s.io/kind@v0.24.0` or download the binary |
| `kubectl` | Talk to the cluster | Matching your kind's Kubernetes version (1.31.x) |
| `helm` | Install the chart | `brew install helm` or the official installer |
| `openssl` | Generate the shared secret | Present by default on macOS and most Linux distros |
| `curl` | Smoke testing | Present by default |

Verify everything is on PATH:

```bash
docker --version
kind --version
kubectl version --client
helm version
openssl version
```

---

## 1. Local development (running the tests)

The Docker images deliberately do **not** use a virtualenv (see "Design
decisions" below), but for working on the code on your host machine a venv is
the standard, correct tool. Each app ships a `requirements-dev.txt` (runtime
deps + `pytest` + `httpx` + `ruff`):

```bash
cd apps/server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Do the same for `apps/client`. The `.venv/` directory is gitignored, so it
won't pollute the repo. Lint both apps with `ruff check apps` (from the repo
root, with either venv active).

---

## 2. Local deployment (kind + Helm)

The whole flow is wrapped in a `Makefile` — `make help` lists every target.

```bash
# 1. Generate a random shared secret into a gitignored .env file
make init

# 2. Create the kind cluster with Calico (NetworkPolicy enforcement)
make kind-up

# 3. Build the images and load them into the cluster
make build-and-load

# 4. Install/upgrade the Helm release
make deploy

# 5. Verify app-to-app traffic and network isolation
make smoke-test
```

### What each step does

**`make kind-up`** creates a 2-node `kind` cluster **with the default CNI
disabled**, and installs [Calico](https://www.tigera.io/project-calico/) in its
place.

> **Why this matters:** kind's default CNI (`kindnetd`) does not enforce
> `NetworkPolicy` objects at all — it accepts them but silently does nothing.
> Without Calico (or another NetworkPolicy-capable CNI), every `NetworkPolicy`
> in the chart would be inert, and the namespace-isolation demo — the most
> important part of this assignment — wouldn't actually prove anything. This
> step takes 1–2 minutes; be patient.

**`make build-and-load`** builds both images and loads them straight into the
cluster's nodes. kind has no registry, so this bypasses one entirely — the
right tool for a fast local dev loop, but **not** how images reach the cluster
in CI (that goes through GHCR instead).

**`make deploy`** runs `helm upgrade --install` against the chart in
`helm/devops-assignment/`. The chart creates the `server` and `client`
namespaces (with restricted Pod Security Standard labels), the `server-auth`
Secret in both (same value, injected at install time), and every workload,
Service, NetworkPolicy, ResourceQuota, LimitRange, and PodDisruptionBudget.
The shared secret is read from `.env` if present, otherwise generated on the
fly.

**`make smoke-test`** checks, in order:
- App1's logs show repeated `200` responses against App2.
- App2's logs show it handling those requests.
- A direct port-forwarded request with the correct secret returns `200`;
  with the wrong secret, `401`.
- **NetworkPolicy isolation**: a throwaway pod in the `default` namespace
  (i.e. *not* the `client` namespace) attempts to reach App2 and is
  correctly blocked. Seeing this fail/time out is the expected, correct
  result — it's proof the isolation is real, not just declared in YAML.

### Explore manually (optional)

```bash
kubectl get all -n server
kubectl get all -n client
kubectl get networkpolicy -A
kubectl -n server logs -f deployment/app2-server
kubectl -n client logs -f deployment/app1-client
```

### Tear down

```bash
make teardown
```

---

## 3. CI/CD (GitHub Actions)

Two workflows live in `.github/workflows/`:

**`ci.yml`** — runs on every push to `main` and every pull request:
- `lint` — `ruff check apps`
- `test` — `pytest` for both apps (matrix)
- `build-push` (main only) — builds both images with Buildx, pushes them to
  GHCR (`ghcr.io/<owner>/ld-devops-assignment/{server,client}`) tagged with
  the commit SHA, `main`, and semver tags on releases; scans each image with
  Trivy (fails on CRITICAL/HIGH); signs each image with cosign keyless signing
  via GitHub OIDC.

**`deploy-verify.yml`** — runs on every push to `main`:
- Spins up an ephemeral kind cluster with Calico.
- Installs the Helm chart with the freshly pushed GHCR images and the
  `SHARED_SECRET` from repository secrets.
- Runs `scripts/smoke-test.sh` to prove the deployment actually works.

### Repository secrets

Set one secret in the repo settings (Settings → Secrets and variables →
Actions):

| Name | Value |
|---|---|
| `SHARED_SECRET` | A random value, e.g. `openssl rand -hex 32` |

---

## 4. Repository layout

```
apps/
  server/            # App2 — FastAPI, one endpoint, auth, structured logs
  client/            # App1 — FastAPI + background polling loop
helm/
  devops-assignment/ # Helm chart: namespaces, deployments, services,
                      # network policies, quotas, limit ranges, PDB, secret
scripts/             # local tooling (kind, build-and-load, deploy, smoke-test)
.github/
  workflows/         # ci.yml + deploy-verify.yml
  dependabot.yml     # weekly dependency updates
kind-config.yaml     # 2-node kind cluster, default CNI disabled
Makefile             # one-command local flow
pyproject.toml       # ruff config
```

---

## 5. Design decisions

- **Both apps are Python/FastAPI** — same stack, same Dockerfile pattern,
  same structured-logging module (literally the same file, copied into both
  apps rather than published as a shared package — not worth the packaging
  overhead at this scale).
- **Real secret, real auth**: `/work` returns `401` without the correct
  `X-API-Key`. This is deliberately more than the assignment strictly
  requires, to have one genuine Secret to design around.
- **Distroless, non-root, read-only root filesystem, dropped capabilities,
  `seccompProfile: RuntimeDefault`** on both containers — see the
  Dockerfiles and the `securityContext` blocks in the chart's Deployment
  template.
- **No venv inside the images.** The distroless runtime image ships its own
  Python interpreter; a venv created in the builder would carry broken
  symlinks into the runtime (see the Dockerfile comments for the full
  explanation). Dependencies are installed flat with
  `pip install --target=/dependencies` and exposed via `PYTHONPATH`. For
  *local* development (running tests, linting) a normal venv is the right
  tool — see "Local development" above.
- **Default-deny NetworkPolicy** in both namespaces, with narrow, explicit
  allows (client → server on 8000, both → kube-system on 53 for DNS).
- **`ResourceQuota` + `LimitRange`** in both namespaces so neither can
  starve the other or the node.
- **Helm chart instead of raw manifests** — one source of truth for local
  (kind) and CI (ephemeral kind) deployment, with image repo/tag and the
  shared secret parameterized.
- **What's intentionally *not* here**: Ingress (nothing external-facing),
  HorizontalPodAutoscaler (no variable load to autoscale against), Vault /
  service mesh / OPA (disproportionate at this scale).

---

## 6. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `kind create cluster` hangs on "Waiting for nodes" | Docker Desktop needs more resources (Settings → Resources); 2 nodes need a bit of headroom |
| Client logs show connection errors, not `401`/`200` | Check `kubectl -n server get pods` — is App2 actually Running/Ready? |
| Client logs show `401` instead of `200` | The two `server-auth` Secrets don't match — re-run `make deploy` (delete `.env` first if you want a fresh random value in both) |
| NetworkPolicy smoke test *succeeds* in reaching App2 (should fail) | Calico isn't installed/ready — check `kubectl -n kube-system get pods \| grep calico`; re-run `make kind-up` |
| `ImagePullBackOff` on either Deployment | Images weren't loaded into kind — re-run `make build-and-load`, confirm the cluster name matches (`devops-assignment`) |
| `exec: "/venv/bin/python": stat ... no such file or directory` | A distroless-specific gotcha: `python -m venv` creates symlinks back into the *builder* image, which break when copied into a different base image. The Dockerfiles use `pip install --target=/dependencies` + `PYTHONPATH` instead, with the builder pinned to the exact Python version (3.11) that Debian 12/distroless ships. If you ever modify the Dockerfiles and reintroduce a venv, this is why it will break again. |