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
│  │  Science    │    │   Agent     │    │   Agent     │                     │
│  │   Team      │    │             │    │             │                     │
│  │ (Energy,    │    │             │    │             │                     │
│  │ Behavioral, │    │             │    │             │                     │
│  │ Diagnostic) │    │             │    │             │                     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                     │
│         │                  │                  │                             │
│         ▼                  ▼                  ▼                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │  Sandbox    │    │  HA Client  │    │  Automation │                     │
│  │  (gVisor)   │    │  (REST API) │    │   Deploy    │                     │
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
│  │  (REST API)     │                    │   (LLM)         │                 │
│  └─────────────────┘                    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agent Responsibilities

| Agent | Role | Tools |
|-------|------|-------|
| **Architect** | Unified chat entry point, routes to specialists, system diagnostics, config review | consult_data_science_team (auto-routes to Energy/Behavioral/Diagnostic Analysts), discover_entities, review_config, get_entity_history, get_ha_logs, check_ha_config, analyze_error_log, find_unavailable_entities, diagnose_entity, check_integration_health, validate_config, seek_approval, HA tools |
| **Data Science Team** | Energy analysis, pattern detection, insights, diagnostic analysis | Sandbox execution, history aggregation, diagnostic mode, dual synthesis (programmatic + LLM) |
| **Librarian** | Entity discovery, catalog maintenance | HA list_entities, domain_summary |
| **Developer** | Automation creation, YAML generation | deploy_automation (with HITL) |
| **Dashboard Designer** | Lovelace dashboard generation | generate_dashboard_yaml, validate_dashboard_yaml, list_dashboards |

### Diagnostic Collaboration Flow

The Architect and Data Science team collaborate to diagnose Home Assistant issues (missing data, sensor failures, integration problems):

```
User → Architect: "My car charger energy data disappeared"
         │
         ├─→ analyze_error_log()              # Structured log analysis with pattern matching
         ├─→ find_unavailable_entities()      # Broad entity health scan
         ├─→ diagnose_entity(entity_id)       # Deep-dive on specific entity
         ├─→ check_integration_health()       # Integration-level diagnosis
         ├─→ validate_config()                # Structured config check
         │
         ├─→ consult_data_science_team(       # Delegate to DS Team (auto-routes to Diagnostic Analyst)
         │     analysis_type="diagnostic",
         │     entity_ids=[...],
         │     diagnostic_context="...",       # Collected evidence
         │     instructions="...",             # What to investigate
         │   )
         │   └─→ DS Team's Diagnostic Analyst:
         │       ├─ Receives Architect's evidence
         │       ├─ Analyzes entity data for gaps/anomalies
         │       └─ Returns diagnostic findings
         │
         ├─→ (optional) Gather more data based on DS Team findings
         ├─→ (optional) Re-delegate with refined instructions
         │
         └─→ User: "Here's what I found: [diagnosis + recommendations]"
```

**Key design decisions:**
- No new workflow graph needed — uses Architect's existing tool-calling loop
- Architect gathers evidence first, then delegates with context (not blind delegation)
- DS Team's Diagnostic Analyst has a dedicated DIAGNOSTIC analysis type with its own prompt
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

### YAML Schema Validation (`src/schema/`)

Validates HA configuration YAML in two phases:

| Module | Purpose |
|--------|---------|
| `core.py` | `SchemaRegistry` maps schema names to Pydantic models and JSON schemas. `validate_yaml()` parses YAML and validates structure. `validate_yaml_semantic()` adds live-state checks. |
| `semantic.py` | `SemanticValidator` checks entity IDs, service calls, and area IDs against the live HA registry. |
| `ha/automation.py` | Schema for HA automations (triggers, conditions, actions). |
| `ha/script.py` | Schema for HA scripts (sequences). |
| `ha/scene.py` | Schema for HA scenes (entity states). |
| `ha/dashboard.py` | Schema for Lovelace dashboards (views, cards). |

Used during: automation design, Smart Config Review, dashboard generation.

### Smart Config Review Workflow

The Architect's `review_config` tool triggers a dedicated LangGraph workflow that reviews existing HA configurations:

```
review_config(target, focus)
         │
         ▼
┌─────────────────────┐
│ resolve_targets_node │  Resolve "all_automations" → concrete entity IDs
└──────────┬──────────┘  or accept specific entity_id
           │
           ▼
┌─────────────────────┐
│ fetch_configs_node   │  Fetch current YAML from HA REST API
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ gather_context_node  │  Collect entities, registry, configs for DS team
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ DS Team consultation │  Analyze config quality, suggest improvements
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────┐
│ create_review_proposals  │  Create AutomationProposal entries with
│         _node            │  original_yaml for diff view
└──────────────────────────┘
```

Proposals from config review follow the same approval/deploy/rollback flow as new automations.

