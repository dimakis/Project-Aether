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
│         ┌───────────────────┼───────────────────┐                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   Data      │    │  Librarian  │    │  Developer  │                     │
│  │  Scientist  │    │   Agent     │    │   Agent     │                     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                     │
│         │                  │                  │                             │
│         ▼                  ▼                  ▼                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │  Sandbox    │    │    MCP      │    │  Automation  │                    │
│  │  (gVisor)   │    │   Client    │    │   Deploy     │                    │
│  └─────────────┘    └─────────────┘    └──────────────┘                    │
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
| **Architect** | Orchestrator & Chat | The unified entry point. Handles conversation, routes to specialists, designs automations. Has 12 curated tools. |
| **Data Science Team** | Analysis & Insights | Three specialists: Energy Analyst, Behavioral Analyst, Diagnostic Analyst. Share findings via TeamAnalysis, auto-synthesize. Scripts run in gVisor sandbox. |
| **Librarian** | Discovery & Catalog | Discovers all HA entities, devices, and areas. Builds a searchable local catalog. |
| **Developer** | Deployment | Takes approved automation proposals and deploys them to Home Assistant via the REST API (`/api/config/automation/config`). Falls back to manual instructions if the API is unreachable. |

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
git clone https://github.com/dimakis/Project-Aether.git
cd Project-Aether

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

The Architect is the unified entry point for all user requests. It has 12 curated tools and delegates to specialist agents:

| Tool | Delegates To | Purpose |
|------|-------------|---------|
| `consult_data_science_team` | DS Team (Energy, Behavioral, Diagnostic Analysts) | All analysis, diagnostics, and optimization. Smart-routes to the right specialist(s). |
| `discover_entities` | Librarian | Entity catalog refresh |
| `seek_approval` | Developer (on approval) | Route all mutating actions through the approval workflow |
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

### Data Layer

| Store | Purpose |
|-------|---------|
| **PostgreSQL** | Conversations, messages, entities, devices, areas, automation proposals, insights, insight schedules, discovery sessions, LangGraph checkpoints |
| **MLflow** | Agent traces with parent-child spans, token usage, latency metrics |

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
| **Registry** | `/registry` | Home Assistant registry management — devices, areas, automations |
| **Schedules** | `/schedules` | Manage cron schedules and webhook triggers for automated insights |
| **LLM Usage** | `/usage` | LLM API call tracking — daily trends, cost by model, token breakdown |
| **Diagnostics** | `/diagnostics` | System health, error logs, integration status, entity diagnostics |
| **Login** | `/login` | Authentication — passkey (Face ID / Touch ID) or password login |

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

All endpoints require authentication via JWT token (cookie or Bearer header), API key (`X-API-Key` header or `api_key` query parameter), or passkey. Health, status, metrics, and login endpoints are exempt.

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
| `GET` | `/api/v1/health` | Health check (no auth required) |
| `GET` | `/api/v1/status` | System status with component health (no auth required) |
| `GET` | `/api/v1/metrics` | Operational metrics (request rates, latency, errors) |
| **Conversations** | | |
| `POST` | `/api/v1/conversations` | Start new conversation |
| `GET` | `/api/v1/conversations` | List conversations |
| `GET` | `/api/v1/conversations/{id}` | Get conversation with messages |
| `POST` | `/api/v1/conversations/{id}/messages` | Send a message |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation |
| **Entities** | | |
| `GET` | `/api/v1/entities` | List entities (with filtering) |
| `GET` | `/api/v1/entities/{id}` | Get entity details |
| `POST` | `/api/v1/entities/query` | Natural language entity query |
| `POST` | `/api/v1/entities/sync` | Trigger entity sync from HA |
| `GET` | `/api/v1/entities/domains/summary` | Domain counts |
| **Devices & Areas** | | |
| `GET` | `/api/v1/devices` | List devices |
| `GET` | `/api/v1/areas` | List areas |
| **Insights** | | |
| `GET` | `/api/v1/insights` | List insights |
| `GET` | `/api/v1/insights/{id}` | Get insight details |
| `POST` | `/api/v1/insights/analyze` | Trigger analysis |
| **Insight Schedules** | | |
| `GET` | `/api/v1/insight-schedules` | List schedules |
| `POST` | `/api/v1/insight-schedules` | Create schedule |
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
| **Optimization** | | |
| `POST` | `/api/v1/optimize` | Run optimization analysis |
| `GET` | `/api/v1/optimize/{job_id}` | Get optimization status |
| `GET` | `/api/v1/optimize/suggestions/list` | List automation suggestions |
| `POST` | `/api/v1/optimize/suggestions/{id}/accept` | Accept suggestion |
| `POST` | `/api/v1/optimize/suggestions/{id}/reject` | Reject suggestion |
| **HA Registry** | | |
| `GET` | `/api/v1/registry/automations` | List HA automations |
| `GET` | `/api/v1/registry/scripts` | List HA scripts |
| `GET` | `/api/v1/registry/scenes` | List HA scenes |
| `GET` | `/api/v1/registry/services` | List known services |
| `POST` | `/api/v1/registry/sync` | Sync automations/scripts/scenes from HA |
| `POST` | `/api/v1/registry/services/call` | Call an HA service |
| `GET` | `/api/v1/registry/summary` | Registry summary |
| **Webhooks** | | |
| `POST` | `/api/v1/webhooks/ha` | Receive HA webhook events |
| **Traces** | | |
| `GET` | `/api/v1/traces/{trace_id}/spans` | Get trace span tree for visualization |
| **Authentication** | | |
| `GET` | `/api/v1/auth/setup-status` | Check if first-time setup is complete (public) |
| `POST` | `/api/v1/auth/setup` | First-time setup: validate HA, store config, return JWT (public, one-shot) |
| `POST` | `/api/v1/auth/login` | Password login (checks DB hash, then env var fallback) |
| `POST` | `/api/v1/auth/login/ha-token` | HA token login (validates against stored HA URL) |
| `POST` | `/api/v1/auth/logout` | Clear session cookie |
| `GET` | `/api/v1/auth/me` | Check session status |
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
aether entities list               # List all entities
aether entities query "kitchen lights"  # Natural language query
aether entities show <entity_id>   # Show entity details

