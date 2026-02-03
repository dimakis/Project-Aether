# Tasks: Project Aether

**Input**: Design documents from `/specs/001-project-aether/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Constitution V (Reliability & Quality) requires comprehensive testing. Each phase includes unit, integration, and E2E test tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Infrastructure in `infrastructure/`

---

## MCP Capability Assessment

### Currently Available via `hass-mcp`

| Tool | Use Case | Entities It Populates |
|------|----------|----------------------|
| `system_overview` | Initial discovery, domain counts | Entity (partial), Area (names only) |
| `list_entities` | Core entity listing | Entity |
| `get_entity` | Single entity detail with attributes | Entity (full attributes) |
| `domain_summary_tool` | Statistics per domain | (aggregates) |
| `search_entities_tool` | Search by name/attributes | Entity |
| `list_automations` | Get all automations | HAAutomation |
| `get_history` | State history for analysis | (temporal data) |
| `call_service_tool` | Execute any service | — |
| `entity_action` | Quick on/off/toggle | — |

### Workarounds for Missing Capabilities

| Missing Tool | Workaround | Limitation |
|--------------|------------|------------|
| `list_devices` | Parse `device_id` from entity attributes via `get_entity` | No manufacturer/model/firmware info |
| `list_areas` | Extract unique `area_id` from entities | No floor association, no icons |
| `list_floors` | **None** - skip Floor entity for MVP | Floor hierarchy unavailable |
| `list_labels` | **None** - skip Label entity for MVP | Tagging unavailable |
| `list_categories` | **None** - skip Category entity for MVP | Organization unavailable |
| `list_config_entries` | **None** - skip ConfigEntry for MVP | Integration config unavailable |
| `list_services` | Hard-code common services OR parse from HA docs | Limited service discovery |
| `list_scripts` | Filter entities by `script.*` domain | Missing script sequence details |
| `list_scenes` | Filter entities by `scene.*` domain | Missing entity_states details |

### MCP Enhancement Roadmap

These features would unlock additional capabilities. **Report back when these become blockers.**

| Priority | MCP Feature | Unlocks | Data Model Entities |
|----------|-------------|---------|---------------------|
| **P1** | `list_devices` | Device hierarchy, manufacturer info | Device |
| **P1** | `list_areas` | Proper area registry with floors | Area (full), Floor |
| **P2** | `list_services` | Dynamic service discovery for agents | Service |
| **P2** | `get_script_config` | Script sequence for analysis | Script (full) |
| **P2** | `get_scene_config` | Scene entity states | Scene (full) |
| **P3** | `list_labels` | Entity tagging/grouping | Label |
| **P3** | `list_config_entries` | Integration status monitoring | ConfigEntry, Integration |
| **P3** | `subscribe_events` | Real-time entity updates | Event (stream) |

---

## Phase 1: Setup (Shared Infrastructure) ✅

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure with src/, tests/, infrastructure/ directories per plan.md
- [x] T002 Initialize Python 3.11+ project with pyproject.toml using uv (`uv init` or manual), add dependencies (langgraph, fastapi, sqlalchemy, mlflow, openai, pydantic)
- [x] T003 [P] Configure ruff for linting and formatting in pyproject.toml `[tool.ruff]` section
- [x] T004 [P] Create .env.example with HA_TOKEN, HA_URL, DATABASE_URL, MLFLOW_TRACKING_URI, OPENAI_API_KEY
- [x] T005 [P] Create infrastructure/podman/Containerfile for main application (use `uv sync --frozen` for reproducible installs)
- [x] T006 [P] Create infrastructure/podman/compose.yaml for local dev (app + postgres + mlflow)
- [x] T007 [P] Create infrastructure/gvisor/config.toml for runsc sandbox configuration
- [x] T008 [P] Create infrastructure/postgres/init.sql with database initialization
- [x] T009 [P] Generate uv.lock file with `uv lock` and commit to repo for reproducible builds

**Checkpoint**: Project skeleton ready for development ✅

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database & Models

- [x] T009 Create src/storage/__init__.py with database connection setup (asyncpg + SQLAlchemy async)
- [x] T010 Create src/storage/models.py with base SQLAlchemy model and common mixins
- [x] T011 [P] Create Alembic migration configuration in alembic.ini and alembic/env.py
- [x] T012 Create initial migration with Agent table in alembic/versions/001_initial.py

### LangGraph Infrastructure

- [x] T013 Create src/graph/__init__.py with LangGraph imports and configuration
- [x] T014 Create src/graph/state.py with base state definitions using Pydantic models
- [x] T015 Create src/storage/checkpoints.py with PostgreSQL checkpointer for LangGraph

### MLflow Tracing (Constitution: Observability)

- [x] T016 Create src/tracing/__init__.py with MLflow client initialization
- [x] T017 Create src/tracing/mlflow.py with experiment setup and tracing decorators

### API Framework

- [x] T018 Create src/api/__init__.py with FastAPI app factory
- [x] T019 Create src/api/main.py with FastAPI application, CORS, and middleware
- [x] T020 [P] Create src/api/routes/__init__.py with router registration
- [x] T021 [P] Create src/api/schemas/__init__.py with common Pydantic schemas (Error, HealthStatus, SystemStatus)
- [x] T022 Create health check endpoints GET /api/v1/health and GET /api/v1/status in src/api/routes/system.py

### CLI Framework

- [ ] T023 Create src/cli/__init__.py with CLI app setup using Typer
- [ ] T024 Create src/cli/main.py with CLI entry point and base commands (serve, discover, chat)

### Sandbox Infrastructure (Constitution: Isolation)

- [ ] T025 Create src/sandbox/__init__.py with sandbox runner imports
- [ ] T026 Create src/sandbox/policies.py with gVisor security policies (no network, read-only mounts, timeout)
- [ ] T027 Create src/sandbox/runner.py with Podman + runsc script execution

### Test Infrastructure (Constitution: Reliability & Quality)

- [ ] T029 Configure pytest in pyproject.toml with pytest-cov, pytest-asyncio, pytest-mock
- [ ] T030 [P] Create tests/conftest.py with shared fixtures (async db, mock MCP client, test settings)
- [ ] T031 [P] Create tests/factories.py with factory_boy factories for all models
- [ ] T032 [P] Create tests/mocks/__init__.py with MCP response mocks and HA state fixtures
- [ ] T033 [P] Create infrastructure/test/docker-compose.test.yaml for integration test environment
- [ ] T034 [P] Configure pre-commit hooks in .pre-commit-config.yaml (ruff, ruff-format, mypy)
- [ ] T035 Create tests/integration/conftest.py with testcontainers setup for PostgreSQL
- [ ] T036 Create .github/workflows/ci.yaml with test pipeline using uv (uv sync --frozen → unit → integration → E2E → coverage)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Discover and Abstract Home Assistant Entities (Priority: P1) 🎯 MVP

**Goal**: Librarian agent discovers HA entities and abstracts them into a queryable DAL

**Independent Test**: Connect to HA, run discovery, verify entities are stored and queryable via natural language

**MCP Tools Used**: `system_overview`, `list_entities`, `get_entity`, `domain_summary_tool`, `list_automations`

### Models for User Story 1

- [ ] T028 [P] [US1] Create Entity model in src/storage/models.py per data-model.md (full schema with device_id, area_id, platform, device_class, supported_features, labels placeholder)
- [ ] T029 [P] [US1] Create Area model in src/storage/models.py (id, ha_area_id, name, floor_id=null) - **Workaround: floor_id nullable until MCP supports floors**
- [ ] T030 [P] [US1] Create Device model in src/storage/models.py (id, ha_device_id, name, area_id) - **Workaround: manufacturer/model/firmware null until MCP supports devices**
- [ ] T031 [P] [US1] Create DiscoverySession model in src/storage/models.py (expanded with devices_found, areas_found, services_found counts)
- [ ] T032 [P] [US1] Create HAAutomation model in src/storage/models.py per data-model.md (synced from HA via list_automations)
- [ ] T033 [P] [US1] Create Script model in src/storage/models.py (entity_id FK, sequence=null) - **Workaround: sequence null until MCP supports script config**
- [ ] T034 [P] [US1] Create Scene model in src/storage/models.py (entity_id FK, entity_states=null) - **Workaround: entity_states null until MCP supports scene config**
- [ ] T035 [P] [US1] Create Service model in src/storage/models.py (domain, service, fields) - **Workaround: seed common services, expand as discovered**
- [ ] T036 [US1] Create Alembic migration for all US1 models in alembic/versions/002_ha_registry.py

### DAL Layer for User Story 1

- [ ] T037 [US1] Create src/dal/__init__.py with DAL public interface
- [ ] T038 [US1] Create src/dal/entities.py with Entity CRUD operations and caching
- [ ] T039 [US1] Create src/dal/devices.py with Device CRUD - **Workaround: infer device_id from entity attributes**
- [ ] T040 [US1] Create src/dal/areas.py with Area CRUD - **Workaround: extract unique area_ids from entities**
- [ ] T041 [US1] Create src/dal/automations.py with HAAutomation, Script, Scene CRUD
- [ ] T042 [US1] Create src/dal/services.py with Service registry - **Workaround: seed common services from constants**
- [ ] T043 [US1] Create src/dal/queries.py with natural language query interface using LLM
- [ ] T044 [US1] Create src/dal/sync.py with HA synchronization orchestration

### MCP Integration Layer for User Story 1

- [ ] T045 [US1] Create src/mcp/__init__.py with MCP client wrapper interface
- [ ] T046 [US1] Create src/mcp/client.py with hass-mcp tool invocation helpers
- [ ] T047 [US1] Create src/mcp/parsers.py with response parsers for system_overview, list_entities, get_entity
- [ ] T048 [US1] Create src/mcp/workarounds.py with device/area inference from entity attributes
- [ ] T049 [US1] Create src/mcp/constants.py with common services seed data (light.turn_on, switch.toggle, etc.)

### Librarian Agent for User Story 1

- [ ] T050 [US1] Create src/agents/__init__.py with agent base class and MLflow tracing
- [ ] T051 [US1] Create src/agents/librarian.py with entity discovery workflow using MCP layer
- [ ] T052 [US1] Create src/graph/nodes.py with Librarian graph nodes (discover, infer_devices, infer_areas, sync_automations, persist)
- [ ] T053 [US1] Create src/graph/workflows.py with discovery workflow using StateGraph

### API Endpoints for User Story 1

- [ ] T054 [P] [US1] Create entity schemas in src/api/schemas/entities.py (Entity, EntityList, EntityQuery, EntityQueryResult)
- [ ] T055 [P] [US1] Create device schemas in src/api/schemas/devices.py (Device, DeviceList)
- [ ] T056 [P] [US1] Create area schemas in src/api/schemas/areas.py (Area, AreaList)
- [ ] T057 [P] [US1] Create automation schemas in src/api/schemas/ha_automations.py (HAAutomation, Script, Scene lists)
- [ ] T058 [US1] Create src/api/routes/entities.py with GET /entities, GET /entities/{id}, POST /entities/query, POST /entities/sync
- [ ] T059 [US1] Create src/api/routes/devices.py with GET /devices, GET /devices/{id}
- [ ] T060 [US1] Create src/api/routes/areas.py with GET /areas, GET /areas/{id}
- [ ] T061 [US1] Create src/api/routes/ha_registry.py with GET /automations, /scripts, /scenes, /services

### CLI Commands for User Story 1

- [ ] T062 [US1] Add `aether discover` command in src/cli/main.py to trigger Librarian discovery
- [ ] T063 [US1] Add `aether entities list/query/show` commands in src/cli/main.py
- [ ] T064 [US1] Add `aether devices list/show` commands in src/cli/main.py
- [ ] T065 [US1] Add `aether areas list/show` commands in src/cli/main.py
- [ ] T066 [US1] Add `aether automations/scripts/scenes/services list` commands in src/cli/main.py

### MCP Gap Tracking for User Story 1

- [ ] T067 [US1] Create src/mcp/gaps.py with MCP capability gap tracker (log missing features with context)
- [ ] T068 [US1] Add gap reporting to DiscoverySession (mcp_gaps_encountered JSONB field)
- [ ] T069 [US1] Create `aether mcp-gaps report` CLI command to show what MCP enhancements would help

### Tests for User Story 1 (Constitution: Reliability & Quality)

**Unit Tests**:
- [ ] T070 [P] [US1] Create tests/unit/test_dal_entities.py - Entity CRUD, caching logic
- [ ] T071 [P] [US1] Create tests/unit/test_dal_devices.py - Device inference from attributes
- [ ] T072 [P] [US1] Create tests/unit/test_dal_areas.py - Area extraction logic
- [ ] T073 [P] [US1] Create tests/unit/test_dal_queries.py - NL query parsing (mock LLM)
- [ ] T074 [P] [US1] Create tests/unit/test_mcp_parsers.py - Response parsing logic
- [ ] T075 [P] [US1] Create tests/unit/test_mcp_workarounds.py - Device/area inference
- [ ] T076 [P] [US1] Create tests/unit/test_librarian.py - Agent logic with mocked MCP

**Integration Tests**:
- [ ] T077 [US1] Create tests/integration/test_dal_db.py - DAL against real PostgreSQL
- [ ] T078 [US1] Create tests/integration/test_discovery_workflow.py - LangGraph workflow with mocked MCP
- [ ] T079 [US1] Create tests/integration/test_api_entities.py - FastAPI routes with TestClient

**E2E Tests**:
- [ ] T080 [US1] Create tests/e2e/test_discovery_flow.py - Full discovery with mock HA
- [ ] T081 [US1] Create tests/e2e/test_entity_query.py - NL query end-to-end

**Checkpoint**: User Story 1 complete - entities discoverable, stored, and queryable via NL

**MCP Gap Report (Expected)**:
- ⚠️ Device manufacturer/model requires `list_devices` MCP tool
- ⚠️ Floor hierarchy requires `list_floors` MCP tool  
- ⚠️ Script sequences require `get_script_config` MCP tool
- ⚠️ Scene entity states require `get_scene_config` MCP tool
- ⚠️ Full service discovery requires `list_services` MCP tool

---

## Phase 4: User Story 2 - Conversational Design with Architect Agent (Priority: P2)

**Goal**: Chat with Architect agent to design automations with HITL approval

**Independent Test**: Start conversation, describe automation need, receive proposal, approve/reject, verify deployment to HA

**MCP Tools Used**: `call_service_tool` (for deployment), `entity_action`, `list_entities` (context for proposals)

### Models for User Story 2

- [ ] T070 [P] [US2] Create Conversation model in src/storage/models.py (id, agent_id, user_id, title, status, context, created_at, updated_at)
- [ ] T071 [P] [US2] Create Message model in src/storage/models.py (id, conversation_id, role, content, tool_calls, tool_results, tokens_used, latency_ms, mlflow_span_id)
- [ ] T072 [P] [US2] Create AutomationProposal model in src/storage/models.py per data-model.md (with HITL state machine)
- [ ] T073 [US2] Create Alembic migration for Conversation, Message, AutomationProposal tables in alembic/versions/003_conversations.py

### Storage Layer for User Story 2

- [ ] T074 [US2] Create src/storage/conversations.py with conversation and message CRUD operations

### Architect Agent for User Story 2

- [ ] T075 [US2] Create src/agents/architect.py with conversational automation design using OpenAI Responses API
- [ ] T076 [US2] Create src/agents/developer.py with automation deployment to HA via call_service_tool
- [ ] T077 [US2] Add Architect and Developer nodes to src/graph/nodes.py (propose, refine, approve_gate, deploy, rollback)
- [ ] T078 [US2] Add conversation workflow to src/graph/workflows.py with HITL interrupt_before at approval gate

### HITL Approval Flow (Constitution: Safety First)

- [ ] T079 [US2] Create ApprovalState in src/graph/state.py with proposal, user_decision, timestamp
- [ ] T080 [US2] Implement LangGraph interrupt_before for HITL approval in src/graph/workflows.py

### Automation Deployment via MCP

- [ ] T081 [US2] Create src/mcp/automation_deploy.py with automation YAML generation
- [ ] T082 [US2] Implement deployment via `call_service_tool` to `automation.reload` after file creation
- [ ] T083 [US2] **Workaround**: Store automation YAML locally, use HA config reload - **Note: Direct automation creation requires HA REST API or file access**

### API Endpoints for User Story 2

- [ ] T084 [P] [US2] Create conversation schemas in src/api/schemas/conversations.py (Conversation, ConversationCreate, Message, MessageCreate)
- [ ] T085 [P] [US2] Create proposal schemas in src/api/schemas/proposals.py (AutomationProposal, ApprovalRequest, RejectionRequest)
- [ ] T086 [US2] Create src/api/routes/chat.py with GET/POST /conversations, GET /conversations/{id}, POST /conversations/{id}/messages
- [ ] T087 [US2] Add WebSocket endpoint for streaming at /conversations/{id}/stream in src/api/routes/chat.py
- [ ] T088 [US2] Create src/api/routes/proposals.py with GET /proposals, GET /proposals/{id}, POST approve/reject/deploy/rollback

### CLI Commands for User Story 2

- [ ] T089 [US2] Add `aether chat` interactive command in src/cli/main.py
- [ ] T090 [US2] Add `aether proposals list/approve/reject/rollback` commands in src/cli/main.py

### Tests for User Story 2 (Constitution: Reliability & Quality)

**Unit Tests**:
- [ ] T091 [P] [US2] Create tests/unit/test_storage_conversations.py - Conversation/Message CRUD
- [ ] T092 [P] [US2] Create tests/unit/test_architect_agent.py - Proposal generation (mock LLM)
- [ ] T093 [P] [US2] Create tests/unit/test_developer_agent.py - Deployment logic (mock MCP)
- [ ] T094 [P] [US2] Create tests/unit/test_approval_state.py - HITL state machine transitions
- [ ] T095 [P] [US2] Create tests/unit/test_automation_yaml.py - YAML generation validation

**Integration Tests**:
- [ ] T096 [US2] Create tests/integration/test_conversation_workflow.py - Full conversation flow with mocks
- [ ] T097 [US2] Create tests/integration/test_hitl_interrupt.py - LangGraph interrupt_before behavior
- [ ] T098 [US2] Create tests/integration/test_api_chat.py - Chat API with WebSocket

**E2E Tests**:
- [ ] T099 [US2] Create tests/e2e/test_automation_design.py - Full conversation → proposal → approval
- [ ] T100 [US2] Create tests/e2e/test_automation_rollback.py - Deploy and rollback flow

**Checkpoint**: User Story 2 complete - conversational automation design with HITL approval working

**MCP Gap Report (Expected)**:
- ⚠️ Direct automation creation requires REST API or `create_automation` MCP tool
- ⚠️ Automation enable/disable requires `automation.turn_on/off` via call_service_tool (available)

---

## Phase 5: User Story 3 - Energy Optimization Suggestions (Priority: P3)

**Goal**: Data Scientist agent analyzes energy data and generates optimization insights in gVisor sandbox

**Independent Test**: Provide 7 days of energy data, trigger analysis, receive optimization suggestions with projected savings

**MCP Tools Used**: `get_history` (for energy data), `list_entities` (find energy sensors), `domain_summary_tool`

### Models for User Story 3

- [ ] T091 [P] [US3] Create Insight model in src/storage/models.py per data-model.md (id, type, title, description, evidence, confidence, impact, entities, script_path, script_output, status, mlflow_run_id)
- [ ] T092 [US3] Create Alembic migration for Insight table in alembic/versions/004_insights.py

### Data Collection via MCP for User Story 3

- [ ] T093 [US3] Create src/mcp/history.py with get_history wrapper for energy sensors
- [ ] T094 [US3] Create src/dal/energy.py with energy data aggregation from history
- [ ] T095 [US3] Implement energy sensor discovery (device_class=energy, unit_of_measurement=kWh/W)

### Data Scientist Agent for User Story 3

- [ ] T096 [US3] Create src/agents/data_scientist.py with energy analysis and visualization generation
- [ ] T097 [US3] Add Data Scientist nodes to src/graph/nodes.py (collect_data, generate_script, execute_sandbox, extract_insights)
- [ ] T098 [US3] Add analysis workflow to src/graph/workflows.py

### Sandbox Execution (Constitution: Isolation)

- [ ] T099 [US3] Create sandbox container image with pandas, numpy, matplotlib in infrastructure/podman/Containerfile.sandbox
- [ ] T100 [US3] Implement sandboxed script execution in src/sandbox/runner.py using Podman + runsc
- [ ] T101 [US3] Add script output capture and insight extraction in src/agents/data_scientist.py

### API Endpoints for User Story 3

- [ ] T102 [P] [US3] Create insight schemas in src/api/schemas/insights.py (Insight, InsightList, AnalysisRequest, AnalysisJob)
- [ ] T103 [US3] Create src/api/routes/insights.py with GET /insights, GET /insights/{id}, POST /insights/analyze

### CLI Commands for User Story 3

- [ ] T104 [US3] Add `aether analyze energy --days N` command in src/cli/main.py
- [ ] T105 [US3] Add `aether insights list/show` commands in src/cli/main.py

### Tests for User Story 3 (Constitution: Reliability & Quality)

**Unit Tests**:
- [ ] T106 [P] [US3] Create tests/unit/test_mcp_history.py - History data parsing
- [ ] T107 [P] [US3] Create tests/unit/test_dal_energy.py - Energy aggregation logic
- [ ] T108 [P] [US3] Create tests/unit/test_data_scientist.py - Script generation (mock LLM)
- [ ] T109 [P] [US3] Create tests/unit/test_sandbox_runner.py - Sandbox execution logic (mock Podman)
- [ ] T110 [P] [US3] Create tests/unit/test_insight_extraction.py - Output parsing

**Integration Tests**:
- [ ] T111 [US3] Create tests/integration/test_analysis_workflow.py - Full analysis pipeline with mocks
- [ ] T112 [US3] Create tests/integration/test_sandbox_isolation.py - Verify gVisor policies enforced
- [ ] T113 [US3] Create tests/integration/test_api_insights.py - Insights API

**E2E Tests**:
- [ ] T114 [US3] Create tests/e2e/test_energy_analysis.py - Full analysis with containerized sandbox

**Checkpoint**: User Story 3 complete - energy analysis with sandboxed script execution working

**MCP Gap Report (Expected)**:
- ✅ `get_history` sufficient for historical data (hours parameter works)
- ⚠️ Long-term history (>7 days) may require HA recorder database access
- ⚠️ Real-time streaming requires `subscribe_events` MCP tool

---

## Phase 6: User Story 4 - Custom Dashboard Generation (Priority: P4)

**Goal**: Generate and deploy custom Home Assistant dashboards based on preferences and usage

**Independent Test**: Request themed dashboard, receive Lovelace configuration, deploy to HA

**MCP Tools Used**: `list_entities` (find entities for cards), `domain_summary_tool` (layout planning)

### Models for User Story 4

- [ ] T106 [P] [US4] Create Dashboard model in src/storage/models.py per data-model.md (id, conversation_id, name, description, theme, layout, entities, status, ha_dashboard_id, deployed_at)
- [ ] T107 [US4] Create Alembic migration for Dashboard table in alembic/versions/005_dashboards.py

### Dashboard Generation for User Story 4

- [ ] T108 [US4] Create src/agents/dashboard.py with Lovelace YAML generation using entity context
- [ ] T109 [US4] Create src/dal/dashboards.py with Dashboard CRUD and Lovelace validation
- [ ] T110 [US4] **Workaround**: Generate dashboard YAML for manual import OR use HA storage API if available

### Dashboard Deployment

- [ ] T111 [US4] Create src/mcp/dashboard_deploy.py with deployment strategy selection
- [ ] T112 [US4] Implement "export" mode: generate downloadable YAML for user import
- [ ] T113 [US4] **Note**: Direct dashboard deployment requires HA Lovelace WebSocket API (not in current MCP)

### API Endpoints for User Story 4

- [ ] T114 [P] [US4] Create dashboard schemas in src/api/schemas/dashboards.py (Dashboard, DashboardList, DashboardExport)
- [ ] T115 [US4] Create src/api/routes/dashboards.py with GET /dashboards, GET /dashboards/{id}, GET /dashboards/{id}/export, POST /dashboards/{id}/deploy

### CLI Commands for User Story 4

- [ ] T116 [US4] Add `aether dashboards list/show/export` commands in src/cli/main.py
- [ ] T117 [US4] Add `aether dashboards generate` command with theme/area options

### Tests for User Story 4 (Constitution: Reliability & Quality)

**Unit Tests**:
- [ ] T118 [P] [US4] Create tests/unit/test_dashboard_generator.py - Lovelace YAML generation
- [ ] T119 [P] [US4] Create tests/unit/test_dal_dashboards.py - Dashboard CRUD
- [ ] T120 [P] [US4] Create tests/unit/test_lovelace_validation.py - YAML schema validation

**Integration Tests**:
- [ ] T121 [US4] Create tests/integration/test_dashboard_workflow.py - Generation pipeline
- [ ] T122 [US4] Create tests/integration/test_api_dashboards.py - Dashboard API

**E2E Tests**:
- [ ] T123 [US4] Create tests/e2e/test_dashboard_generation.py - Full generation and export

**Checkpoint**: User Story 4 complete - dashboard generation and export working

**MCP Gap Report (Expected)**:
- ⚠️ Direct dashboard deployment requires `lovelace/config` WebSocket API
- ⚠️ Dashboard preview requires HA frontend access
- ✅ Export mode works without additional MCP features

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Documentation & Deployment

- [ ] T124 [P] Create README.md with project overview, setup instructions, and usage examples
- [ ] T125 [P] Create systemd unit files for production deployment in infrastructure/systemd/
- [ ] T126 Run quickstart.md validation to ensure all setup steps work

### Error Handling & Observability

- [ ] T127 [P] Add comprehensive error handling across all API routes in src/api/routes/
- [ ] T128 [P] Add request/response logging middleware in src/api/main.py
- [ ] T129 Add MLflow experiment dashboard configuration for agent tracing

### Entity Sync & Caching

- [ ] T130 Add background task for periodic entity sync (every 5 minutes) in src/api/main.py
- [ ] T131 Performance optimization: add Redis caching layer for entity queries in src/dal/entities.py
- [ ] T132 **Future**: Implement real-time sync via `subscribe_events` when MCP supports it

### MCP Gap Summary Report

- [ ] T133 Create comprehensive MCP gap analysis document at docs/mcp-gaps.md
- [ ] T134 Add `aether mcp-status` command showing current capabilities and gaps
- [ ] T135 Create MCP extension specification for priority gaps (devices, areas, services)

### Final Quality Gates

- [ ] T136 Achieve 80%+ overall code coverage (95%+ for critical paths)
- [ ] T137 Pass all mypy strict type checks
- [ ] T138 Zero ruff lint warnings
- [ ] T139 All E2E tests passing in CI
- [ ] T140 Performance benchmark: discovery <30s, query response <500ms

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────────────────────────────────┐
                                                  │
Phase 2 (Foundational) ◄──────────────────────────┘
         │
         │ BLOCKS ALL USER STORIES
         ▼
    ┌────┴────┬────────────┬────────────┐
    ▼         ▼            ▼            ▼
Phase 3    Phase 4     Phase 5     Phase 6
  (US1)      (US2)       (US3)       (US4)
   MVP    
    │         │            │            │
    └────┬────┴────────────┴────────────┘
         ▼
Phase 7 (Polish)
```

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 - No dependencies on other stories - **THIS IS THE MVP**
- **User Story 2 (P2)**: Can start after Phase 2 - Benefits from US1 entities but independently testable
- **User Story 3 (P3)**: Can start after Phase 2 - Benefits from US1 entities and US2 Architect
- **User Story 4 (P4)**: Can start after Phase 2 - Benefits from US1/US2/US3 but independently testable

