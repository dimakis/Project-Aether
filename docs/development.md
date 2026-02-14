# Development

Local development setup, testing, quality checks, and project structure.

---

## Setup

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

---

## Testing

```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-int          # Integration tests (requires PostgreSQL)
make test-e2e          # End-to-end tests
make test-cov          # Tests with coverage report
make test-security     # Security-focused tests
make test-watch        # Watch mode (re-run on changes)
make test-file FILE=tests/unit/test_foo.py  # Run a specific test file

# TDD helpers
make test-red FILE=tests/unit/test_foo.py    # Red phase (expect failure)
make test-green FILE=tests/unit/test_foo.py  # Green phase (expect pass)

# CI variants
make test-ci-unit          # Unit tests (CI mode)
make test-ci-integration   # Integration tests (CI mode)
```

---

## Quality

```bash
make lint              # Ruff linter
make format            # Ruff formatter + auto-fix
make format-check      # Check formatting without fixing
make typecheck         # MyPy type checking
make check             # All quality checks
make ci-local          # Full CI locally (lint + typecheck + unit tests)
make security-scan     # Security vulnerability scan
```

---

## Branch Workflow

All features and functional changes use feature branches with squash-before-push:

```bash
git checkout -b feat/my-feature develop  # 1. Create branch
# ... develop with TDD, commit incrementally ...
make ci-local                            # 2. Run CI locally — must pass
git rebase -i develop                    # 3. Squash into one commit
git push -u origin HEAD                  # 4. Push
gh pr create                             # 5. Open PR (rebase-merged)
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full details.

---

## Database

```bash
make migrate                        # Run pending migrations
make migrate-new NAME=description   # Create new migration
make migrate-down                   # Rollback last migration
make migrate-history                # Show migration history
make psql                           # Connect to PostgreSQL
```

---

## Sandbox

```bash
# Build the DS Team sandbox image (pandas, numpy, scipy, etc.)
make build-sandbox
```

---

## Other Makefile Targets

```bash
make openapi           # Generate OpenAPI spec
make clean             # Clean build artifacts
make demo-us1          # Run demo scenario 1
make demo-us2          # Run demo scenario 2
make help              # Show all available targets
```

---

## Project Structure

```
src/
├── agents/                  # AI agents
│   ├── architect/           # Architect agent package
│   │   ├── agent.py         # Agent class and tool binding
│   │   ├── entity_context.py # Entity context helpers
│   │   ├── proposals.py     # Proposal extraction
│   │   ├── review.py        # Config review logic
│   │   ├── tools.py         # Tool definitions (16 curated tools)
│   │   └── workflow.py      # LangGraph workflow
│   ├── data_scientist/      # DS agent package
│   │   ├── agent.py         # DataScientistAgent
│   │   ├── collectors.py    # Data collection helpers
│   │   ├── constants.py     # Analysis types and triggers
│   │   ├── prompts.py       # Dynamic prompt building
│   │   ├── suggestions.py   # Automation suggestion extraction
│   │   └── workflow.py      # Analysis workflow
│   ├── streaming/           # Streaming infrastructure
│   │   ├── consumer.py      # Stream consumer
│   │   ├── dispatcher.py    # Event dispatcher
│   │   ├── events.py        # Event types
│   │   ├── muxer.py         # Stream multiplexer
│   │   ├── parser.py        # Tool call parser
│   │   └── proposals.py     # Proposal stream extraction
│   ├── base_analyst.py      # Shared DS specialist infrastructure
│   ├── energy_analyst.py    # Energy Analyst specialist
│   ├── behavioral_analyst.py # Behavioral Analyst specialist
│   ├── diagnostic_analyst.py # Diagnostic Analyst specialist
│   ├── synthesis.py         # Dual synthesis (programmatic + LLM)
│   ├── dashboard_designer.py # Dashboard Designer agent
│   ├── developer.py         # Developer agent (automation deployment)
│   ├── librarian.py         # Librarian agent (entity discovery)
│   ├── model_context.py     # Model routing and per-agent overrides
│   ├── config_cache.py      # Runtime agent config cache
│   ├── execution_context.py # Execution context (session, delegation, progress)
│   └── prompts/             # Externalized prompt templates (markdown)
├── api/                     # FastAPI application
│   ├── routes/              # ~26 route modules
│   │   ├── activity_stream.py   # SSE agent activity
│   │   ├── agents.py        # Agent config CRUD (22 endpoints)
│   │   ├── areas.py         # HA areas
│   │   ├── artifacts.py     # Report artifact serving
│   │   ├── auth.py          # Auth (setup, login, logout, OAuth)
│   │   ├── chat.py          # Conversations and messages
│   │   ├── dashboards.py    # Lovelace dashboard listing
│   │   ├── devices.py       # HA devices
│   │   ├── diagnostics.py   # HA health, error log, traces
│   │   ├── entities.py      # Entity CRUD and queries
│   │   ├── evaluations.py   # Trace evaluation
│   │   ├── flow_grades.py   # Flow grades
│   │   ├── ha_registry.py   # HA automations, scripts, scenes, services, helpers
│   │   ├── ha_zones.py      # Multi-server HA zones
│   │   ├── insight_schedules.py # Insight schedule CRUD
│   │   ├── insights.py      # Insight CRUD and analysis
│   │   ├── model_ratings.py # Model ratings and performance
│   │   ├── openai_compat.py # OpenAI-compatible endpoints
│   │   ├── optimization.py  # Optimization jobs and suggestions
│   │   ├── passkey.py       # WebAuthn passkey endpoints
│   │   ├── proposals.py     # Automation proposal CRUD
│   │   ├── reports.py       # Analysis report listing
│   │   ├── system.py        # Health, ready, metrics, status
│   │   ├── traces.py        # Trace span tree
│   │   ├── usage.py         # LLM usage tracking
│   │   ├── webhooks.py      # HA webhook receiver
│   │   └── workflows.py     # Workflow presets
│   ├── schemas/             # Pydantic request/response models
│   ├── services/            # Business logic services
│   │   └── model_discovery.py
│   ├── auth.py              # JWT + WebAuthn + API key + HA token auth
│   ├── ha_verify.py         # HA connection verification
│   ├── rate_limit.py        # SlowAPI rate limiting
│   ├── metrics.py           # In-memory operational metrics
│   ├── middleware.py         # Request tracing middleware
│   ├── utils.py             # API utilities
│   └── main.py              # App factory with lazy initialization
├── cli/                     # Typer CLI application
│   ├── main.py              # CLI entry point
│   ├── utils.py             # CLI utilities
│   └── commands/            # Subcommands (analyze, chat, discover, evaluate, list, proposals, serve, status)
├── dal/                     # Data Access Layer (repositories)
│   ├── base.py              # Generic BaseRepository[T]
│   ├── agents.py            # Agent config repository
│   ├── analysis_reports.py  # Analysis report repository
│   ├── entities.py          # Entity repository
│   ├── flow_grades.py       # Flow grade repository
│   ├── llm_usage.py         # LLM usage tracking
│   ├── insight_schedules.py # Insight schedule repository
│   ├── ha_zones.py          # HA zones repository
│   ├── system_config.py     # System config repository
│   ├── sync.py              # Entity sync repository
│   ├── queries.py           # Complex queries
│   └── ...                  # Other domain repositories
├── diagnostics/             # HA diagnostic modules
│   ├── log_parser.py        # Parse HA error log
│   ├── error_patterns.py    # Known error patterns with fix suggestions
│   ├── entity_health.py     # Unavailable/stale entity detection
│   ├── integration_health.py # Integration config health checks
│   └── config_validator.py  # HA config validation
├── graph/                   # LangGraph workflows and state management
│   ├── state/               # State types package
│   │   ├── analysis.py      # AnalysisState
│   │   ├── conversation.py  # ConversationState
│   │   ├── dashboard.py     # DashboardState
│   │   ├── discovery.py     # DiscoveryState
│   │   ├── orchestrator.py  # OrchestratorState
│   │   ├── review.py        # ReviewState
│   │   ├── workflow.py      # WorkflowState
│   │   ├── base.py          # Base state
│   │   └── enums.py         # State enums
│   ├── nodes/               # Domain-specific nodes
│   │   ├── analysis.py      # Analysis nodes
│   │   ├── conversation.py  # Conversation nodes
│   │   ├── discovery.py     # Discovery nodes
│   │   └── review.py        # Review nodes
│   └── workflows/           # Workflow graph definitions
│       ├── _registry.py     # Workflow registry
│       ├── analysis.py      # Analysis workflow
│       ├── conversation.py  # Conversation workflow
│       ├── dashboard.py     # Dashboard workflow
│       ├── discovery.py     # Discovery workflow
│       ├── optimization.py  # Optimization workflow
│       ├── review.py        # Config review workflow
│       └── team_analysis.py # DS team analysis workflow
├── ha/                      # Home Assistant integration
│   ├── client.py            # HAClient (MCP wrapper)
│   ├── automations.py       # Automation CRUD
│   ├── automation_deploy.py # Deploy automations to HA
│   ├── behavioral.py        # Logbook behavioral data
│   ├── dashboards.py        # Lovelace dashboard operations
│   ├── diagnostics.py       # Diagnostic data collection
│   ├── entities.py          # Entity operations
│   ├── helpers.py           # HA helper management (input_boolean, etc.)
│   ├── history.py           # History data
│   ├── logbook.py           # Logbook data
│   ├── parsers.py           # Response parsers
│   ├── constants.py         # HA constants
│   ├── gaps.py              # MCP capability gaps
│   ├── workarounds.py       # HA API workarounds
│   └── base.py              # Base HA client
├── llm/                     # LLM provider abstraction
│   ├── factory.py           # Multi-provider LLM factory
│   ├── circuit_breaker.py   # Circuit breaker pattern
│   ├── resilient.py         # Resilient LLM wrapper with failover
│   └── usage.py             # Token counting and cost estimation
├── mcp/                     # MCP client abstraction
│   ├── client.py            # MCP client
│   ├── automations.py       # Automation MCP tools
│   ├── automation_deploy.py # Deploy via MCP
│   ├── behavioral.py        # Behavioral data via MCP
│   ├── diagnostics.py       # Diagnostics via MCP
│   ├── entities.py          # Entity MCP tools
│   ├── history.py           # History via MCP
│   ├── logbook.py           # Logbook via MCP
│   ├── parsers.py           # Response parsers
│   ├── constants.py         # MCP constants
│   ├── workarounds.py       # MCP workarounds
│   └── base.py              # Base MCP client
├── sandbox/                 # gVisor sandbox runner
│   ├── runner.py            # Sandbox execution
│   ├── artifact_validator.py # Validate sandbox artifacts
│   └── policies.py          # Sandbox security policies
├── scheduler/               # APScheduler for cron/webhook triggers
│   └── service.py           # Scheduler service
├── schema/                  # YAML schema validation
│   ├── core.py              # SchemaRegistry, validate_yaml
│   ├── semantic.py          # SemanticValidator (live HA state checks)
│   └── ha/                  # HA-specific schemas
│       ├── automation.py    # Automation schema
│       ├── script.py        # Script schema
│       ├── scene.py         # Scene schema
│       ├── dashboard.py     # Dashboard schema
│       ├── registry_cache.py # Registry cache
│       └── common.py        # Shared types
├── storage/                 # SQLAlchemy models and database
│   ├── models.py            # Base model, engine, session
│   ├── checkpoints.py       # LangGraph checkpointing
│   ├── artifact_store.py    # Artifact storage
│   └── entities/            # 21+ domain models
│       ├── agent.py         # Agent, AgentConfigVersion, AgentPromptVersion
│       ├── analysis_report.py # AnalysisReport
│       ├── area.py          # Area
│       ├── automation_proposal.py # AutomationProposal
│       ├── conversation.py  # Conversation, Message
│       ├── device.py        # Device
│       ├── discovery_session.py # DiscoverySession
│       ├── flow_grade.py    # FlowGrade
│       ├── ha_entity.py     # HAEntity
│       ├── ha_zone.py       # HAZone
│       ├── insight.py       # Insight
│       ├── insight_schedule.py # InsightSchedule
│       ├── llm_usage.py     # LLMUsage
│       ├── model_rating.py  # ModelRating
│       ├── passkey.py       # PasskeyCredential
│       ├── registry.py      # HAAutomation, Scene, Script, Service
│       ├── system_config.py # SystemConfig
│       └── user_profile.py  # UserProfile
├── tools/                   # Agent tool definitions
│   ├── agent_tools.py       # Core agent tools
│   ├── ha_tools.py          # HA entity/service tools
│   ├── diagnostic_tools.py  # Diagnostic tools
│   ├── review_tools.py      # Config review tools
│   ├── dashboard_tools.py   # Dashboard generation tools
│   ├── analysis_tools.py    # Analysis tools for DS team
│   ├── approval_tools.py    # HITL approval tools
│   ├── specialist_tools.py  # DS team specialist delegation
│   ├── insight_schedule_tools.py # Insight schedule tools
│   └── report_lifecycle.py  # Analysis report lifecycle helpers
├── tracing/                 # MLflow observability
│   ├── mlflow.py            # Tracing setup and utilities
│   ├── scorers.py           # Custom MLflow 3.x scorers
│   └── context.py           # Session correlation context
├── exceptions.py            # Centralized exception hierarchy
├── llm.py                   # Legacy LLM entry point
├── llm_call_context.py      # LLM call context
├── llm_pricing.py           # Legacy pricing (see llm/usage.py)
├── settings.py              # Pydantic settings (env vars)
└── logging_config.py        # Structured logging (structlog)