### MLflow 3.x Trace Evaluation

Custom scorers evaluate agent trace quality:

| Scorer | What It Checks |
|--------|----------------|
| `response_latency` | Flags traces exceeding 30-second threshold |
| `tool_usage_safety` | Ensures HA mutation tools (deploy, service calls) have approval ancestor spans |
| `agent_delegation_depth` | Detects runaway delegation chains (max depth 6) |
| `tool_call_count` | Counts tool invocations per trace |

Run evaluations via:
- **API**: `POST /api/v1/evaluations/run` — on-demand evaluation
- **CLI**: `aether evaluate --traces 50` — evaluate recent traces
- **Scheduler**: Nightly evaluation job via APScheduler

### Agent Configuration (`src/agents/config_cache.py`)

Runtime agent configuration is stored in PostgreSQL and cached in-memory with 60-second TTL:

- **`AgentRuntimeConfig`** — Resolved config (model, temperature, fallback model, tools, prompt template)
- **`get_agent_runtime_config(agent_name)`** — Returns cached config; falls back to DB on cache miss
- **`invalidate_agent_config(agent_name)`** — Invalidates cache on config/prompt promotion or rollback

API: Full CRUD at `/api/v1/agents/{name}/config/versions` with version promotion, rollback, and cloning.

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

All endpoints require authentication via JWT token (cookie or Bearer header), API key (`X-API-Key` header or `api_key` query param), or passkey. Health, ready, status, and login endpoints are exempt.

