# Project Aether

> Agentic home automation system for Home Assistant

*100% vibecoded by AI (mostly Claude) and mass quantities of coffee. No humans were mass-harmed in the making of this codebase — just mass-caffeinated.*

> [!CAUTION]
> **This project is in early alpha and has not had a stable release.** Expect rough edges, breaking changes, and incomplete features. It is shared as a learning resource and experimentation platform — not as production-ready software. Use at your own risk, especially any features that write to your Home Assistant instance.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Project Aether is an intelligent home automation system that connects AI agents to your Home Assistant instance. Instead of writing YAML by hand or clicking through dashboards, you have a conversation — describe what you want, and Aether's agents discover your devices, analyze your energy data, diagnose problems, and design automations for you.

**Key idea**: An Orchestrator agent classifies user intent and dynamically routes requests to specialized domain agents (Architect, Data Science team, Food, Research, Knowledge, Dashboard Designer, and more). Each agent is configured with the right model, tools, and prompt at runtime. All mutating actions require human approval via the web UI or push notifications (iPhone/Apple Watch).

---

## Features

- **Intelligent Orchestration** — an Orchestrator agent classifies intent, selects the right domain agent and model tier (fast/standard/frontier), and presents clarification options for ambiguous requests
- **Conversational Home Control** — chat with your smart home in natural language; all mutating actions require explicit approval (HITL) via web UI or push notification
- **Push Notification Approval** — mutating actions can be approved/rejected from iPhone or Apple Watch via HA actionable notifications
- **Web Search** — domain agents can search the web for recipes, prices, documentation, and more via DuckDuckGo
- **Dynamic Agent Composition** — agents are configured at runtime with DB-backed prompts, tools, and model selection; workflows can be composed on-the-fly
- **Entity Discovery** — the Librarian agent catalogs all HA entities, devices, and areas into a searchable database
- **Automation Design** — describe automations in plain English; the Architect designs YAML and presents it for approval before deploying
- **Energy Analysis** — the DS team's Energy Analyst analyzes consumption patterns via sandboxed Python scripts
- **Diagnostics & Troubleshooting** — the Diagnostic Analyst investigates error logs, entity health, and integration issues
- **Intelligent Optimization** — the Behavioral Analyst detects patterns and suggests automations for recurring manual actions
- **YAML Schema Validation** — structural and semantic validation of automations, scripts, scenes, and dashboards against live HA state
- **Smart Config Review** — review existing HA configs with improvement suggestions presented as approvable proposal diffs
- **Dashboard Designer** — generates Lovelace dashboard YAML tailored to your home's entities and areas
- **Analysis Reports** — detailed reports with artifacts from DS team analysis sessions
- **Scheduled & Event-Driven Insights** — cron schedules and HA webhook triggers feed into the analysis pipeline
- **Agent Activity Tracing** — real-time visualization of agent delegation and trace timelines in the chat UI
- **Authentication & Passkeys** — WebAuthn (Face ID / Touch ID), HA token, password, and API key auth methods
- **Multi-Provider LLM** — OpenAI, OpenRouter, Google Gemini, Ollama, Together AI, Groq with per-agent model routing and failover
- **Full Observability** — every agent operation traced via MLflow with parent-child spans, token usage, and latency metrics
- **Trace Evaluation** — custom MLflow scorers evaluate agent trace quality (latency, safety, delegation depth)

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interfaces                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │   CLI       │    │  REST API   │    │    Chat UI (React)              │  │
│  │  (aether)   │    │  (FastAPI)  │    │    localhost:3000               │  │
│  └──────┬──────┘    └──────┬──────┘    └───────────────┬─────────────────┘  │
│         └──────────────────┼───────────────────────────┘                    │
│                            ▼                                                │
│              ┌─────────────────────────────┐                                │
│              │   /v1/chat/completions      │  (OpenAI-compatible)           │
│              │   /api/conversations        │  (Native API)                  │
│              └──────────────┬──────────────┘                                │
└─────────────────────────────┼───────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                       Agent Layer                                           │
│                             ▼                                               │
│              ┌─────────────────────────────┐                                │
│              │    Orchestrator Agent       │  ◄── Classifies intent,        │
│              │  (classify → plan → route)  │      routes to domain agents   │
│              └──────────────┬──────────────┘                                │
│                             │ delegates via tools                           │
│         ┌──────────┬────────┼────────┬──────────┐                          │
│         ▼          ▼        ▼        ▼          ▼                          │
│  ┌───────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐            │
│  │   Data    │ │Librarian│ │Developer│ │Dashboard│ │  Schema    │            │
│  │  Science  │ │ Agent  │ │ Agent  │ │Designer│ │ Validator  │            │
│  │   Team    │ │        │ │        │ │        │ │            │            │
│  └─────┬─────┘ └───┬────┘ └───┬────┘ └───┬────┘ └──────┬─────┘            │
│        │           │          │           │             │                  │
│        ▼           ▼          ▼           ▼             ▼                  │
│  ┌───────────┐ ┌────────┐ ┌────────────┐ ┌────────┐ ┌──────────┐          │
│  │ Sandbox   │ │  MCP   │ │ Automation │ │Lovelace│ │ YAML     │          │
│  │ (gVisor)  │ │ Client │ │  Deploy    │ │ YAML   │ │ Schemas  │          │
│  └───────────┘ └────────┘ └────────────┘ └────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                       Data Layer                                            │
│         ┌───────────────────┼───────────────────┐                           │
│         ▼                   ▼                                               │
│  ┌─────────────┐    ┌─────────────┐                                        │
│  │ PostgreSQL  │    │   MLflow    │                                        │
│  │  (State)    │    │  (Traces)   │                                        │
│  └─────────────┘    └─────────────┘                                        │
└──────────────────────────────────────────┬─────────────────────────────────┘
                                           │
