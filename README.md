# Project Aether

> Agentic home automation system for Home Assistant

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Overview

Project Aether is an intelligent home automation system that uses AI agents to discover, manage, and optimize your Home Assistant setup. It features:

- **🔍 Smart Discovery**: Librarian agent discovers and categorizes all HA entities
- **💬 Conversational Design**: Chat with the Architect agent to design automations
- **📊 Energy Insights**: Data Scientist agent analyzes usage and suggests optimizations
- **🎨 Custom Dashboards**: Generate tailored Lovelace dashboards

## Constitution

This project follows strict principles defined in our [Constitution](.specify/memory/constitution.md):

1. **Safety First**: All automations require human approval (HITL)
2. **Isolation**: Generated scripts run in gVisor sandboxes
3. **Observability**: All agent actions traced via MLflow
4. **State**: LangGraph + PostgreSQL for reliable state management
5. **Reliability**: Comprehensive testing (80%+ coverage required)

## Quick Start

```bash
# Prerequisites: Python 3.11+, uv, Podman, gVisor

# Clone and install
cd home_agent
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your HA token and settings

# Start infrastructure
podman-compose -f infrastructure/podman/compose.yaml up -d

# Run migrations
uv run alembic upgrade head

# Discover entities
uv run aether discover

# Start chatting with the Architect
uv run aether chat
```

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Lint and format
uv run ruff check --fix
uv run ruff format

# Type check
uv run mypy src
```

## Documentation

- [Quickstart Guide](specs/001-project-aether/quickstart.md)
- [Data Model](specs/001-project-aether/data-model.md)
- [Technical Decisions](specs/001-project-aether/research.md)
- [API Documentation](http://localhost:8000/docs) (when running)

## License

MIT
