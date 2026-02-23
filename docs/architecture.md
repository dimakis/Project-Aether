# Architecture

System design, agent roles, data flows, observability, and security model for Project Aether.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interfaces                                │
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
│     ┌───────────┬───────────┼───────────┬───────────┐                       │
│     │           │           │           │           │                       │
│     ▼           ▼           ▼           ▼           ▼                       │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐              │
│ │  Data   │ │Librarian│ │Developer│ │Dashboard│ │ Schema   │              │
│ │ Science │ │  Agent  │ │  Agent  │ │Designer │ │Validator │              │
│ │  Team   │ │         │ │         │ │         │ │          │              │
│ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └─────┬────┘              │
│      │           │           │           │            │                     │
│      ▼           ▼           ▼           ▼            ▼                     │
│ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐              │
│ │ Sandbox │ │HA Client│ │Automation│ │Lovelace│ │ YAML     │              │
│ │ (gVisor)│ │  (MCP)  │ │  Deploy  │ │ YAML   │ │ Schemas  │              │
│ └─────────┘ └─────────┘ └──────────┘ └────────┘ └──────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                      Data Layer                                              │
├─────────────────────────────┼───────────────────────────────────────────────┤
│         ┌───────────────────┼───────────────────┐                           │
│         │                   │                   │                           │
│         ▼                   ▼                                               │
│  ┌─────────────┐    ┌─────────────┐                                        │
│  │ PostgreSQL  │    │   MLflow    │                                        │
│  │  (State)    │    │  (Traces)   │                                        │
│  └─────────────┘    └─────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                    External Services                                         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│         ┌───────────────────┴───────────────────┐                           │
│         ▼                                       ▼                           │
│  ┌─────────────────┐                    ┌─────────────────┐                 │
│  │ Home Assistant  │                    │  LLM Provider   │                 │
│  │   (via MCP)     │                    │   (LLM)         │                 │
│  └─────────────────┘                    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Responsibilities

| Agent | Role | Tools |
|-------|------|-------|
| **Architect** | Unified chat entry point, routes to specialists, system diagnostics, config review | 16 tools: `consult_data_science_team`, `consult_dashboard_designer`, `discover_entities`, `review_config`, `seek_approval`, `create_insight_schedule`, `get_entity_state`, `list_entities_by_domain`, `search_entities`, `get_domain_summary`, `list_automations`, `get_automation_config`, `get_script_config`, `render_template`, `get_ha_logs`, `check_ha_config` |
| **Data Science Team** | Energy analysis, behavioral patterns, diagnostics, insights | Sandbox execution, history aggregation, diagnostic mode, dual synthesis (programmatic + LLM) |
| **Librarian** | Entity discovery, catalog maintenance | HA `list_entities`, `domain_summary` |
| **Developer** | Automation deployment (HITL) | `deploy_automation` (with approval) |
| **Dashboard Designer** | Lovelace dashboard generation | `generate_dashboard_yaml`, `validate_dashboard_yaml`, `list_dashboards` |

### Architect Tool Categories

**Delegation tools:**
- `consult_data_science_team` — DS team (auto-routes to Energy, Behavioral, or Diagnostic Analyst)
- `consult_dashboard_designer` — Dashboard Designer agent
- `discover_entities` — Librarian agent
- `seek_approval` — HITL approval workflow
- `review_config` — config review workflow (DS Team + Architect)
- `create_insight_schedule` — scheduled/event-driven analysis

**HA query tools (DB-backed):**
- `get_entity_state`, `list_entities_by_domain`, `search_entities`, `get_domain_summary`
- `list_automations`, `get_automation_config`, `get_script_config`

**HA query tools (live):**
- `render_template`, `get_ha_logs`, `check_ha_config`

All 16 tools are read-only; mutating actions route through `seek_approval` for HITL enforcement.

---

## Diagnostic Collaboration Flow

The Architect and Data Science team collaborate to diagnose HA issues (missing data, sensor failures, integration problems):

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

---

## DS Team Collaboration

The Architect delegates to the Data Science team via `consult_data_science_team`. The team has two execution paths:

### Specialist-Based Team (Primary)

