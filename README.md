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
# Prerequisites: Python 3.11+, uv, Podman

# Install and configure
make install
cp .env.example .env
# Edit .env with your HA_TOKEN, HA_URL, and OPENAI_API_KEY

# Start development environment (single command!)
make run

# Or with chat UI
make run-ui
open http://localhost:3000
```

## Deployment Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Development** | `make run` | API on host with hot-reload |
| **Dev + Chat UI** | `make run-ui` | Above + Open WebUI interface |
| **Production** | `make run-prod` | Everything containerized |
| **Stop** | `make down` | Stop all services |

```
┌─────────────────────────────────────────────────────────┐
│  Open WebUI (localhost:3000)                            │
│  Beautiful chat interface with streaming                │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  Aether API (localhost:8000)                            │
│  ├─ /v1/chat/completions  (OpenAI-compatible)           │
│  └─ /api/conversations    (Native API)                  │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   PostgreSQL      MLflow        Redis
     :5432         :5002         :6379
```

See [Architecture Documentation](docs/architecture.md) for detailed diagrams.

## LLM Configuration

Project Aether supports multiple LLM backends. Configure in your `.env`:

### OpenRouter (Recommended - access to 100+ models)
```bash
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL=anthropic/claude-sonnet-4
```

### Local Ollama (Free, private)
```bash
LLM_PROVIDER=ollama
LLM_MODEL=mistral:latest
# No API key needed
```

### OpenAI Direct
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-openai-key
LLM_MODEL=gpt-4o
```

### Google Gemini
```bash
LLM_PROVIDER=google
GOOGLE_API_KEY=your-google-key
LLM_MODEL=gemini-2.0-flash
```

### Other OpenAI-compatible APIs
```bash
LLM_PROVIDER=together  # or groq, custom
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.together.xyz/v1
LLM_MODEL=meta-llama/Llama-3-70b-chat-hf
```

## Development

```bash
# Install with dev dependencies
uv sync

# Start PostgreSQL + MLflow containers (MLflow on http://localhost:5001)
make mlflow-up

# Or start local MLflow server (defaults to http://localhost:5002)
make mlflow

# Run tests
uv run pytest

# Lint and format
uv run ruff check --fix
uv run ruff format

# Type check
uv run mypy src
```

## Documentation

- [Architecture Overview](docs/architecture.md) - System design, deployment modes, data flows
- [Quickstart Guide](specs/001-project-aether/quickstart.md) - Getting started
- [Data Model](specs/001-project-aether/data-model.md) - Database schema
- [Technical Decisions](specs/001-project-aether/research.md) - Research and rationale
- [API Documentation](http://localhost:8000/docs) (when running)

## License

MIT