### OpenAI-Compatible

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/models` | GET | List available agents as "models" |
| `/api/v1/chat/completions` | POST | Chat with agents (supports streaming) |
| `/api/v1/feedback` | POST | Submit response feedback |

### Native API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Liveness probe |
| `/api/v1/ready` | GET | Readiness probe (Kubernetes) |
| `/api/v1/status` | GET | System status with component health |
| `/api/v1/metrics` | GET | Operational metrics (requests, latency, errors) |
| `/api/v1/conversations` | GET/POST | List/create conversations |
| `/api/v1/conversations/{id}` | GET/DELETE | Get/delete conversation |
| `/api/v1/conversations/{id}/messages` | POST | Send message |
| `/api/v1/conversations/{id}/stream` | WS | WebSocket streaming |
| `/api/v1/entities` | GET | List entities |
| `/api/v1/entities/{id}` | GET | Get entity details |
| `/api/v1/entities/query` | POST | Natural language query |
| `/api/v1/entities/sync` | POST | Trigger entity sync from HA |
| `/api/v1/entities/domains/summary` | GET | Entity count per domain |
| `/api/v1/devices` | GET | List devices |
| `/api/v1/areas` | GET | List areas |
| `/api/v1/insights` | GET/POST | List/create insights |
| `/api/v1/insights/pending` | GET | Pending insights |
| `/api/v1/insights/summary` | GET | Insights summary |
| `/api/v1/insights/{id}/review` | POST | Mark reviewed |
| `/api/v1/insights/{id}/action` | POST | Mark actioned |
| `/api/v1/insights/{id}/dismiss` | POST | Dismiss insight |
| `/api/v1/insights/analyze` | POST | Trigger analysis |
| `/api/v1/insight-schedules` | GET/POST | Manage insight schedules |
| `/api/v1/insight-schedules/{id}` | GET/PUT/DELETE | CRUD schedule |
| `/api/v1/insight-schedules/{id}/run` | POST | Manual trigger |
| `/api/v1/proposals` | GET/POST | List/create automation proposals |
| `/api/v1/proposals/pending` | GET | Pending proposals |
| `/api/v1/proposals/{id}/approve` | POST | Approve automation (HITL) |
| `/api/v1/proposals/{id}/reject` | POST | Reject proposal |
| `/api/v1/proposals/{id}/deploy` | POST | Deploy to Home Assistant |
| `/api/v1/proposals/{id}/rollback` | POST | Rollback deployment |
| `/api/v1/optimize` | POST | Run optimization analysis |
| `/api/v1/optimize/suggestions/list` | GET | List automation suggestions |
| `/api/v1/registry/sync` | POST | Sync automations/scripts/scenes from HA |
| `/api/v1/registry/automations` | GET | List HA automations |
| `/api/v1/registry/automations/{id}/config` | GET | Get automation YAML |
| `/api/v1/registry/scripts` | GET | List HA scripts |
| `/api/v1/registry/scenes` | GET | List HA scenes |
| `/api/v1/registry/services` | GET | List HA services |
| `/api/v1/registry/services/call` | POST | Call an HA service |
| `/api/v1/registry/summary` | GET | Registry summary |
| `/api/v1/diagnostics/ha-health` | GET | HA health (unavailable entities, integrations) |
| `/api/v1/diagnostics/error-log` | GET | Parsed HA error log with pattern matching |
| `/api/v1/diagnostics/config-check` | GET | HA config validation |
| `/api/v1/diagnostics/traces/recent` | GET | Recent agent traces from MLflow |
| `/api/v1/evaluations/summary` | GET | Latest trace evaluation summary |
| `/api/v1/evaluations/run` | POST | Trigger on-demand trace evaluation |
| `/api/v1/evaluations/scorers` | GET | List available scorers |
| `/api/v1/agents` | GET | List agents with active config |
| `/api/v1/agents/{name}` | GET/PATCH | Get/update agent |
| `/api/v1/agents/{name}/config/versions` | GET/POST | Config versioning |
| `/api/v1/agents/{name}/prompt/versions` | GET/POST | Prompt versioning |
| `/api/v1/agents/seed` | POST | Seed default agents |
| `/api/v1/activity/stream` | GET | SSE real-time agent activity |
| `/api/v1/flow-grades` | POST | Submit flow grade |
| `/api/v1/flow-grades/{conversation_id}` | GET | Get conversation grades |
| `/api/v1/zones` | GET/POST | List/create HA zones |
| `/api/v1/zones/{id}` | PATCH/DELETE | Update/delete zone |
| `/api/v1/zones/{id}/test` | POST | Test zone connectivity |
| `/api/v1/models/ratings` | GET/POST | Model ratings |
| `/api/v1/models/summary` | GET | Model summaries |
| `/api/v1/models/performance` | GET | Model performance metrics |
| `/api/v1/webhooks/ha` | POST | Receive HA webhook events |
| `/api/v1/traces/{trace_id}/spans` | GET | Get trace span tree |
| `/api/v1/workflows/presets` | GET | Workflow presets for chat UI |
| `/api/v1/usage/summary` | GET | LLM usage summary |
| `/api/v1/usage/daily` | GET | Daily usage breakdown |
| `/api/v1/usage/models` | GET | Per-model usage |
| `/api/v1/usage/conversation/{id}` | GET | Conversation cost |
| `/api/v1/auth/setup-status` | GET | Setup status (public) |
| `/api/v1/auth/setup` | POST | First-time setup (public) |
| `/api/v1/auth/login` | POST | Password login |
| `/api/v1/auth/login/ha-token` | POST | HA token login |
| `/api/v1/auth/google/url` | GET | Google OAuth URL |
| `/api/v1/auth/passkey/*` | POST | WebAuthn passkey auth |

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
                 ┌─────────────┐      ┌──────────────────────┐      ┌─────────────┐
                 │ HA Tools    │      │consult_data_science_ │     │discover_    │
                 │(direct HA)  │      │team (auto-routes)    │      │entities     │
                 └─────────────┘      └──────┬───────────────┘      └──────┬──────┘
                                             │                              │
                                             ▼                              ▼
                                      ┌──────────────────────┐      ┌─────────────┐
                                      │  Data Science Team   │      │  Librarian  │
                                      │ (Energy, Behavioral, │      │   Agent     │
                                      │  Diagnostic Analysts)│      │             │
                                      └──────────────────────┘      └─────────────┘
```

### Energy Analysis Flow

```
"Analyze my energy usage"
         │
         ▼
┌─────────────────┐
│    Architect    │
│  (routes via    │
│consult_data_    │
│science_team,    │
│auto-routes to   │
│Energy Analyst)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ DS Team's       │───▶│ collect_energy  │
│ Energy Analyst  │    │    _data        │
└────────┬────────┘    └────────┬────────┘
         │                      │
         │                      ▼
         │             ┌─────────────────┐
         │             │  HA History     │
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
│  HA Client → HA │
└─────────────────┘
```

### Sandbox Isolation

DS Team scripts run in gVisor with:
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
│   ├── consult_data_science_team (tool, auto-routes to Energy Analyst)
│   │   └── DataScientistWorkflow.run_analysis (legacy path for scheduled insights)
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
Request → CORS → Security Headers → Correlation ID → Rate Limiting → Auth → Route Handler
                                                                                │
Response ← Tracing Middleware ← Exception Handler ← ────────────────────────────
```

| Layer | Description |
|-------|-------------|
| **Security Headers** | HSTS, CSP, Permissions-Policy headers added in production/staging |
| **Correlation ID** | UUID generated per request, propagated through context vars to all logs and error responses |
| **Auth** | JWT token (cookie/Bearer), WebAuthn passkey, API key (`X-API-Key` header or `api_key` param), or HA token; bypasses for health/ready/status/login endpoints |
| **Rate Limiting** | SlowAPI-based limits on LLM-backed and resource-intensive endpoints |
| **Request Tracing** | Logs method, path, status, duration, correlation ID for every request |
| **Metrics Collection** | In-memory counters for request rates, latency percentiles, error rates, active connections |
| **Exception Hierarchy** | `AetherError` → `AgentError`, `DALError`, `HAClientError`, `SandboxError`, `LLMError`, `ConfigurationError`, `ValidationError` -- all include correlation IDs |

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

---

## Target Architecture (Jarvis Pivot)

> **Status**: Planned (Features 29/30). See `docs/architecture-review.md` for the full readiness assessment.

The current Architect-centric architecture will evolve into a domain-agnostic Orchestrator pattern. The Architect becomes one of several domain agents, and a new Orchestrator handles intent classification and routing.

### Target System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interfaces                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │   CLI       │    │  REST API   │    │      Chat UI (React)            │  │
│  │  (aether)   │    │  (FastAPI)  │    │  (Agent Picker + Model Picker)  │  │
│  └──────┬──────┘    └──────┬──────┘    └───────────────┬─────────────────┘  │
│         │                  │                           │                     │
│         └──────────────────┼───────────────────────────┘                     │
│                            │                                                 │
│                            ▼                                                 │
│              ┌─────────────────────────────┐                                │
│              │   /v1/chat/completions      │  (OpenAI-compatible)           │
│              │   agent: auto | <name>      │  (agent field for routing)     │
│              └──────────────┬──────────────┘                                │
└─────────────────────────────┼───────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                      Agent Layer                                             │
├─────────────────────────────┼───────────────────────────────────────────────┤
│                             ▼                                                │
│              ┌─────────────────────────────┐                                │
│              │    Orchestrator (Jarvis)    │  ◄── Intent Classification     │
│              │   (Routes by intent or      │      + Personality             │
│              │    explicit agent selection) │                                │
│              └──────────────┬──────────────┘                                │
│                             │                                                │
│     ┌───────────┬───────────┼───────────┬───────────┐                       │
│     │           │           │           │           │                       │
│     ▼           ▼           ▼           ▼           ▼                       │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│ │  Home   │ │Knowledge│ │Research │ │  Food   │ │Dynamic  │              │
│ │  Agent  │ │  Agent  │ │  Agent  │ │  Agent  │ │ Agents  │              │
│ │(Archit.)│ │(no tools│ │(web     │ │(recipes │ │(user-   │              │
│ │         │ │ pure LLM│ │ search) │ │+ HA     │ │ created)│              │
│ │         │ │         │ │         │ │ deleg.) │ │         │              │
│ └────┬────┘ └─────────┘ └─────────┘ └────┬────┘ └─────────┘              │
│      │                                    │                                │
│      ▼                                    ▼                                │
│ ┌──────────────┐                    ┌──────────┐                           │
│ │ DS Team      │                    │ Cross-   │                           │
│ │ Librarian    │                    │ Domain   │                           │
│ │ Developer    │                    │ Delegat. │                           │
│ └──────────────┘                    └──────────┘                           │
│                                                                             │
│ ┌──────────────────────────────────────────────────────────────┐           │
│ │  Shared Infrastructure                                       │           │
│ │  ├─ MutatingToolRegistry (centralized HITL enforcement)     │           │
│ │  ├─ AgentRegistry (name → class, DB-driven config)          │           │
│ │  ├─ ToolRegistry (per-agent tool resolution)                │           │
│ │  └─ WorkflowCompiler (dynamic graph composition)            │           │
│ └──────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Changes from Current Architecture

| Aspect | Current | Target |
|--------|---------|--------|
| Entry point | Architect Agent (fixed) | Orchestrator with intent routing |
| Agent selection | Implicit (always Architect) | Explicit (`agent` field) or auto (Orchestrator) |
| Domain scope | Home Assistant only | Multi-domain (HA, Knowledge, Research, Food, ...) |
| HITL enforcement | Per-agent (`_READ_ONLY_TOOLS`) | Centralized `MutatingToolRegistry` |
| Tool assignment | Hardcoded (`get_architect_tools()`) | DB-driven via `tools_enabled` + agent config |
| Agent configuration | Code-defined | DB-driven (Feature 23 wired to runtime) |
| Workflows | Static (Python-defined) | Static + dynamic (declarative composition) |
| Voice support | Not supported | HA Voice Pipeline (Wyoming + Whisper + Piper) |
| Personality | None | Consistent "Jarvis" personality, channel-aware |

### Implementation Phases

1. **Phase 0**: Pre-pivot refactoring (centralize HITL, wire Feature 23, split workflows.py)
2. **Phase 1**: Orchestrator + intent routing + KnowledgeAgent + `agent` field + UI picker
3. **Phase 2**: ResearchAgent + FoodAgent + cross-domain delegation + voice pipeline
4. **Phase 3**: Dynamic workflow composition + dynamic agent creation + persistence

See `docs/architecture-review.md` for the full assessment, gap analysis, and risk register.
