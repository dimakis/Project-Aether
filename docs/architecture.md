# Project Aether - Architecture

## Overview

Project Aether is an agentic home automation system that provides conversational interaction with Home Assistant through specialized AI agents.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interfaces                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │   CLI       │    │  REST API   │    │      Chat UI (React)            │  │
│  │  (aether)   │    │  (FastAPI)  │    │  (Chat UI with streaming)       │  │
│  └──────┬──────┘    └──────┬──────┘    └───────────────┬─────────────────┘  │
│         │                  │                           │                     │
│         └──────────────────┼───────────────────────────┘                     │
│                            │                                                 │
│                            ▼                                                 │
│              ┌─────────────────────────────┐                                │
│              │   /v1/chat/completions      │  (OpenAI-compatible)           │
│              │   /api/conversations        │  (Native API)                  │
│              └──────────────┬──────────────┘                                │
└─────────────────────────────┼───────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                      Agent Layer                                             │
├─────────────────────────────┼───────────────────────────────────────────────┤
│                             ▼                                                │
│              ┌─────────────────────────────┐                                │
│              │      Architect Agent        │  ◄── Unified Entry Point       │
│              │   (Smart Router + Chat)     │                                │
│              └──────────────┬──────────────┘                                │
│                             │                                                │
│         ┌───────────────────┼───────────────────┐                           │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   Data      │    │  Librarian  │    │  Developer  │                     │
│  │  Scientist  │    │   Agent     │    │   Agent     │                     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                     │
│         │                  │                  │                             │
│         ▼                  ▼                  ▼                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │  Sandbox    │    │    MCP      │    │  Automation │                     │
│  │  (gVisor)   │    │   Client    │    │   Deploy    │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                      Data Layer                                              │
├─────────────────────────────┼───────────────────────────────────────────────┤
│         ┌───────────────────┼───────────────────┐                           │
│         │                   │                   │                           │
│         ▼                   ▼                                                   │
│  ┌─────────────┐    ┌─────────────┐                                           │
│  │ PostgreSQL  │    │   MLflow    │                                           │
│  │  (State)    │    │  (Traces)   │                                           │
│  └─────────────┘    └─────────────┘                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                    External Services                                         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│         ┌───────────────────┴───────────────────┐                           │
│         ▼                                       ▼                           │
│  ┌─────────────────┐                    ┌─────────────────┐                 │
│  │ Home Assistant  │                    │  LLM Provider   │                 │
│  │    (MCP)        │                    │   (LLM)         │                 │
│  └─────────────────┘                    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agent Responsibilities

| Agent | Role | Tools |
|-------|------|-------|
| **Architect** | Unified chat entry point, routes to specialists, system diagnostics | analyze_energy, discover_entities, get_entity_history, diagnose_issue, get_ha_logs, check_ha_config, analyze_error_log, find_unavailable_entities, diagnose_entity, check_integration_health, validate_config, seek_approval, HA tools |
| **Data Scientist** | Energy analysis, pattern detection, insights, diagnostic analysis | Sandbox execution, history aggregation, diagnostic mode |
| **Librarian** | Entity discovery, catalog maintenance | MCP list_entities, domain_summary |
| **Developer** | Automation creation, YAML generation | deploy_automation (with HITL) |

### Diagnostic Collaboration Flow

The Architect and Data Scientist collaborate to diagnose Home Assistant issues (missing data, sensor failures, integration problems):

```
User → Architect: "My car charger energy data disappeared"
         │
         ├─→ analyze_error_log()              # Structured log analysis with pattern matching
         ├─→ find_unavailable_entities()      # Broad entity health scan
         ├─→ diagnose_entity(entity_id)       # Deep-dive on specific entity
         ├─→ check_integration_health()       # Integration-level diagnosis
         ├─→ validate_config()                # Structured config check
         │
         ├─→ diagnose_issue(                  # Delegate to Data Scientist
         │     entity_ids=[...],
         │     diagnostic_context="...",       # Collected evidence
         │     instructions="...",             # What to investigate
         │   )
         │   └─→ Data Scientist:
         │       ├─ Receives Architect's evidence
         │       ├─ Analyzes entity data for gaps/anomalies
         │       └─ Returns diagnostic findings
         │
         ├─→ (optional) Gather more data based on DS findings
         ├─→ (optional) Re-delegate with refined instructions
         │
         └─→ User: "Here's what I found: [diagnosis + recommendations]"
```