Used by `consult_data_science_team`:
- **Keyword routing** (`SPECIALIST_TRIGGERS`) selects specialists based on query content
- **Strategies**: `parallel` (default — specialists run concurrently) or `teamwork` (sequential with cross-consultation)
- Shared `TeamAnalysis` collects findings from all specialists
- `ProgrammaticSynthesizer` merges findings into consensus, conflicts, and recommendations
- Optional discussion round when conflicts are detected

### Monolithic DataScientistAgent (Scheduled Analysis)

Used by scheduled insights and CLI analysis commands:
- Single agent handles energy and behavioral analysis
- Pipeline: collect data → generate script → sandbox execution → extract insights → persist
- Can produce `AutomationSuggestion` for high-confidence findings

### Specialist Roles

| Specialist | Focus Areas |
|-----------|-------------|
| **Energy Analyst** | Energy sensors, cost analysis, usage patterns, anomaly detection |
| **Behavioral Analyst** | Button/switch usage, automation effectiveness, gaps, correlations, device health, script/scene usage |
| **Diagnostic Analyst** | Unavailable entities, unhealthy integrations, config checks, error logs, sensor drift |

### Synthesis

`synthesis.py` provides two synthesizers:
- **ProgrammaticSynthesizer** (default) — rule-based merging of specialist findings
- **LLMSynthesizer** — LLM-based, used for conflict resolution when programmatic synthesis detects disagreements

---

## YAML Schema Validation (`src/schema/`)

Validates HA configuration YAML in two phases:

| Module | Purpose |
|--------|---------|
| `core.py` | `SchemaRegistry` maps schema names to Pydantic models and JSON schemas. `validate_yaml()` parses YAML and validates structure. `validate_yaml_semantic()` adds live-state checks. |
| `semantic.py` | `SemanticValidator` checks entity IDs, service calls, and area IDs against the live HA registry. |
| `ha/automation.py` | Schema for HA automations (triggers, conditions, actions). |
| `ha/script.py` | Schema for HA scripts (sequences). |
| `ha/scene.py` | Schema for HA scenes (entity states). |
| `ha/dashboard.py` | Schema for Lovelace dashboards (views, cards). |
| `ha/registry_cache.py` | Cached registry data for semantic validation. |

Used during: automation design, Smart Config Review, dashboard generation.

---

## Smart Config Review Workflow

The Architect's `review_config` tool triggers a dedicated LangGraph workflow:

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

---

## MLflow Trace Evaluation

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

---

## Agent Configuration (`src/agents/config_cache.py`)

Runtime agent configuration is stored in PostgreSQL and cached in-memory with 60-second TTL:

- **`AgentRuntimeConfig`** — Resolved config (model, temperature, fallback model, tools, prompt template)
- **`get_agent_runtime_config(agent_name)`** — Returns cached config; falls back to DB on cache miss
- **`invalidate_agent_config(agent_name)`** — Invalidates cache on config/prompt promotion or rollback
- **`is_agent_enabled(agent_name)`** — Checks agent status (Dashboard Designer can be disabled)

API: Full CRUD at `/api/v1/agents/{name}/config/versions` with version promotion, rollback, and cloning.

### Model Context Propagation

When a user selects a model in the UI, that choice propagates through all agent delegations via `model_context.py`:

```
Resolution order:  UI selection  >  DB-backed active config  >  per-agent .env setting  >  global default
```

---

## LangGraph Workflows

All workflows are defined as LangGraph graphs in `src/graph/workflows/`:

| Workflow | Builder | Purpose |
|---------|---------|---------|
| `conversation` | `build_conversation_graph` | Main chat interaction |
| `discovery` | `build_discovery_graph` | Full entity discovery |
| `discovery_simple` | `build_simple_discovery_graph` | Lightweight discovery |
| `analysis` | `build_analysis_graph` | DS team analysis pipeline |
| `team_analysis` | `build_team_analysis_graph` | Multi-specialist team analysis |
| `optimization` | `build_optimization_graph` | Behavioral optimization |
| `dashboard` | `build_dashboard_graph` | Dashboard generation |
| `review` | `build_review_graph` | Config review workflow |

State types are in `src/graph/state/` (ConversationState, AnalysisState, DiscoveryState, DashboardState, ReviewState, OrchestratorState, WorkflowState).