### Within Each User Story

- Models → Migrations → MCP Integration → DAL → Agents → Graph nodes → API routes → CLI commands
- Each story independently completable and testable

### Parallel Opportunities

**Phase 1 (all [P] tasks):**
```bash
T003, T004, T005, T006, T007, T008  # All can run in parallel
```

**Phase 2:**
```bash
T011  # Alembic config (parallel with T016, T018, T023, T025)
T016, T017  # MLflow (parallel)
T020, T021  # API schemas (parallel)
```

**User Stories (after Phase 2):**
```bash
# Can start US1, US2, US3, US4 in parallel if team has capacity
# Within each story, models are parallelizable
T028-T035  # US1 models (parallel)
T070-T072  # US2 models (parallel)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~4 hours)
2. Complete Phase 2: Foundational + Test Infrastructure (~12 hours)
3. Complete Phase 3: User Story 1 + Tests (~20 hours) - includes MCP integration layer
4. **Quality Gate**: 80%+ coverage, all tests green, mypy clean
5. **STOP and VALIDATE**: Test discovery and NL queries
6. **Report MCP Gaps**: Document what additional MCP features would help
7. Deploy/demo the MVP

### Incremental Delivery

1. **MVP**: Setup + Foundational + US1 + Tests → Queryable entity DAL with workarounds
2. **+US2**: Conversational Architect with HITL + Tests → Automation design
3. **+US3**: Data Scientist with sandbox + Tests → Energy insights
4. **+US4**: Dashboard generation + Tests → Complete feature set
5. **Polish**: Production hardening + MCP gap documentation + Final quality gates

### Test-Driven Development

Each user story follows TDD:
1. Write unit tests for new models/DAL
2. Implement models/DAL until tests pass
3. Write integration tests for workflows
4. Implement agents/workflows until tests pass
5. Write E2E tests for critical paths
6. Implement API/CLI until tests pass
7. Verify coverage meets threshold before marking complete

---

## Summary

| Phase | Tasks | Parallel | Story | MCP Tools Used |
|-------|-------|----------|-------|----------------|
| Phase 1: Setup | T001-T008 | 6 | — | — |
| Phase 2: Foundational | T009-T035 | 8 | — | — |
| Phase 3: US1 (MVP) | T036-T081 | 16 | US1 | system_overview, list_entities, get_entity, list_automations |
| Phase 4: US2 | T082-T100 | 7 | US2 | call_service_tool, entity_action |
| Phase 5: US3 | T101-T114 | 6 | US3 | get_history |
| Phase 6: US4 | T115-T123 | 4 | US4 | list_entities, domain_summary_tool |
| Phase 7: Polish | T124-T140 | 6 | — | — |
| **Total** | **140 tasks** | **53 parallel** | — | — |

**MVP Scope**: Phases 1-3 (81 tasks) → Delivers queryable entity discovery with device/area inference + full test coverage

---

## MCP Gap Summary

### What Works Today

| Capability | MCP Tool | Status |
|------------|----------|--------|
| Entity discovery | `list_entities`, `get_entity` | ✅ Full |
| Entity state/attributes | `get_entity` | ✅ Full |
| Domain overview | `domain_summary_tool` | ✅ Full |
| Automation listing | `list_automations` | ✅ Full |
| Historical data | `get_history` | ✅ Full (hours param) |
| Service execution | `call_service_tool` | ✅ Full |
| Entity control | `entity_action` | ✅ Full |

### Workarounds Implemented

| Missing Feature | Workaround | Limitation |
|-----------------|------------|------------|
| Device registry | Infer from entity attributes | No manufacturer/model/firmware |
| Area registry | Extract from entity area_id | No floor hierarchy |
| Service list | Seed common services | Limited discovery |
| Script details | Domain filter entities | No sequence config |
| Scene details | Domain filter entities | No entity_states |

### Future MCP Enhancements (Priority Order)

| Priority | MCP Tool Needed | Unlocks | Impact |
|----------|-----------------|---------|--------|
| **P1** | `list_devices` | Full device hierarchy | High - better entity grouping |
| **P1** | `list_areas` | Floor/area structure | High - spatial context |
| **P2** | `list_services` | Dynamic service discovery | Medium - better agent actions |
| **P2** | `get_script_config` | Script sequence analysis | Medium - automation suggestions |
| **P2** | `get_scene_config` | Scene entity states | Medium - scene recommendations |
| **P3** | `subscribe_events` | Real-time updates | Medium - live dashboard |
| **P3** | `list_floors` | Building hierarchy | Low - spatial organization |
| **P3** | `list_labels` | Custom tagging | Low - user organization |

**Action**: When a workaround becomes a blocker, report with context and the specific MCP tool that would resolve it.
