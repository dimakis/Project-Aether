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
