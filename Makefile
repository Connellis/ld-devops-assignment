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
	ruff check apps

test: ## Run pytest for both apps
	cd apps/server && pytest -q
	cd apps/client && pytest -q