# Project Aether

> Agentic home automation system for Home Assistant

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Project Aether is an intelligent home automation system that connects AI agents to your Home Assistant instance. Instead of writing YAML by hand or clicking through dashboards, you have a conversation — describe what you want, and Aether's agents discover your devices, analyze your energy data, diagnose problems, and design automations for you.

**Key idea**: A team of specialized AI agents (Architect, Data Science team, Librarian, Developer) collaborate to understand your smart home and act on your behalf — with human approval required for any changes.

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [User Flows](#user-flows)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [LLM Usage Tracking](#llm-usage-tracking)
- [Remote Access](#remote-access)
- [Deployment Modes](#deployment-modes)
- [LLM Configuration](#llm-configuration)
- [Architecture](#architecture)
- [UI Pages](#ui-pages)
- [API Reference](#api-reference)
- [CLI Reference](#cli-reference)
- [Development](#development)
- [Project Principles](#project-principles)
- [Documentation](#documentation)

---

## Features

### Conversational Home Control
Chat with your smart home in natural language. Ask to turn on lights, check sensor readings, or query entity states. All mutating actions require your explicit approval (Human-in-the-Loop).

### Entity Discovery & Catalog
The Librarian agent automatically discovers and catalogs all Home Assistant entities, devices, and areas into a searchable database. Query your home with natural language — "which lights are on in the kitchen?" or "show me all temperature sensors."

### Automation Design
Describe an automation in plain English — "turn off the lights when everyone leaves" — and the Architect agent designs it, generates the YAML, and presents it for your approval before deploying to Home Assistant.

### Energy Analysis
The Data Science team's Energy Analyst analyzes your energy consumption patterns using historical data. It generates Python analysis scripts, executes them in a secure gVisor sandbox, and returns insights with projected savings.

### Diagnostics & Troubleshooting
When something goes wrong — missing sensor data, unavailable devices, integration errors — the Architect delegates to the Data Science team via a single `consult_data_science_team` call. The team's Diagnostic Analyst analyzes error logs, entity health, and integration status to produce actionable diagnoses.

### Intelligent Optimization
The Data Science team's Behavioral Analyst detects behavioral patterns from logbook data, identifies manual actions that could be automated, and suggests optimizations. When it finds a high-impact opportunity, it proposes it to the Architect, who can design an automation for you.

### YAML Schema Validation
Validates Home Assistant configuration YAML (automations, scripts, scenes, dashboards) against structural schemas and — optionally — against live HA state. Catches typos, missing entities, invalid service calls, and unknown areas before deployment. Integrates with Smart Config Review and the Architect's automation design flow.

### Smart Config Review
Ask the Architect to review your existing HA configurations. It fetches the current YAML from Home Assistant, consults the Data Science team for analysis, and produces improvement suggestions as proposal diffs you can approve and deploy — just like the automation design flow.

### Dashboard Designer
The Dashboard Designer agent creates Lovelace dashboard YAML by consulting the Data Science team for entity and area data, then generating a dashboard layout tailored to your home. Dashboards can be validated against the schema before deployment.

### Trace Evaluation
Custom MLflow 3.x scorers automatically evaluate agent trace quality: response latency, tool usage safety (mutation tools require prior approval), delegation depth (detects runaway chains), and tool call counts. Run evaluations on-demand via the API or the `aether evaluate` CLI command.

### Scheduled & Event-Driven Insights
Set up cron schedules (e.g., daily energy analysis at 2 AM) or HA webhook triggers (e.g., run diagnostics when a device goes unavailable). Uses APScheduler with PostgreSQL-backed persistence.

### Agent Activity Tracing
A real-time visualization panel in the chat UI shows which agents are active, how they delegate to each other, and a timeline of trace events — making the "thinking" process visible and debuggable.

### Authentication & Passkeys
HA-verified first-time setup: on first launch, a setup wizard prompts for your Home Assistant URL and long-lived access token. After validation, you set an optional fallback password and register a passkey. Subsequent logins support **passkeys** (primary, Face ID / Touch ID), **HA token** (alternative), and **password** (fallback). All methods coexist — use a passkey from your phone and an API key for scripts.

### LLM Usage Tracking
Every LLM API call is tracked with token counts, estimated costs, and response latency. The Usage dashboard shows daily trends, per-model breakdowns, and cost estimates. Pricing data covers OpenAI, Anthropic, Google, Meta, DeepSeek, and Mistral models.

### Multi-Provider LLM Support
Works with OpenAI, OpenRouter (100+ models), Google Gemini, Ollama (local/free), Together AI, and Groq. Per-agent model routing lets you use a premium model for the Architect and a cheaper model for script generation.

### Full Observability
Every agent operation is traced via MLflow with parent-child span relationships, token usage, and latency metrics. View traces at `http://localhost:5002`.

### API Security & Resilience
API key authentication (via header or query param), centralized exception hierarchy with correlation IDs for request tracing, and operational metrics collection (request rates, latency, error tracking).

### LLM Resilience
Circuit breaker pattern with automatic provider failover. When your primary LLM provider fails, Aether retries with exponential backoff and falls back to a configured secondary provider.

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
│              │      Architect Agent        │  ◄── Unified entry point       │
│              │   (Routes + Orchestrates)   │      for all user requests     │
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
│         ▼                   ▼                                                 │
│  ┌─────────────┐    ┌─────────────┐                                         │
│  │ PostgreSQL  │    │   MLflow    │                                         │
│  │  (State)    │    │  (Traces)   │                                         │
│  └─────────────┘    └─────────────┘                                         │
└──────────────────────────────────────────┬──────────────────────────────────┘
                                           │
┌──────────────────────────────────────────┼──────────────────────────────────┐
│                    External Services      │                                  │
│         ┌────────────────────────────────┴──────────────────┐               │
│         ▼                                                   ▼               │
│  ┌─────────────────┐                               ┌─────────────────┐     │
│  │ Home Assistant  │                               │   LLM Provider  │     │
│  │   (via MCP)     │                               │ (OpenAI/etc.)   │     │
│  └─────────────────┘                               └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Agents

| Agent | Role | What It Does |
|-------|------|--------------|
| **Architect** | Orchestrator & Chat | The unified entry point. Handles conversation, routes to specialists, designs automations, reviews existing configs. Has 14 curated tools. |
| **Data Science Team** | Analysis & Insights | Three specialists: Energy Analyst, Behavioral Analyst, Diagnostic Analyst. Share findings via TeamAnalysis with dual synthesis (programmatic + LLM). Scripts run in gVisor sandbox. |
| **Librarian** | Discovery & Catalog | Discovers all HA entities, devices, and areas. Builds a searchable local catalog. |
| **Developer** | Deployment | Takes approved automation proposals and deploys them to Home Assistant via the REST API (`/api/config/automation/config`). Falls back to manual instructions if the API is unreachable. |
| **Dashboard Designer** | Dashboard Generation | Designs Lovelace dashboards by consulting the DS team for entity/area data and generating validated YAML configs. |

### Model Context Propagation

When you select a model in the UI (e.g., `claude-sonnet-4`), that choice propagates through all agent delegations. Per-agent overrides in `.env` allow cost optimization:

```
Resolution order:  UI selection  >  per-agent .env setting  >  global default
```

---

## User Flows

### 1. Chat & Home Control

```
You: "Turn on the living room lights"
         │
         ▼
    ┌─────────────┐
    │  Architect   │  Detects entity control intent
    └──────┬──────┘
           │
           ▼
    ┌─────────────────┐
    │ WAITING APPROVAL │  "I can turn on light.living_room. Reply 'approve' to proceed."
    └──────┬──────────┘
           │
      You: "approve"
           │
           ▼
    ┌─────────────┐
    │ Execute via │──▶ Home Assistant (MCP)
    │    MCP      │
    └─────────────┘
           │
           ▼
    "Done! The living room lights are now on."
```

### 2. Entity Discovery

```
You: "Discover my home" (or run `make discover`)
         │
         ▼
    ┌─────────────┐    ┌─────────────┐
    │  Architect   │──▶│  Librarian   │
    └─────────────┘    └──────┬──────┘
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              list_entities  domain   system
              (all domains)  summary  overview
                    │         │         │
                    └─────────┼─────────┘
                              ▼
                    ┌─────────────────┐
                    │  Infer devices  │  (from entity attributes)
                    │  Extract areas  │  (from entity area_ids)
                    │  Sync automations│ (from list_automations)
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ Persist to DB   │  Entities, devices, areas stored
                    │ (PostgreSQL)    │  in local catalog
                    └─────────────────┘
                             │
                             ▼
    "Discovered 847 entities across 23 domains, 12 areas, 156 devices."
```

### 3. Automation Design (HITL)

```
You: "Create an automation that turns off the hallway lights at midnight"
         │
         ▼
    ┌─────────────┐
    │  Architect   │  Queries entity catalog for hallway lights
    └──────┬──────┘  Designs automation trigger + action
           │
           ▼
    ┌───────────────────┐
    │ Automation        │  Status: PROPOSED
    │ Proposal          │  Shows YAML + explanation
    │                   │  "Here's what this will do..."
    └──────┬────────────┘
           │
      You: "approve"
           │
           ▼
    ┌─────────────┐    ┌─────────────┐
    │  Developer   │──▶│ Deploy to   │  Generates YAML, reloads HA
    │   Agent      │    │ Home Asst.  │
    └─────────────┘    └─────────────┘
           │
           ▼
    "Automation deployed! 'Hallway lights midnight off' is now active in HA."
    
    (You can later: view, disable, or rollback via /proposals)
```

### 4. Energy Analysis

```
You: "Analyze my energy consumption this week"
         │
         ▼
    ┌─────────────┐         ┌──────────────────┐
    │  Architect   │────────▶│  DS Team (Energy) │
    └─────────────┘         └────────┬─────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            Discover energy    Fetch 7 days      Generate Python
            sensors (MCP)      of history (MCP)   analysis script (LLM)
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                            ┌─────────────────┐
                            │  gVisor Sandbox  │  Execute script in isolation
                            │  (pandas/numpy)  │  No network, read-only FS
                            └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │ Extract Insights │  Parse output, identify patterns
                            │    (LLM)         │  Calculate projected savings
                            └────────┬────────┘
                                     │
                                     ▼
    "Your total consumption was 187 kWh this week. Peak usage occurs
     between 6-8 PM. Suggestion: Shifting your EV charging to off-peak
     hours (midnight-6 AM) could save ~$12/month."
     
    Insight persisted to DB, viewable in /insights
```

### 5. Diagnostics & Troubleshooting

```
You: "My car charger energy data disappeared from my dashboards"
         │
         ▼
    ┌─────────────┐
    │  Architect   │
    └──────┬──────┘
           │
    ┌──────┼───────────────────────────────────────┐
    │      ▼                                        │
    │  analyze_error_log()    → Parse HA error log  │
    │  find_unavailable()     → Scan entity health  │  Evidence
    │  diagnose_entity(...)   → Deep-dive sensors   │  gathering
    │  check_integration()    → Integration status  │
    │  validate_config()      → Config validation   │
    └──────┬────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ consult_data_science_team() │  Auto-routes to Diagnostic Analyst
    └──────┬───────────────────────┘
           │
           ▼
    ┌──────────────────┐
    │  DS Team          │  Diagnostic Analyst: analyze data gaps,
    │  (sandbox)        │  sensor connectivity, integration failures
    └──────┬───────────┘
           │
           ▼
    (Architect may call again with refined query)
           │
           ▼
    "I found the issue: Your Easee integration lost connection 3 days ago
     (error: 'authentication token expired'). The charger entity has been
     'unavailable' since then. To fix: Go to Settings → Integrations → 
     Easee → Reconfigure and re-authenticate."
```

### 6. Scheduled Insights

```
You: "Run energy analysis every day at 2 AM"
         │
         ▼
    ┌─────────────────────────────┐
    │ POST /insight-schedules     │
    │ {                           │
    │   "name": "Daily energy",   │
    │   "analysis_type": "energy",│
    │   "trigger_type": "cron",   │
    │   "cron_expression":        │
    │     "0 2 * * *"             │
    │ }                           │
    └─────────────┬───────────────┘
                  │
                  ▼
    APScheduler (PostgreSQL-backed) fires at 2:00 AM daily
                  │
                  ▼
    DS Team runs analysis → Insight persisted → Visible in UI
```

Webhook triggers work similarly — configure an HA automation to POST to `/api/v1/webhooks/ha` when specific events occur (e.g., device goes unavailable), and Aether runs the analysis automatically.

### 7. Optimization Suggestions (Agent Collaboration)

```
    DS Team's Behavioral Analyst discovers a pattern during analysis:
    "User manually turns off living room lights every night at 11 PM"
         │
         ▼
    ┌──────────────────┐
    │ AutomationSugg.  │  High-confidence, actionable
    │ {                 │
    │  trigger: time    │
    │  action: light.off│
    │  confidence: 0.92 │
    │ }                 │
    └──────┬───────────┘
           │ returned to Architect via tool response
           ▼
    ┌─────────────┐
    │  Architect   │  "The Behavioral Analyst noticed you turn off the living room
    └──────┬──────┘   lights every night at 11 PM. Want me to create an
           │          automation for that?"
           ▼
      You: "Yes please"
           │
           ▼
    (Standard automation design flow with HITL approval)
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Podman](https://podman.io/) or Docker (for PostgreSQL, MLflow)
- Node.js 18+ (for the UI)
- A Home Assistant instance with a [long-lived access token](https://www.home-assistant.io/docs/authentication/)
- An LLM API key (OpenAI, OpenRouter, or other — see [LLM Configuration](#llm-configuration))

### Setup

```bash
# Clone the repository
git clone https://github.com/dsaridak/home_agent.git
cd home_agent

# Install Python dependencies
make install

# Install UI dependencies
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

## Authentication

Aether uses HA-verified first-time setup and supports four authentication methods:

### First-Time Setup

On first launch, the UI shows a setup wizard:

1. **Enter HA URL + token** — Aether validates the connection by calling the HA API
2. **Set fallback password** (optional) — stored as a bcrypt hash in the database
3. **Register a passkey** — Face ID / Touch ID for quick biometric login

The HA URL and token are stored in the database (encrypted with Fernet, key derived from `JWT_SECRET`). Setup can only be run once; to re-run, delete the `system_config` DB row.

### 1. Passkey / Biometric Login (WebAuthn) — Primary

The recommended login method. After registering a passkey during setup, use Face ID, Touch ID, or Windows Hello to sign in instantly.

Configure for your domain:

```bash
WEBAUTHN_RP_ID=home.example.com     # your domain (must match URL)
WEBAUTHN_RP_NAME=Aether             # display name
WEBAUTHN_ORIGIN=https://home.example.com  # full origin URL
```

> **Note**: WebAuthn requires HTTPS in production. Use Cloudflare Tunnel or Tailscale for secure remote access.

### 2. HA Token Login — Alternative

Log in using any valid Home Assistant long-lived access token. Aether validates the token against the stored HA URL (from setup) or env var fallback.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ha-token \
  -H "Content-Type: application/json" \
  -d '{"ha_token": "your-long-lived-access-token"}'
```

### 3. Password Login (JWT) — Fallback

If you set a password during setup, use it to log in. Aether checks the DB hash first, then falls back to the `AUTH_PASSWORD` env var.

```bash
# Optional env var fallback (DB password from setup takes priority)
AUTH_USERNAME=admin
AUTH_PASSWORD=your-secret
JWT_SECRET=a-long-random-string  # optional, auto-derived if empty
JWT_EXPIRY_HOURS=72
```

Login via the UI or API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-secret"}'
```

The JWT is returned in the response body **and** as an httpOnly cookie (`aether_session`).

### 4. API Key (Programmatic Access)

For scripts, CLI tools, or external integrations:

```bash
API_KEY=your-api-key
```

Pass via header or query parameter:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/entities
```

### Auth Disabled (Development)

When no setup has been completed and neither `AUTH_PASSWORD` nor `API_KEY` is set, authentication is completely disabled for development convenience.

---

## LLM Usage Tracking

Every LLM call is automatically tracked with token counts and estimated costs.

### Dashboard

Navigate to **LLM Usage** in the sidebar to see:
- **Summary cards**: total calls, tokens, estimated cost, models used
- **Daily usage chart**: calls per day over the selected period
- **Cost by model**: pie chart showing cost distribution
- **Model breakdown table**: per-model stats with latency

### API Endpoints

```bash
# Get usage summary (last 30 days)
GET /api/v1/usage/summary?days=30

# Get daily breakdown
GET /api/v1/usage/daily?days=30

# Get per-model breakdown
GET /api/v1/usage/models?days=30
```

### Custom Pricing

Override or add model pricing with a JSON file:

```bash
LLM_PRICING_FILE=/path/to/pricing.json
```

Format:

```json
{
  "my-custom-model": {
    "input_per_1m": 1.50,
    "output_per_1m": 5.00
  }
}
```

---

## Remote Access

To access Aether from your phone or outside your home network:

### Recommended: Cloudflare Tunnel (Free)

1. Install `cloudflared` on your HA machine
2. Create a tunnel: `cloudflared tunnel create aether`
3. Configure to route to `http://localhost:3000`
4. Update your `.env`:

```bash
WEBAUTHN_RP_ID=aether.your-domain.com
WEBAUTHN_ORIGIN=https://aether.your-domain.com
ALLOWED_ORIGINS=https://aether.your-domain.com
```

Benefits: no port forwarding, automatic HTTPS, DDoS protection.

### Alternative: Tailscale (VPN)

1. Install Tailscale on your HA machine and phone
2. Access via Tailscale IP: `http://100.x.y.z:3000`

Benefits: zero-config VPN, no public exposure, works with HTTP (no HTTPS needed for WebAuthn on Tailscale).

### Security Checklist

- [ ] Set `AUTH_PASSWORD` to a strong password
- [ ] Set `JWT_SECRET` to a random 32+ character string
- [ ] Configure `ALLOWED_ORIGINS` for your domain
- [ ] Register a passkey for passwordless login
- [ ] Use HTTPS (required for WebAuthn on public domains)

---

## Deployment Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Development** | `make run` | Infrastructure in containers, API on host with hot-reload |
| **Dev + UI** | `make run-ui` | Above + React UI dev server with HMR |
| **Production** | `make run-prod` | Everything containerized (Podman Compose) |
| **Stop** | `make down` | Stop all services and containers |

### Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| Chat UI | `3000` | React frontend |
| Aether API | `8000` | FastAPI backend (OpenAI-compatible + native API) |
| MLflow | `5002` | Trace viewer for agent observability |
| PostgreSQL | `5432` | State, conversations, entities, insights |

---

## LLM Configuration

Project Aether supports multiple LLM backends. Configure in your `.env`:

### OpenRouter (Recommended — access to 100+ models)

```bash
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL=anthropic/claude-sonnet-4
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

### Local Ollama (Free, private)

```bash
LLM_PROVIDER=ollama
LLM_MODEL=mistral:latest
# No API key needed
```

### Other OpenAI-Compatible APIs

```bash
LLM_PROVIDER=together  # or groq, custom
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.together.xyz/v1
LLM_MODEL=meta-llama/Llama-3-70b-chat-hf
```

### Per-Agent Model Overrides

Optimize cost by using cheaper models for specific agents:

```bash
# Global (used by Architect)
LLM_MODEL=anthropic/claude-sonnet-4

# DS Team specialists use a cheaper model for script generation
DATA_SCIENTIST_MODEL=gpt-4o-mini
DATA_SCIENTIST_TEMPERATURE=0.3
```

Resolution order: **UI model selection > per-agent `.env` setting > global default**.

### LLM Failover

Configure a fallback provider for resilience:

```bash
# Primary provider
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-v1-your-key
LLM_MODEL=anthropic/claude-sonnet-4

# Fallback provider (used when primary fails after retries)
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_MODEL=gpt-4o
```

The circuit breaker opens after 5 consecutive failures and retries after a 60-second cooldown.

---

## Architecture

### Agent System

The Architect is the unified entry point for all user requests. It has 14 curated tools and delegates to specialist agents:

| Tool | Delegates To | Purpose |
|------|-------------|---------|
| `consult_data_science_team` | DS Team (Energy, Behavioral, Diagnostic Analysts) | All analysis, diagnostics, and optimization. Smart-routes to the right specialist(s). |
| `discover_entities` | Librarian | Entity catalog refresh |
| `seek_approval` | Developer (on approval) | Route all mutating actions through the approval workflow |
| `review_config` | Review workflow (DS Team + Architect) | Review existing HA configs and suggest improvements |
| `create_insight_schedule` | System | Recurring or event-driven analysis |
| `get_entity_state`, `list_entities_by_domain`, `search_entities`, `get_domain_summary` | — (direct HA) | Entity queries |
| `list_automations`, `render_template`, `get_ha_logs`, `check_ha_config` | — (direct HA) | HA state and config queries |

### DS Team Collaboration

The Architect delegates to the Data Science team via a single `consult_data_science_team` call. The team auto-selects specialists based on query keywords (energy, behavioral, diagnostic), runs them with shared cross-consultation (`TeamAnalysis`), and returns a synthesized response. For complex issues, the Architect can call again with refined queries.

### Sandbox Isolation

All DS Team analysis scripts run in a gVisor sandbox via Podman:

- **No network access** (default)
- **Read-only filesystem** (except `/tmp`)
- **Memory/CPU limits** enforced
- **Timeout enforcement** (default 30s)
- **Pre-installed**: pandas, numpy, matplotlib, scipy, scikit-learn, seaborn

### Scheduled & Event-Driven Insights

Two trigger mechanisms feed into the same analysis pipeline:

```
  ┌──── Cron (APScheduler) ────►┐
  │   "0 2 * * *"               │   Existing analysis pipeline
  │                              │   (DS Team + sandbox)
  └──── Webhook (HA event) ────►│   → Insight persisted to DB
        POST /webhooks/ha        │
                                 └──────────────────────────────
```

### Schema Validation

HA configuration YAML is validated in two phases:

1. **Structural** — Pydantic models + JSON Schema validate triggers, actions, conditions, and dashboard cards against known HA schemas (`src/schema/core.py`, `src/schema/ha/`).
2. **Semantic** — `SemanticValidator` checks entity IDs, service calls, and area IDs against the live HA registry (`src/schema/semantic.py`).

Validation is used during automation design, config review, and dashboard generation.

### Data Layer

| Store | Purpose |
|-------|---------|
| **PostgreSQL** | Conversations, messages, entities, devices, areas, automation proposals, insights, insight schedules, discovery sessions, agents, flow grades, LLM usage, LangGraph checkpoints |
| **MLflow** | Agent traces with parent-child spans, token usage, latency metrics, evaluation scores |

### Observability

All agent operations are traced via MLflow:

```
Session: conv-12345
├── ArchitectAgent.invoke
│   ├── inputs: {"message": "Analyze energy"}
│   ├── llm.ainvoke
│   ├── analyze_energy (tool)
│   │   └── DataScientistWorkflow.run_analysis
│   │       ├── collect_energy_data
│   │       ├── generate_script
│   │       ├── execute_sandbox
│   │       └── extract_insights
│   └── outputs: {"response": "I analyzed...", "insights": [...]}
```

View traces: `http://localhost:5002`

---

## UI Pages

The React frontend provides a modern interface for interacting with Aether:

| Page | Path | Description |
|------|------|-------------|
| **Dashboard** | `/` | System overview — entity counts, pending proposals, recent insights, domain breakdown |
| **Chat** | `/chat` | Conversational interface with streaming, model selection, thinking disclosure, and agent activity panel |
| **Proposals** | `/proposals` | View, approve, deploy to HA, or rollback automation proposals. Includes an Architect prompt for generating new proposals directly. |
| **Insights** | `/insights` | Browse analysis results — energy patterns, behavioral insights, diagnostics |
| **Entities** | `/entities` | Browse and search all discovered HA entities with filtering |
| **Registry** | `/registry` | Home Assistant registry management — devices, areas, automations, scripts, scenes, services |
| **Agents** | `/agents` | Agent configuration — LLM model, temperature, prompt versioning, tool assignment, enable/disable |
| **Schedules** | `/schedules` | Manage cron schedules and webhook triggers for automated insights |
| **LLM Usage** | `/usage` | LLM API call tracking — daily trends, cost by model, token breakdown |
| **Diagnostics** | `/diagnostics` | System health, HA error log with pattern matching, integration status, entity diagnostics, recent agent traces |
| **Login** | `/login` | Authentication — passkey (Face ID / Touch ID), HA token, or password login |

### Chat Features

- **Streaming responses** with markdown rendering and syntax highlighting
- **Model selection** — pick any model from your configured provider
- **Thinking disclosure** — expandable "thinking" blocks show agent reasoning
- **Agent activity panel** — real-time visualization of which agents are working, delegation flow, and trace timeline
- **Conversation history** — persistent sessions with auto-titling
- **Quick suggestions** — pre-built prompts for common tasks
- **Feedback** — thumbs up/down on responses

---

## API Reference

All endpoints require authentication via JWT token (cookie or Bearer header), API key (`X-API-Key` header or `api_key` query parameter), or passkey. Health, ready, status, and login endpoints are exempt.

### OpenAI-Compatible Endpoints

These endpoints allow any OpenAI-compatible client to work with Aether:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/models` | List available agents as "models" |
| `POST` | `/api/v1/chat/completions` | Chat with agents (supports `stream: true`) |
| `POST` | `/api/v1/feedback` | Submit feedback on responses |

### Native API

| Method | Endpoint | Description |
|--------|----------|-------------|
| **System** | | |
| `GET` | `/api/v1/health` | Liveness probe (no auth required) |
| `GET` | `/api/v1/ready` | Readiness probe for Kubernetes (no auth required) |
| `GET` | `/api/v1/status` | System status with component health (no auth required) |
| `GET` | `/api/v1/metrics` | Operational metrics (request rates, latency, errors) |
| **Conversations** | | |
| `POST` | `/api/v1/conversations` | Start new conversation |
| `GET` | `/api/v1/conversations` | List conversations |
| `GET` | `/api/v1/conversations/{id}` | Get conversation with messages |
| `POST` | `/api/v1/conversations/{id}/messages` | Send a message |
| `WS` | `/api/v1/conversations/{id}/stream` | WebSocket streaming |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation |
| **Entities** | | |
| `GET` | `/api/v1/entities` | List entities (with filtering) |
| `GET` | `/api/v1/entities/{id}` | Get entity details |
| `POST` | `/api/v1/entities/query` | Natural language entity query |
| `POST` | `/api/v1/entities/sync` | Trigger entity sync from HA |
| `GET` | `/api/v1/entities/domains/summary` | Domain counts |
| **Devices & Areas** | | |
| `GET` | `/api/v1/devices` | List devices |
| `GET` | `/api/v1/devices/{id}` | Get device details |
| `GET` | `/api/v1/areas` | List areas |
| `GET` | `/api/v1/areas/{id}` | Get area details |
| **Insights** | | |
| `GET` | `/api/v1/insights` | List insights |
| `GET` | `/api/v1/insights/pending` | List pending insights |
| `GET` | `/api/v1/insights/summary` | Insights summary |
| `GET` | `/api/v1/insights/{id}` | Get insight details |
| `POST` | `/api/v1/insights` | Create insight |
| `POST` | `/api/v1/insights/{id}/review` | Mark insight reviewed |
| `POST` | `/api/v1/insights/{id}/action` | Mark insight actioned |
| `POST` | `/api/v1/insights/{id}/dismiss` | Dismiss insight |
| `DELETE` | `/api/v1/insights/{id}` | Delete insight |
| `POST` | `/api/v1/insights/analyze` | Trigger analysis |
| **Insight Schedules** | | |
| `GET` | `/api/v1/insight-schedules` | List schedules |
| `POST` | `/api/v1/insight-schedules` | Create schedule |
| `GET` | `/api/v1/insight-schedules/{id}` | Get schedule |
| `PUT` | `/api/v1/insight-schedules/{id}` | Update schedule |
| `DELETE` | `/api/v1/insight-schedules/{id}` | Delete schedule |
| `POST` | `/api/v1/insight-schedules/{id}/run` | Manual trigger |
| **Proposals** | | |
| `GET` | `/api/v1/proposals` | List automation proposals (filterable by status) |
| `GET` | `/api/v1/proposals/pending` | List proposals awaiting approval |
| `GET` | `/api/v1/proposals/{id}` | Get proposal details with YAML |
| `POST` | `/api/v1/proposals` | Create a new proposal directly |
| `POST` | `/api/v1/proposals/{id}/approve` | Approve proposal |
| `POST` | `/api/v1/proposals/{id}/reject` | Reject proposal |
| `POST` | `/api/v1/proposals/{id}/deploy` | Deploy approved proposal to HA |
| `POST` | `/api/v1/proposals/{id}/rollback` | Rollback deployed proposal |
| `DELETE` | `/api/v1/proposals/{id}` | Delete proposal |
| **Optimization** | | |
| `POST` | `/api/v1/optimize` | Run optimization analysis |
| `GET` | `/api/v1/optimize/{job_id}` | Get optimization status |
| `GET` | `/api/v1/optimize/suggestions/list` | List automation suggestions |
| `POST` | `/api/v1/optimize/suggestions/{id}/accept` | Accept suggestion |
| `POST` | `/api/v1/optimize/suggestions/{id}/reject` | Reject suggestion |
| **HA Registry** | | |
| `POST` | `/api/v1/registry/sync` | Sync automations/scripts/scenes from HA |
| `GET` | `/api/v1/registry/automations` | List HA automations |
| `GET` | `/api/v1/registry/automations/{id}` | Get automation details |
| `GET` | `/api/v1/registry/automations/{id}/config` | Get automation YAML config |
| `GET` | `/api/v1/registry/scripts` | List HA scripts |
| `GET` | `/api/v1/registry/scripts/{id}` | Get script details |
| `GET` | `/api/v1/registry/scenes` | List HA scenes |
| `GET` | `/api/v1/registry/scenes/{id}` | Get scene details |
| `GET` | `/api/v1/registry/services` | List known services |
| `GET` | `/api/v1/registry/services/{id}` | Get service details |
| `POST` | `/api/v1/registry/services/call` | Call an HA service |
| `POST` | `/api/v1/registry/services/seed` | Seed common services |
| `GET` | `/api/v1/registry/summary` | Registry summary |
| **Diagnostics** | | |
| `GET` | `/api/v1/diagnostics/ha-health` | HA health (unavailable entities, unhealthy integrations) |
| `GET` | `/api/v1/diagnostics/error-log` | Parsed HA error log with pattern matching |
| `GET` | `/api/v1/diagnostics/config-check` | HA config validation |
| `GET` | `/api/v1/diagnostics/traces/recent` | Recent agent traces from MLflow |
| **Evaluations** | | |
| `GET` | `/api/v1/evaluations/summary` | Latest trace evaluation summary |
| `POST` | `/api/v1/evaluations/run` | Trigger on-demand trace evaluation |
| `GET` | `/api/v1/evaluations/scorers` | List available scorers |
| **Agents** | | |
| `GET` | `/api/v1/agents` | List all agents with active config |
| `GET` | `/api/v1/agents/{name}` | Get agent by name |
| `PATCH` | `/api/v1/agents/{name}` | Update agent status |
| `PATCH` | `/api/v1/agents/{name}/model` | Quick model switch |
| `POST` | `/api/v1/agents/{name}/clone` | Clone agent |
| `GET` | `/api/v1/agents/{name}/config/versions` | List config versions |
| `POST` | `/api/v1/agents/{name}/config/versions` | Create config draft |
| `PATCH` | `/api/v1/agents/{name}/config/versions/{id}` | Update config draft |
| `POST` | `/api/v1/agents/{name}/config/versions/{id}/promote` | Promote config |
| `POST` | `/api/v1/agents/{name}/config/rollback` | Rollback config |
| `GET` | `/api/v1/agents/{name}/prompt/versions` | List prompt versions |
| `POST` | `/api/v1/agents/{name}/prompt/versions` | Create prompt draft |
| `POST` | `/api/v1/agents/{name}/prompt/versions/{id}/promote` | Promote prompt |
| `POST` | `/api/v1/agents/{name}/prompt/rollback` | Rollback prompt |
| `POST` | `/api/v1/agents/{name}/promote-all` | Promote config + prompt |
| `POST` | `/api/v1/agents/{name}/prompt/generate` | AI-generate system prompt |
| `POST` | `/api/v1/agents/seed` | Seed default agents |
| **Activity** | | |
| `GET` | `/api/v1/activity/stream` | SSE stream for real-time agent activity |
| **Flow Grades** | | |
| `POST` | `/api/v1/flow-grades` | Submit flow grade |
| `GET` | `/api/v1/flow-grades/{conversation_id}` | Get grades for conversation |
| `DELETE` | `/api/v1/flow-grades/{grade_id}` | Delete grade |
| **HA Zones** | | |
| `GET` | `/api/v1/zones` | List HA zones |
| `POST` | `/api/v1/zones` | Create zone |
| `PATCH` | `/api/v1/zones/{id}` | Update zone |
| `DELETE` | `/api/v1/zones/{id}` | Delete zone |
| `POST` | `/api/v1/zones/{id}/set-default` | Set default zone |
| `POST` | `/api/v1/zones/{id}/test` | Test zone connectivity |
| **Model Ratings** | | |
| `GET` | `/api/v1/models/ratings` | List model ratings |
| `POST` | `/api/v1/models/ratings` | Create model rating |
| `GET` | `/api/v1/models/summary` | Model summaries |
| `GET` | `/api/v1/models/performance` | Model performance metrics |
| **Webhooks** | | |
| `POST` | `/api/v1/webhooks/ha` | Receive HA webhook events |
| **Traces** | | |
| `GET` | `/api/v1/traces/{trace_id}/spans` | Get trace span tree for visualization |
| **Workflows** | | |
| `GET` | `/api/v1/workflows/presets` | List workflow presets for chat UI |
| **Authentication** | | |
| `GET` | `/api/v1/auth/setup-status` | Check if first-time setup is complete (public) |
| `POST` | `/api/v1/auth/setup` | First-time setup: validate HA, store config, return JWT (public, one-shot) |
| `POST` | `/api/v1/auth/login` | Password login (checks DB hash, then env var fallback) |
| `POST` | `/api/v1/auth/login/ha-token` | HA token login (validates against stored HA URL) |
| `POST` | `/api/v1/auth/logout` | Clear session cookie |
| `GET` | `/api/v1/auth/me` | Check session status |
| `GET` | `/api/v1/auth/google/url` | Google OAuth URL |
| `POST` | `/api/v1/auth/google/callback` | Google OAuth callback |
| `POST` | `/api/v1/auth/passkey/register/options` | Start passkey registration (auth required) |
| `POST` | `/api/v1/auth/passkey/register/verify` | Complete passkey registration |
| `POST` | `/api/v1/auth/passkey/authenticate/options` | Start passkey login (public) |
| `POST` | `/api/v1/auth/passkey/authenticate/verify` | Complete passkey login (returns JWT) |
| `GET` | `/api/v1/auth/passkeys` | List registered passkeys |
| `DELETE` | `/api/v1/auth/passkeys/{id}` | Delete a passkey |
| **LLM Usage** | | |
| `GET` | `/api/v1/usage/summary` | Usage summary with cost (query: `?days=30`) |
| `GET` | `/api/v1/usage/daily` | Daily usage breakdown |
| `GET` | `/api/v1/usage/models` | Per-model usage breakdown |
| `GET` | `/api/v1/usage/conversation/{id}` | Conversation cost breakdown |

Interactive API docs available at `http://localhost:8000/api/docs` when running in debug mode.

Full OpenAPI spec: [`specs/001-project-aether/contracts/api.yaml`](specs/001-project-aether/contracts/api.yaml)

---

## CLI Reference

The `aether` CLI provides terminal access to all features:

```bash
# Start the API server
aether serve [--reload]

# Entity discovery
aether discover                    # Run full entity discovery
aether discover --domain light     # Discover specific domain
aether discover --force            # Force re-discovery
aether entities                    # List all entities
aether entities --domain sensor    # Filter by domain

# Devices & Areas
aether devices                     # List discovered devices
aether areas                       # List discovered areas

# Chat
aether chat                        # Interactive chat session
aether chat --continue <id>        # Continue existing conversation

# Automation proposals
aether proposals list              # List proposals
aether proposals show <id>         # Show proposal details
aether proposals approve <id>      # Approve a proposal
aether proposals reject <id>       # Reject a proposal
aether proposals deploy <id>       # Deploy approved proposal to HA
aether proposals rollback <id>     # Rollback deployed proposal

# Analysis
aether analyze energy --days 7     # Run energy analysis
aether analyze behavior            # Run behavioral analysis
aether analyze health              # Run health analysis
aether optimize behavior           # Run optimization analysis

# Insights
aether insights                    # List generated insights
aether insight <id>                # Show insight details

# HA Registry
aether automations                 # List HA automations
aether scripts                     # List HA scripts
aether scenes                      # List HA scenes
aether services                    # List known services
aether seed-services               # Seed common services into DB

# Evaluation
aether evaluate                    # Evaluate recent agent traces
aether evaluate --traces 50        # Evaluate last 50 traces
aether evaluate --hours 48         # Evaluate traces from last 48 hours

# System
aether status                      # Show system status
aether version                     # Show version info
aether ha-gaps                     # Show MCP capability gaps
```

---

## Development

### Setup

```bash
# Install with dev dependencies
uv sync

# Install UI dependencies
cd ui && npm install && cd ..

# Start infrastructure (PostgreSQL, MLflow)
make up

# Run migrations
make migrate

# Start API with hot-reload
make serve

# Start UI dev server (separate terminal)
make ui-dev
```

### Testing

```bash
make test          # Run all tests
make test-unit     # Unit tests only
make test-int      # Integration tests (requires PostgreSQL)
make test-e2e      # End-to-end tests
make test-cov      # Tests with coverage report

# TDD helpers
make test-red FILE=tests/unit/test_foo.py    # Red phase (expect failure)
make test-green FILE=tests/unit/test_foo.py  # Green phase (expect pass)
```

### Quality

```bash
make lint          # Ruff linter
make format        # Ruff formatter + auto-fix
make typecheck     # MyPy type checking
make check         # All quality checks
make ci-local      # Full CI locally (lint + typecheck + unit tests)
```

### Branch Workflow

All features and functional changes use feature branches with squash-before-push:

```bash
git checkout -b feat/my-feature develop  # 1. Create branch
# ... develop with TDD, commit incrementally ...
make ci-local                            # 2. Run CI locally — must pass
git rebase -i develop                    # 3. Squash into one commit
git push -u origin HEAD                  # 4. Push
gh pr create                             # 5. Open PR (rebase-merged)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.

### Database

```bash
make migrate                        # Run pending migrations
make migrate-new NAME=description   # Create new migration
make migrate-down                   # Rollback last migration
make psql                           # Connect to PostgreSQL
```

### Sandbox

```bash
# Build the DS Team sandbox image (pandas, numpy, scipy, etc.)
make build-sandbox
```

### Project Structure

```
src/
├── agents/              # AI agents (Architect, DS Team, Librarian, Developer, Dashboard Designer)
│   ├── architect.py     # Orchestrator — routes to DS team, designs automations, reviews configs
│   ├── energy_analyst.py       # Energy consumption analysis (DS Team)
│   ├── behavioral_analyst.py   # Behavioral patterns (DS Team)
│   ├── diagnostic_analyst.py   # System health diagnostics (DS Team)
│   ├── data_scientist.py       # Legacy orchestrator (used by scheduled analysis)
│   ├── dashboard_designer.py   # Lovelace dashboard generation
│   ├── synthesis.py            # Dual synthesis (programmatic + LLM) for DS team findings
│   ├── librarian.py     # Entity discovery and cataloging
│   ├── developer.py     # Automation deployment (HITL)
│   ├── model_context.py # Model routing and per-agent overrides
│   ├── config_cache.py  # Runtime agent config cache (Feature 23)
│   └── prompts/         # Externalized prompt templates (markdown)
├── api/                 # FastAPI application
│   ├── routes/          # 21 route modules (chat, entities, agents, diagnostics, etc.)
│   ├── schemas/         # Pydantic request/response models
│   ├── auth.py          # JWT + WebAuthn + API key + HA token authentication
│   ├── ha_verify.py     # HA connection verification for setup
│   ├── rate_limit.py    # SlowAPI rate limiting
│   ├── metrics.py       # In-memory operational metrics collector
│   ├── middleware.py    # Request tracing middleware
│   └── main.py          # App factory with lazy initialization
├── cli/                 # Typer CLI application
│   ├── main.py          # CLI entry point and top-level commands
│   └── commands/        # Subcommands (chat, discover, analyze, serve, evaluate, etc.)
├── dal/                 # Data Access Layer (repositories)
│   ├── base.py          # Generic BaseRepository[T] for common CRUD
│   ├── entities.py      # Entity repository
│   ├── agents.py        # Agent config repository (Feature 23)
│   ├── flow_grades.py   # Flow grade repository
│   ├── llm_usage.py     # LLM usage tracking repository
│   ├── insight_schedules.py  # Insight schedule repository
│   └── ...              # Other domain repositories (areas, devices, conversations, etc.)
├── diagnostics/         # HA diagnostic modules
│   ├── log_parser.py    # Parse HA error log into structured entries
│   ├── error_patterns.py # Known error patterns with fix suggestions
│   ├── entity_health.py  # Unavailable/stale entity detection
│   ├── integration_health.py  # Integration config health checks
│   └── config_validator.py    # HA config validation
├── graph/               # LangGraph workflows and state management
│   ├── nodes/           # Domain-specific nodes (discovery, conversation, analysis, review)
│   ├── state.py         # State types (ConversationState, AnalysisState, ReviewState, etc.)
│   └── workflows.py     # Workflow graph definitions and registry
├── ha/                  # Home Assistant integration
│   ├── client.py        # HAClient (MCP wrapper)
│   ├── automations.py   # Automation CRUD
│   ├── automation_deploy.py  # Deploy automations to HA
│   ├── behavioral.py    # Logbook behavioral data
│   ├── diagnostics.py   # Diagnostic data collection
│   ├── entities.py      # Entity operations
│   ├── history.py       # History data
│   └── parsers.py       # Response parsers
├── schema/              # YAML schema validation (Features 26+27)
│   ├── core.py          # SchemaRegistry, validate_yaml, validate_yaml_semantic
│   ├── semantic.py      # SemanticValidator (validates against live HA state)
│   └── ha/              # HA-specific schemas (automation, script, scene, dashboard)
├── sandbox/             # gVisor sandbox runner for script execution
├── scheduler/           # APScheduler for cron/webhook insight triggers
├── storage/             # SQLAlchemy models and database setup
│   └── entities/        # 19 domain models (entity, device, area, agent, conversation, etc.)
├── tools/               # Agent tool definitions
│   ├── agent_tools.py   # Core agent tools (consult DS team, discover, etc.)
│   ├── ha_tools.py      # HA entity/service tools
│   ├── diagnostic_tools.py   # Diagnostic tools (error log, entity health, etc.)
│   ├── review_tools.py       # Config review tools (Feature 28)
│   ├── dashboard_tools.py    # Dashboard generation tools
│   ├── analysis_tools.py     # Analysis tools for DS team
│   ├── approval_tools.py     # HITL approval tools
│   ├── specialist_tools.py   # DS team specialist delegation
│   └── insight_schedule_tools.py  # Insight schedule tools
├── tracing/             # MLflow observability
│   ├── mlflow.py        # Tracing setup and utilities
│   ├── scorers.py       # Custom MLflow 3.x scorers for trace evaluation
│   └── context.py       # Session correlation context
├── exceptions.py        # Centralized exception hierarchy (AetherError + subtypes)
├── llm.py               # Multi-provider LLM factory with circuit breaker & failover
├── settings.py          # Pydantic settings (environment variables)
└── logging_config.py    # Structured logging (structlog)

ui/
├── src/
│   ├── pages/           # React pages (each split into sub-components)
│   │   ├── chat/        # Chat page (ChatInput, MessageBubble, ModelPicker, etc.)
│   │   ├── insights/    # Insights page (InsightCard, EvidencePanel, Filters, etc.)
│   │   ├── proposals/   # Proposals page (ProposalCard, ProposalDetail, etc.)
│   │   ├── registry/    # Registry page (AutomationTab, SceneTab, etc.)
│   │   ├── agents/      # Agent configuration page (Feature 23)
│   │   ├── dashboard.tsx
│   │   ├── entities.tsx
│   │   └── diagnostics.tsx
│   ├── components/      # Reusable UI components
│   │   ├── chat/        # Chat-specific (markdown renderer, thinking, agent activity)
│   │   └── ui/          # Base components (button, card, badge, etc.)
│   ├── api/             # API client and React Query hooks
│   ├── layouts/         # App layout with sidebar navigation
│   └── lib/             # Utilities, types, storage helpers
└── vite.config.ts       # Vite configuration

tests/
├── unit/                # Unit tests (mocked dependencies)
├── integration/         # Integration tests (real PostgreSQL via testcontainers)
└── e2e/                 # End-to-end tests (full pipeline)

infrastructure/
├── podman/
│   ├── compose.yaml     # Podman Compose (PostgreSQL, MLflow, app, UI)
│   ├── Containerfile    # API container image
│   ├── Containerfile.ui # UI container image
│   └── Containerfile.sandbox  # Data science sandbox image
└── postgres/
    └── init.sql         # Database initialization
```

---

## Project Principles

Project Aether follows a constitution with six core principles:

1. **Safety First (HITL)**: All mutating Home Assistant actions require explicit human approval. No automation deploys without your "approve."

2. **Isolation**: DS Team analysis scripts run in gVisor sandboxes — no network access, read-only filesystem, enforced resource limits. Generated code never touches your HA instance directly.

3. **Observability**: Every agent action is traced via MLflow with full span trees, token counts, and latency metrics. Custom scorers evaluate trace quality. Nothing happens in the dark.

4. **Reliable State**: LangGraph + PostgreSQL for checkpointed workflow state. Conversations, proposals, and insights persist across restarts.

5. **Reliability**: Comprehensive testing (unit, integration, E2E) with TDD workflow support. 80% minimum unit test coverage target. Ruff linting, MyPy type checking.

6. **Security**: Defence in depth — encrypted credentials (Fernet/AES-256), bcrypt password hashing, Pydantic input validation, parameterized queries, security headers (HSTS, CSP), no plaintext secrets.

---

## Documentation

- [Architecture Overview](docs/architecture.md) — Detailed system design, deployment modes, data flows
- [Code Healthcheck](docs/code-healthcheck.md) — Architecture health and technical debt tracking
- [Data Model](specs/001-project-aether/data-model.md) — Database schema reference
- [Feature Specs](specs/001-project-aether/features/) — Individual feature specifications
- [OpenAPI Specification](specs/001-project-aether/contracts/api.yaml) — Full API contract (auto-generated)
- [API Documentation](http://localhost:8000/docs) — Interactive Swagger UI (when running)
- [MLflow Traces](http://localhost:5002) — Agent trace viewer (when running)

---

## License

MIT
