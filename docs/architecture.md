# Project Aether - Architecture

## Overview

Project Aether is an agentic home automation system that provides conversational interaction with Home Assistant through specialized AI agents.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interfaces                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │   CLI       │    │  REST API   │    │         Open WebUI              │  │
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
│         ▼                   ▼                   ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │ PostgreSQL  │    │   MLflow    │    │   Redis     │                     │
│  │  (State)    │    │  (Traces)   │    │  (Cache)    │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                    External Services                                         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│         ┌───────────────────┴───────────────────┐                           │
│         ▼                                       ▼                           │
│  ┌─────────────────┐                    ┌─────────────────┐                 │
│  │ Home Assistant  │                    │   OpenAI API    │                 │
│  │    (MCP)        │                    │   (LLM)         │                 │
│  └─────────────────┘                    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agent Responsibilities

| Agent | Role | Tools |
|-------|------|-------|
| **Architect** | Unified chat entry point, routes to specialists, system diagnostics | analyze_energy, discover_entities, get_entity_history, diagnose_issue, get_ha_logs, check_ha_config, HA tools |
| **Data Scientist** | Energy analysis, pattern detection, insights, diagnostic analysis | Sandbox execution, history aggregation, diagnostic mode |
| **Librarian** | Entity discovery, catalog maintenance | MCP list_entities, domain_summary |
| **Developer** | Automation creation, YAML generation | deploy_automation (with HITL) |

### Diagnostic Collaboration Flow

The Architect and Data Scientist collaborate to diagnose Home Assistant issues (missing data, sensor failures, integration problems):

```
User → Architect: "My car charger energy data disappeared"
         │
         ├─→ get_ha_logs()                    # Check HA error logs
         ├─→ check_ha_config()                # Validate HA configuration
         ├─→ get_entity_history(detailed=true) # Identify data gaps
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
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ PostgreSQL  │  │   MLflow    │  │   Redis     │              │
│  │   :5432     │  │   :5002     │  │   :6379     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
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
│  │ PostgreSQL  │  │   MLflow    │  │ Open WebUI  │              │
│  │   :5432     │  │   :5002     │  │   :3000     │              │
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
│  │                    Open WebUI :3000                      │    │
│  └────────────────────────────┬────────────────────────────┘    │
│                               │                                  │
│  ┌────────────────────────────▼────────────────────────────┐    │
│  │                   Aether API :8000                       │    │
│  └────────────────────────────┬────────────────────────────┘    │
│                               │                                  │
│  ┌─────────────┐  ┌───────────┴─┐  ┌─────────────┐              │
│  │ PostgreSQL  │  │   MLflow    │  │   Redis     │              │
│  │   :5432     │  │   :5002     │  │   :6379     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
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
│  │   ├─ /         → open-webui-service                      │    │
│  │   ├─ /api      → aether-api-service                      │    │
│  │   └─ /mlflow   → mlflow-service                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ open-webui  │  │ aether-api  │  │  mlflow     │              │
│  │ Deployment  │  │ Deployment  │  │ Deployment  │              │
│  │ (replicas:2)│  │ (replicas:3)│  │ (replicas:1)│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ StatefulSets                                             │    │
│  │  ├─ PostgreSQL (1 replica + PVC)                        │    │
│  │  └─ Redis (1 replica + PVC)                             │    │
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

### OpenAI-Compatible (for Open WebUI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/models` | GET | List available agents (architect, data-scientist) |
| `/v1/chat/completions` | POST | Chat with agents (supports streaming) |

### Native API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conversations` | POST | Start new conversation |
| `/api/conversations/{id}/messages` | POST | Continue conversation |
| `/api/entities` | GET | List entities |
| `/api/entities/query` | POST | Natural language query |
| `/api/insights` | GET/POST | Manage insights |
| `/api/insights/analyze` | POST | Trigger analysis |
| `/api/proposals` | GET | List automation proposals |
| `/api/proposals/{id}/approve` | POST | Approve automation (HITL) |

## Data Flow

### Chat Request Flow

```
User Message
     │
     ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Open WebUI  │───▶│  /v1/chat   │───▶│  Architect  │
│             │    │ /completions│    │   Agent     │
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

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `MLFLOW_TRACKING_URI` | `http://localhost:5002` | MLflow server URL |
| `HA_URL` | - | Home Assistant URL |
| `HA_TOKEN` | - | Home Assistant long-lived access token |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `LOG_LEVEL` | `INFO` | Logging level |
| `API_PORT` | `8000` | API server port |
| `WEBUI_PORT` | `3000` | Open WebUI port |
| `MLFLOW_PORT` | `5002` | MLflow UI port |

### Deployment Commands

| Command | Description |
|---------|-------------|
| `make run` | Development mode (API on host with hot-reload) |
| `make run-ui` | Development + Open WebUI chat interface |
| `make run-prod` | Production mode (everything containerized) |
| `make down` | Stop all services |

### Compose Profiles (advanced)

| Profile | Services Added | Use Case |
|---------|----------------|----------|
| (none) | postgres, mlflow, redis | Infrastructure only |
| `ui` | + open-webui | Add chat UI |
| `full` | + aether-app | Containerized API |
| `full` + `ui` | All services | Production stack |
