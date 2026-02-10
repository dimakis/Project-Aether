# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Multi-provider LLM support** — OpenAI, OpenRouter (100+ models), Google Gemini, Ollama (local/free), Together AI, Groq, and custom OpenAI-compatible APIs
- **Per-agent model routing** — configure different models per agent for cost optimization; resolution order: UI selection > per-agent env > global default
- **LLM circuit breaker & failover** — automatic retry with exponential backoff and configurable fallback provider
- **LLM usage tracking** — token counts, estimated costs, and latency per call; dashboard with daily trends, per-model breakdown, and cost estimates; pricing data for OpenAI, Anthropic, Google, Meta, DeepSeek, and Mistral models
- **Data Science team architecture** — three specialists (Energy Analyst, Behavioral Analyst, Diagnostic Analyst) with shared cross-consultation via TeamAnalysis and auto-synthesis
- **Behavioral Analyst** — detects behavioral patterns from logbook data, identifies manual actions that could be automated, and proposes automation suggestions to the Architect
- **Agent activity tracing panel** — real-time visualization of active agents, delegation flow, and trace timeline in the chat UI
- **WebAuthn / Passkey authentication** — Face ID / Touch ID login via passkey registration during first-time setup
- **HA-verified first-time setup wizard** — validates HA connection, sets fallback password, registers passkey; stores HA config encrypted in DB
- **HA token login** — alternative auth method validating against stored HA URL
- **Google OAuth 2.0** — optional sign-in via Google identity
- **Scheduled & event-driven insights** — cron schedules (APScheduler with PostgreSQL persistence) and HA webhook triggers for automated analysis
- **Discovery sync** — periodic delta sync of HA entities with configurable interval
- **HA Registry management** — browse and sync automations, scripts, scenes, and services from Home Assistant
- **Optimization API** — run optimization analysis, list automation suggestions, accept/reject suggestions
- **Enterprise security hardening** for production deployment
  - HSTS, CSP, and Permissions-Policy security headers
  - `/api/v1/ready` readiness probe endpoint for Kubernetes
  - `AETHER_ROLE` setting for multi-replica K8s deployment (api/scheduler/all)
  - Production guard blocking unsandboxed script execution
- **Centralized exception hierarchy** — `AetherError` with subtypes and correlation IDs for request tracing
- **Operational metrics** — request rates, latency, and error tracking via `/api/v1/metrics`
- Open-source readiness files (LICENSE, CONTRIBUTING.md, SECURITY.md, CHANGELOG.md)
- GitHub CI pipeline (lint, type check, unit/integration/E2E tests, coverage, security scan)
- PR templates, issue templates, and PR governance workflows (dependency review, conventional commit title check, auto-labelling)
- **YAML schema validation** (Feature 26) — Pydantic + JSON Schema validation for HA automation, script, scene, and dashboard YAML; `SchemaRegistry` with pluggable schemas
- **Semantic YAML validation** (Feature 27) — validates entity IDs, service calls, and area IDs against the live HA registry via `SemanticValidator`
- **Smart Config Review** (Feature 28) — Architect reviews existing HA configs, consults DS team, and produces improvement proposals with original/proposed YAML diffs
- **Dashboard Designer agent** — Lovelace dashboard generation by consulting DS team for entity/area data; tools: `generate_dashboard_yaml`, `validate_dashboard_yaml`, `list_dashboards`
- **MLflow 3.x trace evaluation** — custom scorers (`response_latency`, `tool_usage_safety`, `agent_delegation_depth`, `tool_call_count`) with on-demand and nightly evaluation
- **`aether evaluate` CLI command** — evaluate recent agent traces with MLflow 3.x scorers
- **Evaluations API** — `GET /evaluations/summary`, `POST /evaluations/run`, `GET /evaluations/scorers`
- **Diagnostics API** — `GET /diagnostics/ha-health`, `GET /diagnostics/error-log`, `GET /diagnostics/config-check`, `GET /diagnostics/traces/recent`
- **Agent configuration API** (Feature 23) — full CRUD for agent config/prompt versioning, promotion, rollback, cloning, and AI-generated prompts; runtime config cache with 60s TTL
- **Activity stream** — `GET /activity/stream` SSE endpoint for real-time agent activity events
- **Flow grades API** — submit, list, and delete flow grades for conversation quality tracking
- **HA zones API** — CRUD for HA zones with connectivity testing and default zone selection
- **Model ratings API** — rate models, view summaries, and track performance metrics
- **Workflow presets API** — `GET /workflows/presets` for chat UI workflow selection
- **Dual synthesis** — programmatic + LLM synthesis strategies for DS team findings (`src/agents/synthesis.py`)
- **Agent runtime config cache** — async in-memory cache for agent configs to avoid per-call DB queries (`src/agents/config_cache.py`)

### Changed
- Upgraded Fernet key derivation from SHA-256 to PBKDF2-HMAC-SHA256 (480k iterations)
- Rate limiter now uses X-Forwarded-For for real client IP behind reverse proxies
- `/metrics` endpoint now requires authentication (removed from auth-exempt routes)
- Status endpoint error messages sanitized in production (no internal details)
- Containerfile updated with proxy headers, graceful shutdown, and K8s-ready defaults
- `.env.example` updated to reflect multi-provider LLM config, scheduler, discovery sync, and all current settings

### Security
- Fixed rate limiting bypass when behind reverse proxy (all clients shared same IP)
- Prevented information leakage in health check error messages
- Added HSTS to enforce HTTPS in production/staging environments
- Added CSP to restrict resource loading on API responses
- Blocked unsandboxed script execution in production environment

## [0.1.0] - 2025-01-01

### Added
- Initial release of Project Aether
- Multi-agent system with Architect, Librarian, Data Scientist, and Developer agents
- LangGraph-based workflow orchestration with human-in-the-loop approval
- Home Assistant integration via MCP (Model Context Protocol)
- FastAPI REST API with JWT + WebAuthn authentication
- React dashboard UI with chat, proposals, insights, entities, and trace views
- PostgreSQL storage with Alembic migrations
- MLflow observability and trace visualization
- gVisor-sandboxed script execution for data analysis
- APScheduler-based scheduled and event-driven insights
- OpenAI-compatible API endpoint for third-party integrations
