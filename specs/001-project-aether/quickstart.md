# Quickstart: Project Aether

**Feature Branch**: `001-project-aether`  
**Date**: 2026-02-03

## Prerequisites

- **Home Assistant**: Running instance with long-lived access token
- **Python**: 3.11+
- **Podman**: 4.0+ with rootless mode configured
- **gVisor**: runsc runtime installed and configured
- **PostgreSQL**: 15+ (can use containerized)
- **OpenAI API Key**: For LLM access

## Quick Setup (5 minutes)

### 1. Clone and Install

```bash
cd /Users/dsaridak/projects/home_agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values:
```

```ini
# Home Assistant
HA_TOKEN=your_long_lived_access_token
HA_URL=http://192.168.1.10:8123

# OpenAI
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql://aether:aether@localhost:5432/aether

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# Optional
LOG_LEVEL=INFO
```

### 3. Start Infrastructure

```bash
# Start PostgreSQL and MLflow
podman-compose -f infrastructure/podman/compose.yaml up -d

# Run database migrations
alembic upgrade head

# Verify services
curl http://localhost:5000/health  # MLflow
psql $DATABASE_URL -c "SELECT 1"   # PostgreSQL
```

### 4. Run Initial Discovery

```bash
# Start the Librarian agent to discover entities
aether discover

# Verify entities were discovered
aether entities list
```

### 5. Start the API Server

```bash
# Development mode with auto-reload
aether serve --reload

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

---

## Usage Examples

### Chat with the Architect

```bash
# Start a conversation
aether chat

# Or via API
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"initial_message": "I want to automate my morning routine"}'
```

### Query Entities (Natural Language)

```bash
# CLI
aether entities query "all lights in the living room"

# API
curl -X POST http://localhost:8000/api/v1/entities/query \
  -H "Content-Type: application/json" \
  -d '{"query": "all lights in the living room"}'
```

### Approve an Automation (HITL)

```bash
# List pending automations
aether automations list --status proposed

# Approve with comment
aether automations approve <automation-id> --comment "Looks good"

# Or reject
aether automations reject <automation-id> --reason "Too aggressive"
```

### Request Energy Analysis

```bash
# Request 30-day energy analysis
aether analyze energy --days 30

# View generated insights
aether insights list --type energy_optimization
```

---

## Development Workflow

### Run Tests

```bash
# Unit tests
pytest tests/unit

# Integration tests (requires running services)
pytest tests/integration

# Contract tests
pytest tests/contract

# All tests with coverage
pytest --cov=src --cov-report=html
```

### Lint and Format

```bash
# Format code
ruff format src tests

# Lint
ruff check src tests

# Type check
mypy src
```

### View MLflow Traces

```bash
# Open MLflow UI
open http://localhost:5000

# View specific experiment
mlflow experiments list
mlflow runs list --experiment-id 1
```

---

## Project Structure

```
home_agent/
├── src/
│   ├── agents/          # LangGraph agent implementations
│   ├── dal/             # Entity abstraction layer
│   ├── graph/           # LangGraph workflows
│   ├── sandbox/         # gVisor script execution
│   ├── storage/         # PostgreSQL models
│   ├── tracing/         # MLflow integration
│   ├── api/             # FastAPI endpoints
│   └── cli/             # CLI commands
├── tests/
├── infrastructure/
│   ├── podman/          # Container definitions
│   └── gvisor/          # Sandbox configuration
└── specs/               # Feature specifications
```

---

## Troubleshooting

### Home Assistant Connection Failed

```bash
# Test connectivity
curl -H "Authorization: Bearer $HA_TOKEN" $HA_URL/api/

# Check MCP tools
aether debug mcp
```

### gVisor Sandbox Issues

```bash
# Verify runsc is installed
runsc --version

# Test sandbox execution
podman run --runtime=runsc hello-world

# Check Podman runtime config
podman info | grep -A5 runtimes
```

### MLflow Not Recording

```bash
# Check MLflow server
curl http://localhost:5000/health

# Verify environment
echo $MLFLOW_TRACKING_URI

# Test logging
python -c "import mlflow; mlflow.start_run(); mlflow.log_param('test', 'value')"
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
podman ps | grep postgres

# Test connection
psql $DATABASE_URL -c "SELECT version()"

# Reset database
alembic downgrade base && alembic upgrade head
```

---

## Constitution Compliance Checklist

Before deploying, verify:

- [ ] **Safety First**: All automations go through HITL approval (`/api/v1/automations/{id}/approve`)
- [ ] **Isolation**: Data Scientist scripts run in gVisor sandbox (`podman run --runtime=runsc`)
- [ ] **Observability**: All agent actions traced to MLflow (check experiments)
- [ ] **State**: Checkpoints persisted to PostgreSQL (verify `checkpoints` table)

---

## Next Steps

1. Run `/speckit.tasks` to generate implementation tasks
2. Implement agents in priority order (P1 → P4)
3. Add contract tests for each API endpoint
4. Configure production deployment with systemd units