**Key design decisions:**
- No new workflow graph needed — uses Architect's existing tool-calling loop
- Architect gathers evidence first, then delegates with context (not blind delegation)
- Data Scientist has a dedicated DIAGNOSTIC analysis type with its own prompt
- Architect can iterate: gather more data → re-delegate → synthesize

### Diagnostics Module (`src/diagnostics/`)

Provides structured analysis of HA system health, used by agent diagnostic tools:

| Module | Purpose |
|--------|---------|
| `log_parser.py` | Parse raw HA error log into `ErrorLogEntry` objects, categorize by integration, detect recurring patterns |
| `error_patterns.py` | Match entries against `KNOWN_ERROR_PATTERNS` (connection, auth, device, config, setup, database) with fix suggestions |
| `entity_health.py` | Find unavailable/stale entities, correlate by integration to detect common root causes |
| `integration_health.py` | Check all integration config entry health, find unhealthy integrations, deep-dive diagnosis |
| `config_validator.py` | Structured config check with parsed errors/warnings, local automation YAML validation |

## Deployment Modes

### Development Mode

```
┌─────────────────────────────────────────────────────────────────┐
│                     Host Machine                                 │
│  ┌─────────────┐    ┌─────────────┐                             │
│  │ aether CLI  │───▶│ FastAPI     │  (hot-reload enabled)       │
│  └─────────────┘    │ :8000       │                             │
│                     └──────┬──────┘                             │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│               Podman Containers                                  │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │ PostgreSQL  │  │   MLflow    │                              │
│  │   :5432     │  │   :5002     │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘

Command: make run
```

### Development + UI Mode

```
┌─────────────────────────────────────────────────────────────────┐
│                     Host Machine                                 │
│  ┌─────────────┐    ┌─────────────┐                             │
│  │ aether CLI  │───▶│ FastAPI     │  (hot-reload enabled)       │
│  └─────────────┘    │ :8000       │◀─────────┐                  │
└────────────────────────────┼─────────────────┼──────────────────┘
                             │                 │
┌────────────────────────────┼─────────────────┼──────────────────┐
│               Podman Containers              │                   │
│  ┌─────────────┐  ┌─────────────┐  ┌────────┴────┐              │
│  │ PostgreSQL  │  │   MLflow    │  │ Chat UI     │              │
│  │   :5432     │  │   :5002     │  │ (React)      │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘

Command: make run-ui
```

### Production Mode (Fully Containerized)

```
┌─────────────────────────────────────────────────────────────────┐
│                   Podman Containers                              │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Chat UI (React) :3000                      │    │
│  └────────────────────────────┬────────────────────────────┘    │
│                               │                                  │
│  ┌────────────────────────────▼────────────────────────────┐    │
│  │                   Aether API :8000                       │    │
│  └────────────────────────────┬────────────────────────────┘    │
│                               │                                  │
│  ┌─────────────┐  ┌───────────┴─┐                              │
│  │ PostgreSQL  │  │   MLflow    │                              │
│  │   :5432     │  │   :5002     │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘

Command: make run-prod
```

### Stop All Services

```bash
make down
```

### Kubernetes Migration Path

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Ingress Controller (nginx/traefik)                       │    │
│  │   ├─ /         → chat-ui-service                         │    │
│  │   ├─ /api      → aether-api-service                      │    │
│  │   └─ /mlflow   → mlflow-service                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  chat-ui    │  │ aether-api  │  │  mlflow     │              │
│  │ Deployment  │  │ Deployment  │  │ Deployment  │              │
│  │ (replicas:2)│  │ (replicas:3)│  │ (replicas:1)│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ StatefulSets                                             │    │
│  │  └─ PostgreSQL (1 replica + PVC)                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Optional: AI Gateway (Kong + AI Plugin)                  │    │
│  │   ├─ Rate limiting                                       │    │
│  │   ├─ Token counting                                      │    │
│  │   └─ Request/response logging                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

