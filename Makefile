# Project Aether Makefile
# ========================
# Common tasks for development, testing, and deployment

.PHONY: help install dev up up-full up-ui up-all down migrate test test-unit test-int test-e2e lint format typecheck serve discover chat status mlflow mlflow-up clean

# Default target
MLFLOW_PORT ?= 5002
help:
	@echo "Project Aether - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install dependencies with uv"
	@echo "  make dev         - Full dev setup (install + infra + migrate)"
	@echo ""
	@echo "Infrastructure (Deployment Modes):"
	@echo "  make up          - Infra only (dev mode, run API on host with hot-reload)"
	@echo "  make up-full     - Everything containerized (production-like)"
	@echo "  make up-ui       - Infra + Open WebUI (API on host)"
	@echo "  make up-all      - Full stack including UI (all containerized)"
	@echo "  make down        - Stop all containers"
	@echo "  make logs        - View container logs"
	@echo "  make logs-app    - View API container logs only"
	@echo "  make psql        - Connect to PostgreSQL"
	@echo "  make mlflow      - Start local MLflow server (SQLite, port $(MLFLOW_PORT))"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     - Run Alembic migrations"
	@echo "  make migrate-new - Create new migration (NAME=description)"
	@echo "  make migrate-down- Rollback last migration"
	@echo ""
	@echo "Testing (TDD Workflow):"
	@echo "  make test        - Run all tests"
	@echo "  make test-unit   - Run unit tests only"
	@echo "  make test-int    - Run integration tests only"
	@echo "  make test-e2e    - Run E2E tests only"
	@echo "  make test-cov    - Run tests with coverage report"
	@echo "  make test-watch  - Run tests in watch mode"
	@echo ""
	@echo "Quality:"
	@echo "  make lint        - Run ruff linter"
	@echo "  make format      - Format code with ruff"
	@echo "  make typecheck   - Run mypy type checker"
	@echo "  make check       - Run all quality checks (lint + typecheck)"
	@echo ""
	@echo "Application:"
	@echo "  make serve       - Start the API server"
	@echo "  make discover    - Run entity discovery"
	@echo "  make chat        - Start interactive chat"
	@echo "  make status      - Show system status"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       - Remove build artifacts and caches"
	@echo "  make demo-us1    - Run US1 demo"
	@echo "  make demo-us2    - Run US2 demo"

# ============================================================================
# Setup
# ============================================================================

install:
	uv sync

dev: install up migrate
	@echo "Development environment ready!"
	@echo "Run 'make serve' to start the API server"
	@echo "Run 'make discover' to populate entities from Home Assistant"

# ============================================================================
# Infrastructure
# ============================================================================
# Deployment modes:
#   make up          - Infrastructure only (dev mode, API on host)
#   make up-full     - Everything containerized (production-like)
#   make up-ui       - Infrastructure + Open WebUI (API on host)
#   make up-all      - Full stack including UI

COMPOSE := podman-compose -f infrastructure/podman/compose.yaml

up:
	$(COMPOSE) up -d postgres mlflow redis
	@echo "Waiting for services..."
	@sleep 3
	@echo ""
	@echo "Infrastructure ready:"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  MLflow:     localhost:$(MLFLOW_PORT)"
	@echo "  Redis:      localhost:6379"
	@echo ""
	@echo "Run 'make serve' to start the API on host (hot-reload)"

up-full:
	$(COMPOSE) --profile full up -d --build
	@echo ""
	@echo "Full containerized stack running:"
	@echo "  API:        localhost:8000"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  MLflow:     localhost:$(MLFLOW_PORT)"
	@echo ""
	@echo "View logs: make logs"

up-ui:
	$(COMPOSE) --profile ui up -d
	@echo ""
	@echo "Infrastructure + Open WebUI running:"
	@echo "  Open WebUI: http://localhost:3000"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  MLflow:     localhost:$(MLFLOW_PORT)"
	@echo ""
	@echo "Run 'make serve' to start the API on host"

up-all:
	AETHER_API_URL=http://app:8000/api $(COMPOSE) --profile full --profile ui up -d --build
	@echo ""
	@echo "Full stack with UI running:"
	@echo "  Open WebUI: http://localhost:3000"
	@echo "  API:        localhost:8000"
	@echo "  MLflow:     localhost:$(MLFLOW_PORT)"

mlflow:
	@chmod +x scripts/mlflow_local.sh 2>/dev/null || true
	./scripts/mlflow_local.sh

mlflow-up:
	$(COMPOSE) up -d postgres mlflow
	@echo "PostgreSQL and MLflow are running on localhost:5432 and :$(MLFLOW_PORT)"

down:
	$(COMPOSE) --profile full --profile ui down

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
