# Project Aether Makefile
# ========================
# Common tasks for development, testing, and deployment

.PHONY: help install dev run run-ui run-prod up up-full up-ui up-all down migrate test test-unit test-int test-e2e lint format typecheck serve discover chat status mlflow mlflow-up clean ui-dev ui-build ui-install build-sandbox

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
	@echo "URLs (when running):"
	@echo "  API:        http://localhost:$(API_PORT)"
	@echo "  UI:         http://localhost:$(WEBUI_PORT)"
	@echo "  MLflow:     http://localhost:$(MLFLOW_PORT)"

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

# Development mode: infra in containers, API on host with hot-reload
run: up migrate
	@echo ""
	@echo "Starting API server with hot-reload..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	uv run aether serve --reload

# Development + UI (API on host, UI dev server)
run-ui: up migrate
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
	$(COMPOSE) --profile full --profile ui down
	@echo "All services stopped."

# ============================================================================
# Infrastructure (building blocks)
# ============================================================================
# Use these if you want more control over what's running

up:
	$(COMPOSE) up -d postgres mlflow redis
	@echo "Waiting for services..."
	@sleep 3
	@echo ""
	@echo "Infrastructure ready:"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  MLflow:     http://localhost:$(MLFLOW_PORT)"
	@echo "  Redis:      localhost:6379"

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

check: lint typecheck
	@echo "All quality checks passed!"

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