Migration:
  1. kompose convert -f infrastructure/podman/compose.yaml
  2. Adjust resource limits, replicas, PVCs
  3. Add Ingress rules
  4. Configure secrets via K8s Secrets/Vault
```

## API Endpoints

All endpoints require API key authentication via `X-API-Key` header (except health/status).

### OpenAI-Compatible

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/models` | GET | List available agents as "models" |
| `/api/v1/chat/completions` | POST | Chat with agents (supports streaming) |
| `/api/v1/feedback` | POST | Submit response feedback |

### Native API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/status` | GET | System status with component health |
| `/api/v1/metrics` | GET | Operational metrics (requests, latency, errors) |
| `/api/v1/conversations` | POST | Start new conversation |
| `/api/v1/conversations/{id}/messages` | POST | Continue conversation |
| `/api/v1/entities` | GET | List entities |
| `/api/v1/entities/query` | POST | Natural language query |
| `/api/v1/entities/sync` | POST | Trigger entity sync from HA |
| `/api/v1/insights` | GET/POST | Manage insights |
| `/api/v1/insights/analyze` | POST | Trigger analysis |
| `/api/v1/insight-schedules` | GET/POST | Manage insight schedules |
| `/api/v1/proposals` | GET/POST | List/create automation proposals |
| `/api/v1/proposals/{id}/approve` | POST | Approve automation (HITL) |
| `/api/v1/proposals/{id}/deploy` | POST | Deploy to Home Assistant |
| `/api/v1/proposals/{id}/rollback` | POST | Rollback deployment |
| `/api/v1/optimize` | POST | Run optimization analysis |
| `/api/v1/registry/automations` | GET | List HA automations |
| `/api/v1/registry/sync` | POST | Sync automations/scripts/scenes from HA |
| `/api/v1/registry/services` | GET | List HA services |
| `/api/v1/registry/services/call` | POST | Call an HA service |
| `/api/v1/webhooks/ha` | POST | Receive HA webhook events |
| `/api/v1/traces/{trace_id}/spans` | GET | Get trace span tree |

## Data Flow

### Chat Request Flow

```
User Message
     │
     ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Chat UI     │───▶│  /v1/chat   │───▶│  Architect  │
│ (React)     │    │ /completions│    │   Agent     │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
                        ┌────────────────────┼────────────────────┐
                        │                    │                    │
                        ▼                    ▼                    ▼
                 ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                 │ HA Tools    │      │analyze_energy│     │discover_    │
                 │(direct MCP) │      │   (tool)    │      │entities     │
                 └─────────────┘      └──────┬──────┘      └──────┬──────┘
                                             │                    │
                                             ▼                    ▼
                                      ┌─────────────┐      ┌─────────────┐
                                      │Data Scientist│     │  Librarian  │
                                      │   Agent     │      │   Agent     │
                                      └─────────────┘      └─────────────┘
```

### Energy Analysis Flow

```
"Analyze my energy usage"
         │
         ▼
┌─────────────────┐
│    Architect    │
│  (routes via    │
│ analyze_energy) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ Data Scientist  │───▶│ collect_energy  │
│    Agent        │    │    _data        │
└────────┬────────┘    └────────┬────────┘
         │                      │
         │                      ▼
         │             ┌─────────────────┐
         │             │  MCP History    │
         │             │  (24-168 hrs)   │
         │             └────────┬────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ generate_script │◀───│  Energy Data    │
│    (LLM)        │    │  (aggregated)   │
└────────┬────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ execute_sandbox │───▶│  gVisor/Podman  │
│                 │    │  (isolated)     │
└────────┬────────┘    └────────┬────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│extract_insights │◀───│  Script Output  │
│    (LLM)        │    │  (JSON/plots)   │
└────────┬────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Conversational  │
│    Summary      │
│ + Insights DB   │
└─────────────────┘
```

