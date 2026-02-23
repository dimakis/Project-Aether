# Project Aether Makefile
# ========================
# Common tasks for development, testing, and deployment

.PHONY: help install dev run run-ui run-prod run-distributed run-distributed-build down-distributed run-observed down-observed up up-full up-ui up-all down migrate build-base test test-unit test-int test-e2e lint format format-check typecheck check ci-local security-scan serve discover chat status mlflow mlflow-up clean ui-dev ui-build ui-install build-sandbox ensure-sandbox build-services openapi

# Default target
MLFLOW_PORT ?= 5002
API_PORT ?= 8000
WEBUI_PORT ?= 3000

help:
	@echo "Project Aether - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Deployment (single commands):"
	@echo "  make run         - Start development environment (infra + API with hot-reload)"
	@echo "  make run-ui      - Start dev environment + UI dev server"
	@echo "  make run-prod    - Start production stack (everything containerized)"
	@echo "  make down        - Stop all services and containers"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install dependencies with uv"
	@echo "  make dev         - Full dev setup (install + infra + migrate)"
	@echo ""
	@echo "Infrastructure (building blocks):"
	@echo "  make up          - Start infrastructure containers only"
	@echo "  make up-ui       - Start infrastructure + UI container"
	@echo "  make serve       - Start API server on host (hot-reload)"
	@echo "  make logs        - View container logs"
	@echo "  make psql        - Connect to PostgreSQL"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     - Run Alembic migrations"
	@echo "  make migrate-new - Create new migration (NAME=description)"
	@echo "  make migrate-down- Rollback last migration"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests"
	@echo "  make test-unit   - Run unit tests only"
	@echo "  make test-int    - Run integration tests"
	@echo "  make test-cov    - Run tests with coverage report"
	@echo ""
	@echo "Quality:"
	@echo "  make lint        - Run ruff linter"
	@echo "  make format      - Format code with ruff"
	@echo "  make check       - Run all quality checks"
	@echo "  make ci-local    - Run full CI locally (lint + typecheck + security + unit tests)"
	@echo ""
	@echo "Application:"
	@echo "  make chat        - Start interactive CLI chat"
	@echo "  make discover    - Run entity discovery"
	@echo "  make status      - Show system status"
	@echo ""
	@echo "UI:"
	@echo "  make ui-install  - Install UI dependencies"
	@echo "  make ui-dev      - Start UI dev server"
	@echo "  make ui-build    - Build UI for production"
	@echo ""
	@echo "Sandbox:"
	@echo "  make build-sandbox - Build sandbox image for Data Scientist analysis"
	@echo ""
	@echo "Distributed Mode (A2A agent services):"
	@echo "  make run-distributed       - Start distributed stack (gateway + UI + agent containers)"
	@echo "  make run-distributed-build - Same but rebuilds images first"
	@echo "  make down-distributed      - Stop distributed services"
	@echo "  make build-base            - Build shared base image (deps only, run once)"
	@echo "  make build-services        - Build all agent service images (fast, uses base)"
	@echo ""
	@echo "Observability (distributed + metrics/logs):"
	@echo "  make run-observed          - Distributed + Prometheus + Grafana + Loki"
	@echo "  make down-observed         - Stop everything including observability"
	@echo ""
	@echo "Docs:"
	@echo "  make openapi       - Regenerate OpenAPI spec from FastAPI"
	@echo ""
	@echo "URLs (when running):"
	@echo "  API:        http://localhost:$(API_PORT)"
	@echo "  UI:         http://localhost:$(WEBUI_PORT)"
	@echo "  MLflow:     http://localhost:$(MLFLOW_PORT)"
	@echo ""
	@echo "URLs (distributed mode):"
	@echo "  Architect:          http://localhost:8001"
	@echo "  DS Orchestrator:    http://localhost:8002"
	@echo "  DS Analysts:        http://localhost:8003"
	@echo "  Developer:          http://localhost:8004"
	@echo "  Librarian:          http://localhost:8005"
	@echo "  Dashboard Designer: http://localhost:8006"
	@echo "  Orchestrator:       http://localhost:8007"