---

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

---

## Sandbox Isolation

All DS Team analysis scripts run in a gVisor sandbox via Podman:

- **No network access** (default)
- **Read-only filesystem** (except `/tmp`)
- **Memory/CPU limits** enforced (tiered: quick 256MB, standard 512MB, deep 1GB)
- **Timeout enforcement** (tiered: quick 15s, standard 30s, deep 60s)
- **Pre-installed**: pandas, numpy, matplotlib, scipy, scikit-learn, seaborn
- **Artifact collection**: charts and data files can be extracted from sandbox runs
- **Security policies** defined in `src/sandbox/policies.py`
- **Artifact validation** in `src/sandbox/artifact_validator.py`

---

## Scheduled & Event-Driven Insights

Two trigger mechanisms feed into the same analysis pipeline:

```
  ┌──── Cron (APScheduler) ────►┐
  │   "0 2 * * *"               │   Existing analysis pipeline
  │                              │   (DS Team + sandbox)
  └──── Webhook (HA event) ────►│   → Insight persisted to DB
        POST /webhooks/ha        │
                                 └──────────────────────────────
```

---

## Data Layer

| Store | Purpose |
|-------|---------|
| **PostgreSQL** | Conversations, messages, entities, devices, areas, automation proposals, insights, insight schedules, discovery sessions, agents (config + prompt versions), analysis reports, flow grades, LLM usage, model ratings, HA zones, passkey credentials, system config, user profiles, LangGraph checkpoints |
| **MLflow** | Agent traces with parent-child spans, token usage, latency metrics, evaluation scores |

### Database Models (21+)

All models are in `src/storage/entities/`:

| Model | Purpose |
|-------|---------|
| `Agent`, `AgentConfigVersion`, `AgentPromptVersion` | Agent configuration and versioning |
| `AnalysisReport` | DS team analysis reports with artifacts |
| `Area` | HA areas |
| `AutomationProposal` | Automation proposals (HITL workflow) |
| `Conversation`, `Message` | Chat state |
| `Device` | HA devices |
| `DiscoverySession` | Entity discovery sessions |
| `FlowGrade` | Conversation quality grades |
| `HAAutomation`, `Scene`, `Script`, `Service` | HA registry items |
| `HAEntity` | Discovered HA entities |
| `HAZone` | Multi-server HA zones |
| `Insight`, `InsightSchedule` | Analysis insights and schedules |
| `LLMUsage` | Token counts, costs, latency per LLM call |
| `ModelRating` | Model quality ratings |
| `PasskeyCredential` | WebAuthn credentials |
| `SystemConfig` | System-wide config (HA URL, setup status) |
| `UserProfile` | User profiles |

---

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

---

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

---

## Middleware & Cross-Cutting Concerns

### Request Pipeline

```
Request → CORS → Body Size Limit → Security Headers → Correlation ID → Auth → Route Handler
                                                                                │
Response ← Request Tracing Middleware ← Exception Handler ← ────────────────────
```

| Layer | Description |
|-------|-------------|
| **Security Headers** | HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Permissions-Policy |
| **Correlation ID** | UUID generated per request, propagated through context vars to all logs and error responses |
| **Auth** | JWT token (cookie/Bearer), WebAuthn passkey, API key (`X-API-Key` header or `api_key` param), or HA token; bypasses for health/ready/status/login endpoints |
| **Rate Limiting** | SlowAPI-based limits on LLM-backed and resource-intensive endpoints |
| **Request Tracing** | Logs method, path, status, duration, correlation ID for every request |
| **Metrics Collection** | In-memory counters for request rates, latency percentiles, error rates, active connections |
| **Exception Hierarchy** | `AetherError` → `AgentError`, `DALError`, `HAClientError`, `SandboxError`, `LLMError`, `ConfigurationError`, `ValidationError` — all include correlation IDs |

---

## LLM Provider Abstraction (`src/llm/`)

The LLM subsystem is in `src/llm/`:

| Module | Purpose |
|--------|---------|
| `factory.py` | Multi-provider LLM factory (OpenAI, OpenRouter, Google, Ollama, Together, Groq) |
| `circuit_breaker.py` | Circuit breaker pattern — opens after 5 failures, retries after 60s cooldown |
| `resilient.py` | Resilient LLM wrapper with automatic failover to secondary provider |
| `usage.py` | Token counting, cost estimation, pricing tables |