ui/
├── src/
│   ├── pages/               # React pages
│   │   ├── agents/          # Agent configuration (model, prompt, history)
│   │   ├── architecture/    # Agent topology visualization
│   │   ├── chat/            # Chat (input, messages, model picker, sidebar)
│   │   ├── dashboard/       # System overview dashboard
│   │   ├── dashboard-editor/ # Lovelace dashboard editor
│   │   ├── entities/        # Entity browser
│   │   ├── insights/        # Insights browser
│   │   ├── login/           # Authentication
│   │   ├── model-registry/  # Model registry and ratings
│   │   ├── proposals/       # Automation proposals
│   │   ├── registry/        # HA registry (automations, scripts, scenes)
│   │   ├── reports/         # Analysis reports
│   │   ├── schedules/       # Insight schedules
│   │   ├── settings/        # Application settings
│   │   ├── usage/           # LLM usage tracking
│   │   └── webhooks/        # Webhook management
│   ├── components/          # Reusable UI components
│   │   ├── chat/            # Chat-specific (markdown, thinking, agent activity)
│   │   └── ui/              # Base components (button, card, badge, etc.)
│   ├── api/                 # API client and React Query hooks
│   ├── contexts/            # React contexts (auth)
│   ├── hooks/               # Custom hooks
│   ├── layouts/             # App layout with sidebar navigation
│   └── lib/                 # Utilities, types, storage helpers
└── vite.config.ts           # Vite configuration

tests/
├── unit/                    # Unit tests (mocked dependencies)
├── integration/             # Integration tests (real PostgreSQL via testcontainers)
└── e2e/                     # End-to-end tests

infrastructure/
├── gvisor/
│   └── config.toml          # gVisor configuration
├── podman/
│   ├── compose.yaml         # Podman Compose (PostgreSQL, MLflow, app, UI)
│   ├── Containerfile        # API container image
│   ├── Containerfile.ui     # UI container image
│   ├── Containerfile.sandbox # Data science sandbox image
│   └── nginx.conf           # Nginx config for production
├── postgres/
│   └── init.sql             # Database initialization
└── test/
    └── docker-compose.test.yaml  # Test infrastructure
```

---

## See Also

- [Contributing](../CONTRIBUTING.md) — coding standards and branch strategy
- [Architecture](architecture.md) — system design
- [Configuration](configuration.md) — environment variables