# ============================================================================
# Setup
# ============================================================================

install:
	uv sync

dev: install up migrate
	@echo "Development environment ready!"
	@echo "Run 'make run' to start everything"

# ============================================================================
# Deployment Modes (single commands)
# ============================================================================
# These are the primary commands for running Aether:
#   make run      - Development (hot-reload)
#   make run-ui   - Development + chat UI
#   make run-prod - Production (containerized)
#   make down     - Stop everything

COMPOSE := podman-compose -f infrastructure/podman/compose.yaml

# Build sandbox image only if not already present (non-fatal)
ensure-sandbox:
	@podman image exists aether-sandbox:latest 2>/dev/null \
		&& echo "  Sandbox image: aether-sandbox:latest (exists)" \
		|| ($(MAKE) build-sandbox 2>/dev/null || echo "  Sandbox image skipped (podman not available)")

# Development mode: infra in containers, API on host with hot-reload
run: up migrate ensure-sandbox
	@echo ""
	@echo "Starting API server with hot-reload..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	uv run aether serve --reload

# Development + UI (API on host, UI dev server)
run-ui: up migrate ensure-sandbox
	@echo ""
	@echo "Starting API server + UI dev server..."
	@echo "UI:  http://localhost:$(WEBUI_PORT)"
	@echo "API: http://localhost:$(API_PORT)"
	@echo "Press Ctrl+C to stop"
	@echo ""
	@trap 'kill 0' EXIT; \
		cd ui && npm run dev & \
		uv run aether serve --reload

# Production mode: everything containerized
run-prod: migrate-container
	AETHER_API_UPSTREAM=http://app:8000 $(COMPOSE) --profile full --profile ui up -d --build
	@echo ""
	@echo "Production stack running:"
	@echo "  Open WebUI: http://localhost:$(WEBUI_PORT)"
	@echo "  API:        http://localhost:$(API_PORT)"
	@echo "  MLflow:     http://localhost:$(MLFLOW_PORT)"
	@echo ""
	@echo "View logs: make logs"

# Run migrations inside container (for production mode)
migrate-container:
	$(COMPOSE) up -d postgres
	@echo "Waiting for PostgreSQL..."
	@sleep 3
	uv run alembic upgrade head

# Stop all services
down:
	@echo "Stopping all Aether services..."
	-$(COMPOSE_DIST) --profile full --profile ui down 2>/dev/null
	$(COMPOSE) --profile full --profile ui down
	@echo "All services stopped."

# ============================================================================
# Infrastructure (building blocks)
# ============================================================================
# Use these if you want more control over what's running

up:
	$(COMPOSE) up -d postgres mlflow
	@echo "Waiting for services..."
	@sleep 3
	@echo ""
	@echo "Infrastructure ready:"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  MLflow:     http://localhost:$(MLFLOW_PORT)"

up-ui:
	$(COMPOSE) --profile ui up -d --build
	@echo "Waiting for services..."
	@sleep 3
	@echo ""
	@echo "Infrastructure + Aether UI ready:"
	@echo "  UI:     http://localhost:$(WEBUI_PORT)"
	@echo "  MLflow: http://localhost:$(MLFLOW_PORT)"

mlflow:
	@chmod +x scripts/mlflow_local.sh 2>/dev/null || true
	./scripts/mlflow_local.sh

logs:
	$(COMPOSE) --profile full --profile ui logs -f

logs-app:
	$(COMPOSE) logs -f app

psql:
	podman exec -it aether-postgres psql -U aether -d aether

# ============================================================================
# Database
# ============================================================================

migrate:
	uv run alembic upgrade head

migrate-new:
	@if [ -z "$(NAME)" ]; then \
		echo "Usage: make migrate-new NAME=description"; \
		exit 1; \
	fi
	uv run alembic revision --autogenerate -m "$(NAME)"