---

## MCP Client (`src/mcp/`)

The MCP (Model Context Protocol) client abstracts communication with Home Assistant:

| Module | Purpose |
|--------|---------|
| `client.py` | MCP client connection and tool invocation |
| `entities.py` | Entity operations (list, get state, search) |
| `automations.py` | Automation CRUD |
| `automation_deploy.py` | Deploy automations to HA |
| `behavioral.py` | Logbook and behavioral data |
| `diagnostics.py` | Diagnostic data collection |
| `history.py` | Historical state data |
| `logbook.py` | HA logbook entries |
| `parsers.py` | Response parsing |
| `workarounds.py` | HA API workarounds |

---

## Target Architecture (Jarvis Pivot)

> **Status**: Planned (Features 29/30). See `docs/architecture-review.md` for the full readiness assessment.

The current Architect-centric architecture will evolve into a domain-agnostic Orchestrator pattern. The Architect becomes one of several domain agents, and a new Orchestrator handles intent classification and routing.

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

### Implementation Phases

1. **Phase 0**: Pre-pivot refactoring (centralize HITL, wire Feature 23, split workflows.py)
2. **Phase 1**: Orchestrator + intent routing + KnowledgeAgent + `agent` field + UI picker
3. **Phase 2**: ResearchAgent + FoodAgent + cross-domain delegation + voice pipeline
4. **Phase 3**: Dynamic workflow composition + dynamic agent creation + persistence

See `docs/architecture-review.md` for the full assessment, gap analysis, and risk register.

---

## Distributed Architecture (A2A Protocol)

When `DEPLOYMENT_MODE=distributed`, agents run as separate containers communicating via the [A2A protocol](https://google.github.io/A2A/):

```
                    +-----------------+
User  -->  API Gateway (:8000)  -->  | Architect (:8001) |
                                     +-----------------+
                                            |
                                            | A2A SendMessage
                                            v
                                     +---------------------+
                                     | DS Orchestrator     |
                                     | (:8002)             |
                                     +---------------------+
                                            |
                                            | A2A SendMessage (confidence loops)
                                            v
                                     +---------------------+
                                     | DS Analysts (:8003) |
                                     | Energy + Behavioral |
                                     | + Diagnostic        |
                                     +---------------------+
                                            |
                                            v
                                      gVisor Sandbox
```

### Container Responsibilities

| Container | Agent(s) | Pattern | Description |
|-----------|----------|---------|-------------|
| API Gateway | None (routing only) | Gateway | HTTP, auth, SSE streaming, delegates to Architect via A2A |
| Architect | ArchitectAgent | Single-agent | Conversational agent, proposals, delegates to DS Orchestrator |
| DS Orchestrator | DataScientistAgent | Single-agent | Coordinates analysts, confidence loops, synthesis |
| DS Analysts | Energy + Behavioral + Diagnostic | Multi-agent | Analysts share AnalysisState in-process |

### A2A Protocol

Each agent container exposes:
- `POST /` — JSON-RPC endpoint for `SendMessage` / `SendStreamingMessage`
- `GET /.well-known/agent-card.json` — Agent Card describing skills and capabilities
- `GET /health` — Liveness probe
- `GET /ready` — Readiness probe

State is serialized into A2A `DataPart` using `pack_state_to_data()` which handles LangChain message serialization via `dumpd()`/`load()`.

### Dual-Mode Switch

The `resolve_agent_invoker()` function in `src/agents/dual_mode.py` checks `DEPLOYMENT_MODE`:
- `monolith`: instantiates agent classes in-process (default)
- `distributed`: uses `A2ARemoteClient` to call the agent's service URL

See [Distributed Mode Guide](distributed-mode.md) for the full runbook.

---

## See Also

- [API Reference](api-reference.md) — all ~120 REST API endpoints
- [Distributed Mode](distributed-mode.md) — running agents as A2A services
- [Development](development.md) — project structure and code organization
- [Configuration](configuration.md) — environment variables and LLM setup
- [User Flows](user-flows.md) — step-by-step interaction sequences