# Devices & Areas
aether devices list                # List discovered devices
aether areas list                  # List discovered areas

# Chat
aether chat                        # Interactive chat session

# Automation proposals
aether proposals list              # List proposals
aether proposals approve <id>      # Approve a proposal
aether proposals reject <id>       # Reject a proposal

# Energy analysis
aether analyze energy --days 7     # Run energy analysis

# Insights
aether insights list               # List generated insights
aether insights show <id>          # Show insight details

# HA Registry
aether automations list            # List HA automations
aether scripts list                # List HA scripts
aether scenes list                 # List HA scenes
aether services list               # List known services

# System
aether status                      # Show system status
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
```

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
├── agents/              # AI agents (Architect, DS Team, Librarian, Developer)
│   ├── architect.py     # Orchestrator — routes to DS team, designs automations
│   ├── energy_analyst.py# Energy consumption analysis (DS Team)
│   ├── behavioral_analyst.py # Behavioral patterns (DS Team)
│   ├── diagnostic_analyst.py # System health diagnostics (DS Team)
│   ├── data_scientist.py# Legacy orchestrator (used by scheduled analysis)
│   ├── librarian.py     # Entity discovery and cataloging
│   ├── developer.py     # Automation deployment (HITL)
│   ├── model_context.py # Model routing and per-agent overrides
│   └── prompts/         # Externalized prompt templates (markdown)
├── api/                 # FastAPI application
│   ├── routes/          # API endpoints (chat, entities, insights, proposals, etc.)
│   ├── schemas/         # Pydantic request/response models
│   ├── auth.py          # API key authentication dependency
│   ├── metrics.py       # In-memory operational metrics collector
│   ├── middleware.py    # Request tracing middleware
│   └── main.py          # App factory with lazy initialization
├── cli/                 # Typer CLI application
│   ├── main.py          # CLI entry point and top-level commands
│   └── commands/        # Subcommands (chat, discover, analyze, serve, etc.)
├── dal/                 # Data Access Layer (repositories)
│   ├── base.py          # Generic BaseRepository[T] for common CRUD
│   ├── entities.py      # Entity repository
│   ├── areas.py         # Area repository
│   ├── devices.py       # Device repository
│   └── ...              # Other domain repositories
├── diagnostics/         # HA diagnostic modules (log parser, entity health, etc.)
├── graph/               # LangGraph workflows and state management
│   ├── nodes/           # Domain-specific nodes (discovery, conversation, analysis)
│   └── workflows.py     # Workflow graph definitions
├── mcp/                 # MCP client for Home Assistant communication
│   ├── base.py          # Base HTTP client
│   ├── entities.py      # Entity operations
│   ├── automations.py   # Automation/script/scene management
│   ├── diagnostics.py   # Diagnostic operations
│   └── client.py        # Thin facade
├── sandbox/             # gVisor sandbox runner for script execution
├── scheduler/           # APScheduler for cron/webhook insight triggers
├── storage/             # SQLAlchemy models and database setup
│   └── entities/        # Domain models (entity, device, area, conversation, etc.)
├── tools/               # Agent tool definitions (HA tools, diagnostic tools)
├── tracing/             # MLflow tracing integration
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
│   │   ├── dashboard.tsx
│   │   └── entities.tsx
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

Project Aether follows a constitution with five core principles:

1. **Safety First (HITL)**: All mutating Home Assistant actions require explicit human approval. No automation deploys without your "approve."

2. **Isolation**: DS Team analysis scripts run in gVisor sandboxes — no network access, read-only filesystem, enforced resource limits. Generated code never touches your HA instance directly.

3. **Observability**: Every agent action is traced via MLflow with full span trees, token counts, and latency metrics. Nothing happens in the dark.

4. **Reliable State**: LangGraph + PostgreSQL for checkpointed workflow state. Conversations, proposals, and insights persist across restarts.

5. **Quality**: Comprehensive testing (unit, integration, E2E) with TDD workflow support. Ruff linting, MyPy type checking, and pre-commit hooks.

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