migrate-down:
	uv run alembic downgrade -1

migrate-history:
	uv run alembic history

# ============================================================================
# Testing (TDD Workflow - Constitution V)
# ============================================================================

test:
	uv run pytest tests/ -v --tb=short

test-unit:
	uv run pytest tests/unit/ -v --tb=short

test-int:
	uv run pytest tests/integration/ -v --tb=short

test-e2e:
	uv run pytest tests/e2e/ -v --tb=short

test-security:
	uv run pytest tests/unit/test_security_hardening.py tests/unit/test_security_headers.py -v --tb=short

test-ci-unit:
	uv run pytest tests/unit/ -v --tb=short -m "not slow" --junitxml=reports/unit.xml

test-ci-integration:
	uv run pytest tests/integration/ -v --tb=short --junitxml=reports/integration.xml

test-cov:
	uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-watch:
	uv run pytest-watch -- tests/ -v --tb=short

# Run specific test file (usage: make test-file FILE=tests/unit/test_foo.py)
test-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make test-file FILE=tests/unit/test_foo.py"; \
		exit 1; \
	fi
	uv run pytest $(FILE) -v --tb=short

# TDD helper: run test, expect failure (red phase)
test-red:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make test-red FILE=tests/unit/test_foo.py"; \
		exit 1; \
	fi
	@echo "🔴 Red Phase: Test should FAIL"
	-uv run pytest $(FILE) -v --tb=short
	@echo ""
	@echo "If test failed as expected, implement the feature and run 'make test-green FILE=$(FILE)'"

# TDD helper: run test, expect success (green phase)
test-green:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make test-green FILE=tests/unit/test_foo.py"; \
		exit 1; \
	fi
	@echo "🟢 Green Phase: Test should PASS"
	uv run pytest $(FILE) -v --tb=short
	@echo ""
	@echo "✅ Test passed! Ready to commit test + implementation together."

# ============================================================================
# Quality
# ============================================================================

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

typecheck:
	uv run mypy src/ --ignore-missing-imports

check: format-check lint typecheck
	@echo "All quality checks passed!"

# Run CI checks locally (mirrors GitHub Actions pipeline)
# Run this before squashing and pushing a feature branch
ci-local: format-check lint typecheck security-scan test-unit
	@echo ""
	@echo "All CI checks passed! Safe to squash, push, and open PR."

security-scan:
	uv run bandit -r src/ -c pyproject.toml

format-check:
	uv run ruff format --check src/ tests/

# ============================================================================
# Application
# ============================================================================

serve:
	uv run aether serve

discover:
	uv run aether discover

chat:
	uv run aether chat

status:
	uv run aether status

entities:
	uv run aether entities

proposals:
	uv run aether proposals list

# ============================================================================
# Demos
# ============================================================================

demo-us1:
	@chmod +x demo_us1.sh 2>/dev/null || true
	./demo_us1.sh

demo-us2:
	@chmod +x demo_us2.sh 2>/dev/null || true
	./demo_us2.sh

# ============================================================================
# UI (React Frontend)
# ============================================================================

ui-install:
	cd ui && npm install

ui-dev:
	cd ui && npm run dev

ui-build:
	cd ui && npm run build

ui-lint:
	cd ui && npm run lint

# ============================================================================
# Sandbox
# ============================================================================

build-sandbox:
	@echo "Building Data Scientist sandbox image..."
	podman build -t aether-sandbox:latest -f infrastructure/podman/Containerfile.sandbox .
	@echo ""
	@echo "Sandbox image built: aether-sandbox:latest"
	@echo "The Data Scientist can now run analysis scripts with numpy, pandas, scipy, etc."

# ============================================================================
# Distributed Agent Services
# ============================================================================

COMPOSE_DIST := $(COMPOSE) -f infrastructure/podman/compose.distributed.yaml

