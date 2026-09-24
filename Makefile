# Single entry point for project commands. Works with GNU make on Linux, WSL and macOS.
.DEFAULT_GOAL := help
SHELL := /bin/bash

ENV_FILE := $(if $(wildcard .env),--env-file .env,)
COMPOSE  := docker compose -f infra/compose/docker-compose.yml $(ENV_FILE)
MONOLITH_URL ?= http://localhost:$(or $(MONOLITH_HOST_PORT),8000)

.PHONY: help up down clean logs test e2e lint fmt migrate

help: ## List targets
	@grep -hE '^[a-zA-Z0-9_%-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

up: ## Build and start core services; wait until healthy
	$(COMPOSE) up -d --build --wait
	@echo "--- $(MONOLITH_URL)/health/ready"; curl -fsS $(MONOLITH_URL)/health/ready; echo

down: ## Stop services
	$(COMPOSE) down

clean: ## Stop services and delete volumes (fresh state)
	$(COMPOSE) down -v --remove-orphans

logs: ## Tail logs: make logs s=<service>
	$(COMPOSE) logs -f $(s)

test: ## Unit + component tests (component tests need Docker)
	uv run pytest

e2e: ## End-to-end tests against the running stack
	@if ls tests/e2e/test_*.py >/dev/null 2>&1; then uv run pytest tests/e2e -m e2e; \
	else echo "No e2e tests yet (tests/e2e/test_*.py)"; exit 1; fi

lint: ## ruff check + ruff format --check + mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy libs/common/src monolith/src

fmt: ## Format and autofix
	uv run ruff format .
	uv run ruff check --fix .

migrate: ## alembic upgrade head (inside the running monolith container)
	$(COMPOSE) exec monolith alembic -c monolith/alembic.ini upgrade head

demo-%: ## Run scripts/demo/phase-N.sh, e.g. make demo-0
	@test -x scripts/demo/phase-$*.sh || { echo "scripts/demo/phase-$*.sh does not exist yet"; exit 1; }
	./scripts/demo/phase-$*.sh
