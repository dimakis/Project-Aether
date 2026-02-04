# Quickstart: Project Aether

**Feature Branch**: `001-project-aether`  
**Date**: 2026-02-03

## Prerequisites

- **Home Assistant**: Running instance with long-lived access token
- **Python**: 3.11+
- **uv**: 0.4+ (fast Python package manager) - install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Podman**: 4.0+ with rootless mode configured
- **gVisor**: runsc runtime installed and configured
- **PostgreSQL**: 15+ (can use containerized)
- **OpenAI API Key**: For LLM access

## Quick Setup (5 minutes)

### 1. Clone and Install

```bash
cd /Users/dsaridak/projects/home_agent

# Create venv and install dependencies (uv does both in one step)
uv sync

# Or if starting fresh:
uv venv
uv pip install -e ".[dev]"

# Activate the virtual environment
source .venv/bin/activate
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

**Option 1: Open WebUI (Recommended)**

```bash
# Start Open WebUI (beautiful chat interface)
podman-compose -f infrastructure/podman/compose.yaml up -d open-webui

# Make sure Aether API is running
aether serve --reload

# Open in browser
open http://localhost:3000
```

Open WebUI provides:
- Streaming chat responses
- Code syntax highlighting
- Markdown rendering
- File downloads (for reports/dashboards)
- Conversation history

**Option 2: CLI**

```bash
# Start a conversation
aether chat

# Continue existing conversation
aether chat --continue <conversation-id>
```

**Option 3: API**

```bash
# OpenAI-compatible endpoint (works with any OpenAI client)
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "architect",
    "messages": [{"role": "user", "content": "I want to automate my morning routine"}],
    "stream": false
  }'

# Or the native conversation endpoint
curl -X POST http://localhost:8000/api/conversations \
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

### Dependency Management

```bash
# Add a production dependency
uv add langgraph

# Add a dev dependency
uv add --dev pytest-cov

# Update all dependencies
uv lock --upgrade

# Sync environment with lockfile (CI-safe, reproducible)
uv sync --frozen

# Show dependency tree
uv tree
```

### Run Tests

```bash
# Unit tests (fast, isolated)
uv run pytest tests/unit -v

# Integration tests (requires running services)
uv run pytest tests/integration -v

# E2E tests (full system)
uv run pytest tests/e2e -v

# All tests with coverage (Constitution: 80%+ required)
uv run pytest --cov=src --cov-report=html --cov-fail-under=80

# Run specific test file
uv run pytest tests/unit/test_dal_entities.py -v
```

### Lint and Format (Pre-commit)

```bash
# Format code
uv run ruff format src tests

# Lint and auto-fix
uv run ruff check src tests --fix

# Type check (strict mode)
uv run mypy src --strict

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

### View MLflow Traces

```bash
# Start MLflow UI (if using local SQLite)
make mlflow-local
# Or if using containerized MLflow:
open http://localhost:5002

# View experiments
mlflow experiments list

# View runs in an experiment
mlflow runs list --experiment-name aether
```

**Understanding Traces in the UI**:

1. **Experiment Runs**: Navigate to the "aether" experiment to see workflow runs (discovery, conversations)
2. **Traces Tab**: Click on a run, then "Traces" to see detailed span hierarchies
3. **Session Grouping**: Multi-turn conversations share the same session ID - filter by `mlflow.trace.session` to see all turns
4. **Span Details**: Click any span to see:
   - Inputs (user message, tool arguments)
   - Outputs (agent response, tool results)
   - Timing and status
5. **LLM Calls**: Autologged LangChain spans show full message content and token usage

**Querying Traces Programmatically**:

```python
import mlflow
mlflow.set_tracking_uri("sqlite:///mlflow.db")

# Search traces by session
traces = mlflow.search_traces(
    experiment_ids=[mlflow.get_experiment_by_name("aether").experiment_id],
    filter_string="metadata.`mlflow.trace.session` = 'your-session-id'",
)
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
