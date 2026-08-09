SHELL := /bin/bash

.PHONY: help init kind-up build-and-load deploy smoke-test lint test teardown

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'

init: ## Generate .env with a random shared secret
	./scripts/generate-local-env.sh

kind-up: ## Create the kind cluster with Calico (NetworkPolicy enforcement)
	./scripts/kind-up.sh

build-and-load: ## Build images and load them into kind
	./scripts/build-and-load.sh

deploy: ## Install/upgrade the Helm release (uses local images)
	./scripts/deploy.sh

smoke-test: ## Verify app-to-app traffic and network isolation
	./scripts/smoke-test.sh

teardown: ## Delete the kind cluster
	./scripts/teardown.sh

lint: ## Ruff check (run inside either app venv)
	@if [[ -x .venv/bin/ruff ]]; then \
		.venv/bin/ruff check apps; \
	elif [[ -x apps/server/.venv/bin/ruff ]]; then \
		apps/server/.venv/bin/ruff check apps; \
	elif [[ -x apps/client/.venv/bin/ruff ]]; then \
		apps/client/.venv/bin/ruff check apps; \
	else \
		echo "Ruff not found in .venv, apps/server/.venv, or apps/client/.venv." >&2; \
		echo "Create an app venv and install its requirements-dev.txt first." >&2; \
		exit 1; \
	fi

test: ## Run pytest for both apps
	cd apps/server && pytest -q
	cd apps/client && pytest -q