## Security Model

### HITL (Human-in-the-Loop)

All mutating Home Assistant actions require explicit approval:

```
User: "Turn on the living room lights"
         │
         ▼
┌─────────────────┐
│    Architect    │
│  (detects       │
│ control_entity) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WAITING_APPROVAL│
│                 │
│ "I can perform: │
│ - control_entity│
│   (light.living │
│    room, on)    │
│                 │
│ Reply 'approve' │
│ to proceed"     │
└────────┬────────┘
         │
    User: "approve"
         │
         ▼
┌─────────────────┐
│  Execute via    │
│  MCP → HA       │
└─────────────────┘
```

### Sandbox Isolation

Data Scientist scripts run in gVisor with:
- No network access (default)
- Read-only filesystem (except /tmp)
- Memory/CPU limits
- Timeout enforcement

## Observability

### MLflow Tracing

All agent operations are traced:

```
Session: conv-12345
├── ArchitectAgent.invoke
│   ├── inputs: {"message": "Analyze energy"}
│   ├── _build_messages
│   ├── llm.ainvoke (autologged)
│   ├── analyze_energy (tool)
│   │   └── DataScientistWorkflow.run_analysis
│   │       ├── collect_energy_data
│   │       ├── generate_script
│   │       ├── execute_sandbox
│   │       └── extract_insights
│   └── outputs: {"response": "I analyzed...", "insights": [...]}
```

View traces: `make mlflow` → http://localhost:5002

## Middleware & Cross-Cutting Concerns

### Request Pipeline

```
Request → CORS → Correlation ID → Rate Limiting → API Key Auth → Route Handler
                                                                        │
Response ← Tracing Middleware ← Exception Handler ← ─────────────────────
```

| Layer | Description |
|-------|-------------|
| **Correlation ID** | UUID generated per request, propagated through context vars to all logs and error responses |
| **API Key Auth** | Validates `X-API-Key` header or `api_key` query param; bypasses for health endpoints |
| **Rate Limiting** | SlowAPI-based limits on LLM-backed and resource-intensive endpoints |
| **Request Tracing** | Logs method, path, status, duration, correlation ID for every request |
| **Metrics Collection** | In-memory counters for request rates, latency percentiles, error rates, active connections |
| **Exception Hierarchy** | `AetherError` → `AgentError`, `DALError`, `MCPError`, `SandboxError`, `LLMError`, `ConfigurationError`, `ValidationError` — all include correlation IDs |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `MLFLOW_TRACKING_URI` | `http://localhost:5002` | MLflow server URL |
| `HA_URL` | - | Home Assistant URL |
| `HA_TOKEN` | - | Home Assistant long-lived access token |
| `LLM_PROVIDER` | `openrouter` | LLM provider (openrouter, openai, google, ollama, together, groq) |
| `LLM_API_KEY` | - | LLM API key |
| `LLM_MODEL` | `anthropic/claude-sonnet-4` | Default LLM model |
| `LLM_FALLBACK_PROVIDER` | - | Fallback LLM provider |
| `LLM_FALLBACK_MODEL` | - | Fallback LLM model |
| `API_KEY` | - | API authentication key (empty = auth disabled) |
| `ENVIRONMENT` | `development` | Environment (development, staging, production, testing) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `API_PORT` | `8000` | API server port |

### Deployment Commands

| Command | Description |
|---------|-------------|
| `make run` | Development mode (API on host with hot-reload) |
| `make run-ui` | Development + Chat UI (React) interface |
| `make run-prod` | Production mode (everything containerized) |
| `make down` | Stop all services |

### Compose Profiles (advanced)

| Profile | Services Added | Use Case |
|---------|----------------|----------|
| (none) | postgres, mlflow | Infrastructure only |
| `ui` | + chat-ui | Add React UI |
| `full` | + aether-app | Containerized API |
| `full` + `ui` | All services | Production stack |