┌──────────────────────────────────────────┼─────────────────────────────────┐
│                    External Services      │                                 │
│         ┌────────────────────────────────┴──────────────────┐              │
│         ▼                                                   ▼              │
│  ┌─────────────────┐                               ┌─────────────────┐    │
│  │ Home Assistant  │                               │   LLM Provider  │    │
│  │   (via MCP)     │                               │ (OpenAI/etc.)   │    │
│  └─────────────────┘                               └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Agents

| Agent | Role | What It Does |
|-------|------|--------------|
| **Orchestrator** | Intent Routing | Classifies user intent and dynamically routes to the best domain agent with the right model tier (fast/standard/frontier). Entry point for `agent=auto`. |
| **Architect** | Home Automation | Designs automations, reviews existing HA configs, runs diagnostics, and delegates to the DS team. Has 16 curated tools. |
| **Data Science Team** | Analysis & Insights | Three specialists: Energy Analyst, Behavioral Analyst, Diagnostic Analyst. Share findings via TeamAnalysis with dual synthesis (programmatic + LLM). Scripts run in gVisor sandbox. |
| **Librarian** | Discovery & Catalog | Discovers all HA entities, devices, and areas. Builds a searchable local catalog. |
| **Developer** | Deployment | Takes approved automation proposals and deploys them to Home Assistant. Falls back to manual instructions if the API is unreachable. |
| **Dashboard Designer** | Dashboard Generation | Designs Lovelace dashboards by consulting the DS team for entity/area data and generating validated YAML configs. |

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Podman](https://podman.io/) or Docker (for PostgreSQL, MLflow)
- Node.js 18+ (for the UI)
- A Home Assistant instance with a [long-lived access token](https://www.home-assistant.io/docs/authentication/)
- An LLM API key (OpenAI, OpenRouter, or other — see [Configuration](docs/configuration.md))

### Setup

```bash
# Clone the repository
git clone https://github.com/dimakis/Project-Aether.git
cd Project-Aether

# Install Python dependencies
make install

# Install UI dependencies
# Requires npm
make ui-install

# Configure environment
cp .env.example .env
# Edit .env with your HA_TOKEN, HA_URL, and LLM_API_KEY
```

### Run

```bash
# Start everything (infrastructure + API + UI)
make run-ui

# Open the chat UI
open http://localhost:3000
```

That's it. The UI connects to the API at `localhost:8000`, which talks to your Home Assistant via MCP.

### First Steps

1. **Open the Chat** at `http://localhost:3000` and try: "Discover my home"
2. **Browse Entities** on the Entities page to see what was found
3. **Ask a question**: "What lights are currently on?" or "Analyze my energy usage"
4. **Design an automation**: "Create an automation that turns on the porch light at sunset"
5. **Check diagnostics**: "Are any of my devices unavailable?"

---

## Deployment Modes

Aether supports two deployment modes:

### Monolith (default)

All agents run in a single Python process. This is the simplest setup for development and single-user deployments.

```bash
make run       # Dev: infra in containers, API on host with hot-reload
make run-ui    # Dev + React UI
make run-prod  # Everything containerized
```

### Distributed (A2A agent services)

Agents run as separate containers communicating via the [A2A protocol](https://google.github.io/A2A/). The monolith acts as an API gateway, delegating to agent services.

```bash
make run-distributed   # Gateway + all agent services
```

```
API Gateway :8000
  ├── Orchestrator     :8007
  ├── Architect        :8001
  ├── DS Orchestrator  :8002  -->  DS Analysts :8003
  ├── Developer        :8004
  ├── Librarian        :8005
  └── Dashboard Designer :8006
```

Each agent container serves an A2A Agent Card at `/.well-known/agent-card.json` and health probes at `/health`.

See [Distributed Mode Guide](docs/distributed-mode.md) for the full runbook.

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Authentication, deployment modes, remote access |
| [Distributed Mode](docs/distributed-mode.md) | Running agents as A2A services in separate containers |
| [Configuration](docs/configuration.md) | LLM providers, per-agent overrides, failover, usage tracking, environment variables |
| [Architecture](docs/architecture.md) | System design, agent roles, data flows, observability, security model |
| [User Flows](docs/user-flows.md) | Step-by-step interaction sequences for all major features |
| [API Reference](docs/api-reference.md) | All ~120 REST API endpoints |
| [CLI Reference](docs/cli-reference.md) | Terminal commands for the `aether` CLI |
| [Development](docs/development.md) | Dev setup, testing, quality checks, project structure |
| [UI Guide](ui/README.md) | UI pages, tech stack, development |
| [Contributing](CONTRIBUTING.md) | Workflow, coding standards, branch strategy |
| [Security](SECURITY.md) | Vulnerability reporting, security model |
| [Data Model](specs/001-project-aether/data-model.md) | Database schema reference |
| [Feature Specs](specs/001-project-aether/features/) | Individual feature specifications |
| [OpenAPI Spec](specs/001-project-aether/contracts/api.yaml) | Machine-readable API contract |

---

## Project Principles

1. **Safety First (HITL)**: All mutating Home Assistant actions require explicit human approval. No automation deploys without your "approve."
2. **Isolation**: DS Team analysis scripts run in gVisor sandboxes — no network access, read-only filesystem, enforced resource limits.
3. **Observability**: Every agent action is traced via MLflow with full span trees, token counts, and latency metrics. Custom scorers evaluate trace quality.
4. **Reliable State**: LangGraph + PostgreSQL for checkpointed workflow state. Conversations, proposals, and insights persist across restarts.
5. **Reliability**: Comprehensive testing (unit, integration, E2E) with TDD workflow. 80% minimum unit test coverage target.
6. **Security**: Defence in depth — encrypted credentials (Fernet/AES-256), bcrypt password hashing, Pydantic input validation, parameterized queries, security headers.

---

## Known Issues & Limitations

> [!WARNING]
> **Dashboard Designer — use with extreme caution.** Deploying a generated dashboard **replaces your entire dashboard YAML** rather than merging into it. If you have a carefully crafted Lovelace config, deploying a dashboard proposal will overwrite it completely. A rollback mechanism exists (the previous config is snapshotted before deploy), but restoring a complex dashboard is painful. The in-editor preview only renders after deployment, so you cannot see the result before committing. Dashboard schema validation is structural only — it checks that views exist but does not validate entity IDs, card types, or semantic correctness against your actual HA state.

Other things to be aware of in this alpha:

- **No stable release yet** — APIs, database schema, and agent behavior may change without notice.
- **LLM-generated YAML** — automations and scripts are generated by an LLM. Always review proposals carefully before approving deployment.
- **Schema validation gaps** — automation and script validation is more mature than dashboard validation. Dashboard YAML is only checked structurally (required fields, valid YAML) with no semantic validation against your HA instance.

---

## License

MIT