run-distributed: migrate-container build-base
	$(COMPOSE_DIST) --profile full --profile ui up -d
	@echo ""
	@echo "Distributed mode started:"
	@echo "  Gateway:           http://localhost:$(API_PORT)"
	@echo "  UI:                http://localhost:$(WEBUI_PORT)"
	@echo "  Architect:         http://localhost:8001"
	@echo "  DS Orchestrator:   http://localhost:8002"
	@echo "  DS Analysts:       http://localhost:8003"
	@echo "  Developer:         http://localhost:8004"
	@echo "  Librarian:         http://localhost:8005"
	@echo "  Dashboard Designer: http://localhost:8006"
	@echo "  Orchestrator:      http://localhost:8007"
	@echo ""
	@echo "Tip: run 'make build-services' first if images are stale"

run-distributed-build: migrate-container build-services
	$(COMPOSE_DIST) --profile full --profile ui up -d --build
	@echo ""
	@echo "Distributed mode started (with rebuild)"

down-distributed:
	@echo "Stopping distributed services..."
	-$(COMPOSE_DIST) -f infrastructure/podman/compose.observability.yaml --profile full --profile ui down 2>/dev/null
	$(COMPOSE_DIST) --profile full --profile ui down
	@echo "All distributed services stopped."

COMPOSE_OBS := $(COMPOSE_DIST) -f infrastructure/podman/compose.observability.yaml

run-observed: migrate-container build-base
	$(COMPOSE_OBS) --profile full --profile ui up -d
	@echo ""
	@echo "Distributed + Observability mode started:"
	@echo "  Gateway:           http://localhost:$(API_PORT)"
	@echo "  UI:                http://localhost:$(WEBUI_PORT)"
	@echo "  Prometheus:        http://localhost:9090"
	@echo "  Grafana:           http://localhost:3001 (admin/admin)"
	@echo "  Agent services:    :8001-:8007"

down-observed:
	@echo "Stopping all services (distributed + observability)..."
	$(COMPOSE_OBS) --profile full --profile ui down
	@echo "All services stopped."

build-base:
	@echo "Building shared base image (deps only — run once or when pyproject.toml changes)..."
	podman build -t aether-base:latest -f infrastructure/podman/Containerfile.base .
	@echo "Base image built: aether-base:latest"

build-services: build-base
	@echo "Building all agent service images (lightweight, uses aether-base)..."
	podman build --build-arg AETHER_SERVICE=architect -t aether-architect:latest -f infrastructure/podman/Containerfile.service .
	podman build --build-arg AETHER_SERVICE=ds_orchestrator -t aether-ds-orchestrator:latest -f infrastructure/podman/Containerfile.service .
	podman build --build-arg AETHER_SERVICE=ds_analysts -t aether-ds-analysts:latest -f infrastructure/podman/Containerfile.service .
	podman build --build-arg AETHER_SERVICE=developer -t aether-developer:latest -f infrastructure/podman/Containerfile.service .
	podman build --build-arg AETHER_SERVICE=librarian -t aether-librarian:latest -f infrastructure/podman/Containerfile.service .
	podman build --build-arg AETHER_SERVICE=dashboard_designer -t aether-dashboard-designer:latest -f infrastructure/podman/Containerfile.service .
	podman build --build-arg AETHER_SERVICE=orchestrator -t aether-orchestrator:latest -f infrastructure/podman/Containerfile.service .
	@echo "Built all 7 agent service images"

# ============================================================================
# Docs
# ============================================================================

openapi:
	@echo "Generating OpenAPI spec from FastAPI app..."
	uv run python scripts/generate_openapi.py

# ============================================================================
# Utilities
# ============================================================================

clean:
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Show current git status
git-status:
	@echo "Current branch:"
	@git branch --show-current || echo "(detached HEAD)"
	@echo ""
	@echo "Recent commits:"
	@git log --oneline -5
	@echo ""
	@echo "Working tree status:"
	@git status --short

# Quick commit helper for TDD (usage: make commit MSG="feat: description")
commit:
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make commit MSG=\"feat(scope): description\""; \
		exit 1; \
	fi
	git add -A
	git commit -m "$(MSG)"
