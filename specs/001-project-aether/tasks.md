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

## Phase 2: Foundational (Blocking Prerequisites) ✅

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

- [x] T023 Create src/cli/__init__.py with CLI app setup using Typer
- [x] T024 Create src/cli/main.py with CLI entry point and base commands (serve, discover, chat)

### Sandbox Infrastructure (Constitution: Isolation)

- [x] T025 Create src/sandbox/__init__.py with sandbox runner imports
- [x] T026 Create src/sandbox/policies.py with gVisor security policies (no network, read-only mounts, timeout)
- [x] T027 Create src/sandbox/runner.py with Podman + runsc script execution

### Test Infrastructure (Constitution: Reliability & Quality)

- [x] T029 Configure pytest in pyproject.toml with pytest-cov, pytest-asyncio, pytest-mock
- [x] T030 [P] Create tests/conftest.py with shared fixtures (async db, mock MCP client, test settings)
- [x] T031 [P] Create tests/factories.py with factory_boy factories for all models
- [x] T032 [P] Create tests/mocks/__init__.py with MCP response mocks and HA state fixtures
- [x] T033 [P] Create infrastructure/test/docker-compose.test.yaml for integration test environment
- [x] T034 [P] Configure pre-commit hooks in .pre-commit-config.yaml (ruff, ruff-format, mypy)
- [x] T035 Create tests/integration/conftest.py with testcontainers setup for PostgreSQL
- [x] T036 Create .github/workflows/ci.yaml with test pipeline using uv (uv sync --frozen → unit → integration → E2E → coverage)

**Checkpoint**: Foundation ready - user story implementation can now begin ✅

---

## Phase 3: User Story 1 - Discover and Abstract Home Assistant Entities (Priority: P1) 🎯 MVP

**Goal**: Librarian agent discovers HA entities and abstracts them into a queryable DAL

**Independent Test**: Connect to HA, run discovery, verify entities are stored and queryable via natural language

**MCP Tools Used**: `system_overview`, `list_entities`, `get_entity`, `domain_summary_tool`, `list_automations`

### Models for User Story 1

- [x] T028 [P] [US1] Create Entity model in src/storage/models.py per data-model.md (full schema with device_id, area_id, platform, device_class, supported_features, labels placeholder)
- [x] T029 [P] [US1] Create Area model in src/storage/models.py (id, ha_area_id, name, floor_id=null) - **Workaround: floor_id nullable until MCP supports floors**
- [x] T030 [P] [US1] Create Device model in src/storage/models.py (id, ha_device_id, name, area_id) - **Workaround: manufacturer/model/firmware null until MCP supports devices**
- [x] T031 [P] [US1] Create DiscoverySession model in src/storage/models.py (expanded with devices_found, areas_found, services_found counts)
- [x] T032 [P] [US1] Create HAAutomation model in src/storage/models.py per data-model.md (synced from HA via list_automations)
- [x] T033 [P] [US1] Create Script model in src/storage/models.py (entity_id FK, sequence=null) - **Workaround: sequence null until MCP supports script config**
- [x] T034 [P] [US1] Create Scene model in src/storage/models.py (entity_id FK, entity_states=null) - **Workaround: entity_states null until MCP supports scene config**
- [x] T035 [P] [US1] Create Service model in src/storage/models.py (domain, service, fields) - **Workaround: seed common services, expand as discovered**
- [x] T036 [US1] Create Alembic migration for all US1 models in alembic/versions/002_ha_registry.py

### DAL Layer for User Story 1

- [x] T037 [US1] Create src/dal/__init__.py with DAL public interface
- [x] T038 [US1] Create src/dal/entities.py with Entity CRUD operations and caching
- [x] T039 [US1] Create src/dal/devices.py with Device CRUD - **Workaround: infer device_id from entity attributes**
- [x] T040 [US1] Create src/dal/areas.py with Area CRUD - **Workaround: extract unique area_ids from entities**
- [x] T041 [US1] Create src/dal/automations.py with HAAutomation, Script, Scene CRUD
- [x] T042 [US1] Create src/dal/services.py with Service registry - **Workaround: seed common services from constants**
- [x] T043 [US1] Create src/dal/queries.py with natural language query interface using LLM
- [x] T044 [US1] Create src/dal/sync.py with HA synchronization orchestration

### MCP Integration Layer for User Story 1

- [x] T045 [US1] Create src/mcp/__init__.py with MCP client wrapper interface
- [x] T046 [US1] Create src/mcp/client.py with hass-mcp tool invocation helpers
- [x] T047 [US1] Create src/mcp/parsers.py with response parsers for system_overview, list_entities, get_entity
- [x] T048 [US1] Create src/mcp/workarounds.py with device/area inference from entity attributes
- [x] T049 [US1] Create src/mcp/constants.py with common services seed data (light.turn_on, switch.toggle, etc.)

### Librarian Agent for User Story 1

- [x] T050 [US1] Create src/agents/__init__.py with agent base class and MLflow tracing
- [x] T051 [US1] Create src/agents/librarian.py with entity discovery workflow using MCP layer
- [x] T052 [US1] Create src/graph/nodes.py with Librarian graph nodes (discover, infer_devices, infer_areas, sync_automations, persist)
- [x] T053 [US1] Create src/graph/workflows.py with discovery workflow using StateGraph

### API Endpoints for User Story 1

- [x] T054 [P] [US1] Create entity schemas in src/api/schemas/entities.py (Entity, EntityList, EntityQuery, EntityQueryResult)
- [x] T055 [P] [US1] Create device schemas in src/api/schemas/devices.py (Device, DeviceList)
- [x] T056 [P] [US1] Create area schemas in src/api/schemas/areas.py (Area, AreaList)
- [x] T057 [P] [US1] Create automation schemas in src/api/schemas/ha_automations.py (HAAutomation, Script, Scene lists)
- [x] T058 [US1] Create src/api/routes/entities.py with GET /entities, GET /entities/{id}, POST /entities/query, POST /entities/sync
- [x] T059 [US1] Create src/api/routes/devices.py with GET /devices, GET /devices/{id}
- [x] T060 [US1] Create src/api/routes/areas.py with GET /areas, GET /areas/{id}
- [x] T061 [US1] Create src/api/routes/ha_registry.py with GET /automations, /scripts, /scenes, /services

### CLI Commands for User Story 1

- [x] T062 [US1] Add `aether discover` command in src/cli/main.py to trigger Librarian discovery
- [x] T063 [US1] Add `aether entities list/query/show` commands in src/cli/main.py
- [x] T064 [US1] Add `aether devices list/show` commands in src/cli/main.py
- [x] T065 [US1] Add `aether areas list/show` commands in src/cli/main.py
- [x] T066 [US1] Add `aether automations/scripts/scenes/services list` commands in src/cli/main.py

### MCP Gap Tracking for User Story 1

- [x] T067 [US1] Create src/mcp/gaps.py with MCP capability gap tracker (log missing features with context)
- [x] T068 [US1] Add gap reporting to DiscoverySession (mcp_gaps_encountered JSONB field)
- [x] T069 [US1] Create `aether mcp-gaps report` CLI command to show what MCP enhancements would help

### Tests for User Story 1 (Constitution: Reliability & Quality)

**Unit Tests**:
- [x] T070 [P] [US1] Create tests/unit/test_dal_entities.py - Entity CRUD, caching logic
- [x] T071 [P] [US1] Create tests/unit/test_dal_devices.py - Device inference from attributes
- [x] T072 [P] [US1] Create tests/unit/test_dal_areas.py - Area extraction logic
- [x] T073 [P] [US1] Create tests/unit/test_dal_queries.py - NL query parsing (mock LLM)
- [x] T074 [P] [US1] Create tests/unit/test_mcp_parsers.py - Response parsing logic
- [x] T075 [P] [US1] Create tests/unit/test_mcp_workarounds.py - Device/area inference
- [x] T076 [P] [US1] Create tests/unit/test_librarian.py - Agent logic with mocked MCP

**Integration Tests**:
- [x] T077 [US1] Create tests/integration/test_dal_db.py - DAL against real PostgreSQL (commit: 1821985)
- [x] T078 [US1] Create tests/integration/test_discovery_workflow.py - LangGraph workflow with mocked MCP (commit: 1821985)
- [x] T079 [US1] Create tests/integration/test_api_entities.py - FastAPI routes with TestClient

**E2E Tests**:
- [x] T080 [US1] Create tests/e2e/test_discovery_flow.py - Full discovery with mock HA
- [x] T081 [US1] Create tests/e2e/test_entity_query.py - NL query end-to-end (commit: 1821985)

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

- [x] T070 [P] [US2] Create Conversation model in src/storage/models.py (id, agent_id, user_id, title, status, context, created_at, updated_at) (commit: 1011c15)
- [x] T071 [P] [US2] Create Message model in src/storage/models.py (id, conversation_id, role, content, tool_calls, tool_results, tokens_used, latency_ms, mlflow_span_id) (commit: 1011c15)
- [x] T072 [P] [US2] Create AutomationProposal model in src/storage/models.py per data-model.md (with HITL state machine) (commit: 1011c15)
- [x] T073 [US2] Create Alembic migration for Conversation, Message, AutomationProposal tables in alembic/versions/003_conversations.py (commit: 1011c15)

### Storage Layer for User Story 2

- [x] T074 [US2] Create src/dal/conversations.py with conversation and message CRUD operations (commit: 5d20225)

### Architect Agent for User Story 2

- [x] T075 [US2] Create src/agents/architect.py with conversational automation design using OpenAI Responses API (commit: 1e0e233)
- [x] T076 [US2] Create src/agents/developer.py with automation deployment to HA via call_service_tool (commit: 1e0e233)
- [x] T077 [US2] Add Architect and Developer nodes to src/graph/nodes.py (propose, refine, approve_gate, deploy, rollback) (commit: 1e0e233)
- [x] T078 [US2] Add conversation workflow to src/graph/workflows.py with HITL interrupt_before at approval gate (commit: 1e0e233)
- [x] T141 [US2] Extend Architect context retrieval in src/agents/architect.py to include entities/devices/areas/services from DAL (structured prompt context)
- [x] T142 [US2] Add MCP query capability to Architect via src/tools/ha_tools.py tool binding (tool-calling with safety guards)

### HITL Approval Flow (Constitution: Safety First)

- [x] T079 [US2] Create ApprovalState in src/graph/state.py with proposal, user_decision, timestamp (commit: 86faa4b)
- [x] T080 [US2] Implement LangGraph interrupt_before for HITL approval in src/graph/workflows.py (commit: 1e0e233)

### Automation Deployment via MCP

- [x] T081 [US2] Create src/mcp/automation_deploy.py with automation YAML generation (commit: f6c2224)
- [x] T082 [US2] Implement deployment via `call_service_tool` to `automation.reload` after file creation (commit: f6c2224)
- [x] T083 [US2] **Workaround**: Store automation YAML locally, use HA config reload - **Note: Direct automation creation requires HA REST API or file access** (commit: f6c2224)

### API Endpoints for User Story 2

- [x] T084 [P] [US2] Create conversation schemas in src/api/schemas/conversations.py (Conversation, ConversationCreate, Message, MessageCreate) (commit: 4a2b7e9)
- [x] T085 [P] [US2] Create proposal schemas in src/api/schemas/proposals.py (AutomationProposal, ApprovalRequest, RejectionRequest) (commit: 4a2b7e9)
- [x] T086 [US2] Create src/api/routes/chat.py with GET/POST /conversations, GET /conversations/{id}, POST /conversations/{id}/messages (commit: 4a2b7e9)
- [x] T087 [US2] Add WebSocket endpoint for streaming at /conversations/{id}/stream in src/api/routes/chat.py (commit: 4a2b7e9)
- [x] T088 [US2] Create src/api/routes/proposals.py with GET /proposals, GET /proposals/{id}, POST approve/reject/deploy/rollback (commit: 4a2b7e9)

### CLI Commands for User Story 2

- [x] T089 [US2] Add `aether chat` interactive command in src/cli/main.py (commit: 78c484a)
- [x] T090 [US2] Add `aether proposals list/approve/reject/rollback` commands in src/cli/main.py (commit: 78c484a)

### Tests for User Story 2 (Constitution: Reliability & Quality)

**Unit Tests**:
- [x] T091 [P] [US2] Create tests/unit/test_storage_conversations.py - Conversation/Message CRUD (commit: cd7ac6e)
- [x] T092 [P] [US2] Create tests/unit/test_architect_agent.py - Proposal generation (mock LLM) (commit: cd7ac6e)
- [x] T093 [P] [US2] Create tests/unit/test_developer_agent.py - Deployment logic (mock MCP) (commit: cd7ac6e)
- [x] T094 [P] [US2] Create tests/unit/test_approval_state.py - HITL state machine transitions (commit: cd7ac6e)
- [x] T095 [P] [US2] Create tests/unit/test_automation_yaml.py - YAML generation validation (commit: cd7ac6e)
- [x] T143 [P] [US2] Create tests/unit/test_architect_tools.py - Architect HA tool usage + context retrieval

**Integration Tests**:
- [x] T096 [US2] Create tests/integration/test_conversation_workflow.py - Full conversation flow with mocks
- [x] T097 [US2] Create tests/integration/test_hitl_interrupt.py - LangGraph interrupt_before behavior
- [x] T098 [US2] Create tests/integration/test_api_chat.py - Chat API with WebSocket

**E2E Tests**:
- [x] T099 [US2] Create tests/e2e/test_automation_design.py - Full conversation → proposal → approval
- [x] T100 [US2] Create tests/e2e/test_automation_rollback.py - Deploy and rollback flow

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

- [x] T091 [P] [US3] Create Insight model in src/storage/entities/insight.py per data-model.md (id, type, title, description, evidence, confidence, impact, entities, script_path, script_output, status, mlflow_run_id)
- [x] T092 [US3] Create Alembic migration for Insight table in alembic/versions/004_insights.py
- [x] T145 [US3] Fix Insight migration schema to match data-model.md (drop/recreate insights table)
- [x] T166 [P] [US3] Create src/dal/insights.py with InsightRepository (CRUD operations for Insight model) (commit: 1fa43ee)

### Data Collection via MCP for User Story 3

- [x] T093 [US3] Create src/mcp/history.py with energy-specific history aggregation (get_history exists in client.py; add filtering by device_class=energy, sum/average calculations) (commit: 7168ae4)
- [ ] T094 [US3] Create src/dal/energy.py with energy data aggregation from history (covered by T093 - EnergyHistoryClient)
- [x] T095 [US3] Implement energy sensor discovery (device_class=energy, unit_of_measurement=kWh/W) (commit: 7168ae4)

### Data Scientist Agent for User Story 3

- [x] T096 [US3] Create src/agents/data_scientist.py with energy analysis and visualization generation (commit: 1ff949e)
- [x] T097 [US3] Add Data Scientist nodes to src/graph/nodes.py (collect_data, generate_script, execute_sandbox, extract_insights) (commit: 0923353)
- [x] T098 [US3] Add analysis workflow to src/graph/workflows.py (commit: 24a1340)
- [x] T167 [US3] Export DataScientistAgent from src/agents/__init__.py (pattern: Librarian/Architect) (commit: 9be9609)
- [x] T168 [US3] Add trace_span integration to Data Scientist agent (Constitution: Observability - use BaseAgent.trace_span()) (commit: 1ff949e)
- [x] T169 [US3] Add session_context to analysis workflow entry point (multi-agent trace correlation per T158-T165) (commit: 24a1340)

### Sandbox Execution (Constitution: Isolation)

- [x] T099 [US3] Create sandbox container image with pandas, numpy, matplotlib, scipy in infrastructure/podman/Containerfile.sandbox and update SandboxRunner.DEFAULT_IMAGE (commit: c0a8314)
- [x] T100 [US3] Implement sandboxed script execution in src/sandbox/runner.py using Podman + runsc
- [x] T101 [US3] Add script output capture and insight extraction in src/agents/data_scientist.py (commit: 1ff949e)

### API Endpoints for User Story 3

- [x] T102 [P] [US3] Create insight schemas in src/api/schemas/insights.py (Insight, InsightList, AnalysisRequest, AnalysisJob) (commit: 10a9f7a)
- [x] T103 [US3] Create src/api/routes/insights.py with GET /insights, GET /insights/{id}, POST /insights/analyze (commit: a3e543a)

### CLI Commands for User Story 3

- [x] T104 [US3] Add `aether analyze energy --days N` command in src/cli/main.py (commit: 401405c)
- [x] T105 [US3] Add `aether insights list/show` commands in src/cli/main.py (commit: 401405c)

### Tests for User Story 3 (Constitution: Reliability & Quality)

**Unit Tests**:
- [x] T106 [P] [US3] Create tests/unit/test_mcp_history.py - History data parsing (commit: 7168ae4)
- [ ] T107 [P] [US3] Create tests/unit/test_dal_energy.py - Energy aggregation logic (covered by T106)
- [x] T108 [P] [US3] Create tests/unit/test_data_scientist.py - Script generation (mock LLM) (commit: 4cdf017)
- [x] T109 [P] [US3] Create tests/unit/test_sandbox_runner.py - Sandbox execution logic (mock Podman) (commit: c0a8314)
- [x] T110 [P] [US3] Create tests/unit/test_insight_extraction.py - Output parsing (commit: 27b7c12)

**Integration Tests**:
- [x] T111 [US3] Create tests/integration/test_analysis_workflow.py - Full analysis pipeline with mocks (commit: 0b36dde)
- [x] T112 [US3] Create tests/integration/test_sandbox_isolation.py - Verify gVisor policies enforced
- [x] T113 [US3] Create tests/integration/test_api_insights.py - Insights API (commit: 81a022c)

**E2E Tests**:
- [x] T114 [US3] Create tests/e2e/test_energy_analysis.py - Full analysis with containerized sandbox

**Checkpoint**: User Story 3 complete - energy analysis with sandboxed script execution working

**MCP Gap Report (Expected)**:
- ✅ `get_history` sufficient for historical data (hours parameter works)
- ⚠️ Long-term history (>7 days) may require HA recorder database access
- ⚠️ Real-time streaming requires `subscribe_events` MCP tool

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Documentation & Deployment

- [ ] T124 [P] Create README.md with project overview, setup instructions, and usage examples
- [ ] T125 [P] Create systemd unit files for production deployment in infrastructure/systemd/
- [ ] T126 Run quickstart.md validation to ensure all setup steps work
- [x] T144 [P] Add scripts/mlflow_local.sh and Makefile targets for local MLflow (mlflow, mlflow-up) with separate aether_mlflow DB

### Error Handling & Observability

- [ ] T127 [P] Add comprehensive error handling across all API routes in src/api/routes/
- [ ] T128 [P] Add request/response logging middleware in src/api/main.py
- [ ] T129 Add MLflow experiment dashboard configuration for agent tracing
- [x] T146 Add MLflow GenAI spans across all agent invocations (BaseAgent + Librarian)
- [x] T147 Add deep MLflow spans for Librarian and Developer steps (fetch, sync, deploy)
- [x] T148 Add trace sessions + span events for multi-agent workflows
- [x] T149 Log conversation message payloads to MLflow traces/artifacts
- [x] T150 Apply mlflow.trace across agents/tools/workflows for auto capture
- [x] T151 [P] Refactor src/tracing/__init__.py to use lazy imports via __getattr__ pattern
- [x] T152 [P] Add enable_autolog() to src/tracing/mlflow.py for MLflow openai/langchain auto-tracing
- [x] T153 Fix trace_with_uri() decorator to create actual MLflow spans (was only initializing)
- [x] T154 [P] Create src/tracing/context.py with session ID context management (start_session, get_session_id)
- [x] T155 Add session_id attribute to AetherTracer and BaseAgent.trace_span() for trace correlation
- [x] T156 [P] Add @trace_with_uri decorators to MCPClient methods (list_entities, get_entity, call_service, etc.)
- [x] T157 Enhance BaseAgent.log_conversation() to capture tool_calls and token_usage
- [x] T158 Add session.start() call at workflow entry points (run_discovery_workflow, run_conversation_workflow)
- [x] T159 [P] Create src/logging_config.py with centralized logging and noisy logger suppression (commit: 9c9a7bc)
- [x] T160 Add mlflow.trace.session metadata via update_current_trace() for multi-turn grouping (commit: 282e225)
- [x] T161 Use conversation_id as session ID in trace_span for consistent correlation (commit: 282e225)
- [x] T162 [P] Add span inputs/outputs capture (set_inputs, set_outputs) to BaseAgent.trace_span (commit: 282e225)
- [x] T163 Update CLI chat command with session_context and conversation_id sync (commit: bee6a4e)
- [x] T164 Add MLflow tracing to CLI discover command with librarian_discovery run (commit: b1a0124)
- [x] T165 Document tracing architecture in constitution.md (v1.4.0) and spec docs (commit: d03a1f9)

### Entity Sync & Caching

- [ ] T130 Add background task for periodic entity sync (every 5 minutes) in src/api/main.py
- [ ] T131 Performance optimization: add Redis caching layer for entity queries in src/dal/entities.py
- [ ] T132 **Future**: Implement real-time sync via `subscribe_events` when MCP supports it
- [ ] T170 [P] Implement _sync_automation_entities in src/dal/sync.py (currently stub) - track HA automations/scripts/scenes
- [ ] T171 Add change detection events to DiscoverySyncService (emit events on entity add/update/remove)
- [ ] T172 Create src/dal/automations.py with AutomationRepository for tracking HA automation changes

### Multi-Agent Communication (Cross-Cutting) — Rescoped

See [features/08-C-model-routing-multi-agent/](features/08-C-model-routing-multi-agent/) for full spec and implementation. (Feature complete: 2026-02-07)

- [x] T173 ~~Create AgentCoordinator~~ → **Cancelled**: Tool-delegation pattern + model context handles coordination without a dedicated class
- [x] T174 ~~handoff_to_architect() tool~~ → **Replaced**: Insight `automation_suggestion` pattern in DataScientistAgent + agent_tools.py formatters (lighter, no new agent)
- [x] T175 ~~query_data_scientist() tool~~ → **Already done**: `analyze_energy`/`diagnose_issue` tools in agent_tools.py serve this purpose
- [x] T176 ~~Agent message queue~~ → **Cancelled**: Single-user system doesn't need async messaging; structured tool returns suffice
- [x] T177 Inter-agent tracing: parent_span_id propagation via ModelContext in src/agents/model_context.py

### Sandbox Environment (US3)

- [x] T178 [P] Create infrastructure/podman/Containerfile.sandbox with data science stack:
  - pandas, numpy, matplotlib, scipy, scikit-learn, statsmodels, seaborn (commit: c0a8314)
- [x] T179 Update SandboxRunner.DEFAULT_IMAGE to use custom data science image (commit: c0a8314)
- [x] T180 Add tests/unit/test_sandbox_packages.py to verify required packages available in sandbox

### Additional Tests (Robust Coverage)

- [x] T181 [P] Create tests/unit/test_dal_insights.py - InsightRepository CRUD operations (commit: 1fa43ee)
- [ ] T182 Create tests/unit/test_inter_agent_comm.py - Agent handoff and message passing
- [ ] T183 Create tests/integration/test_librarian_sync.py - Full entity sync with change detection
- [ ] T184 Create tests/integration/test_data_scientist_architect.py - Multi-agent insight→automation flow
- [ ] T185 Create tests/e2e/test_sandbox_security.py - Verify network isolation, filesystem restrictions

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
Phase 1 (Setup) ✅ ────────────────────────────────┐
                                                    │
Phase 2 (Foundational) ✅ ◄────────────────────────┘
         │
         │ BLOCKS ALL USER STORIES
         ▼
    ┌────┴────┬────────────┐
    ▼         ▼            ▼
Phase 3    Phase 4     Phase 5
  (US1)      (US2)       (US3)
   MVP ✅     ✅           ✅
    │         │            │
    └────┬────┘            │
         │                 │
         └────┬────────────┘
              ▼
    ┌──────────────────────────────────┐
    │  New features tracked in         │
    │  features/<name>/ directories    │
    │  (see Feature Implementation     │
    │   Transition below)              │
    └──────────────────────────────────┘
              │
              ▼
Phase 7 (Polish) ──── Cross-cutting, stays here
              │
              ▼
Phase 8 (Optimization) ──── Continuous, stays here
```

### Completed User Story Dependencies

- **User Story 1 (P1)**: ✅ Complete — Entity discovery with DAL
- **User Story 2 (P2)**: ✅ Complete — Conversational Architect with HITL approval
- **User Story 3 (P3)**: ✅ Complete — Energy analysis with sandboxed execution

### Within Each User Story

- Models → Migrations → MCP Integration → DAL → Agents → Graph nodes → API routes → CLI commands
- Each story independently completable and testable

---

## Summary (Completed Phases)

| Phase | Tasks | Story | Status |
|-------|-------|-------|--------|
| Phase 1: Setup | T001-T008 | — | ✅ Complete |
| Phase 2: Foundational | T009-T035 | — | ✅ Complete |
| Phase 3: US1 (MVP) | T036-T081 | US1 | ✅ Complete |
| Phase 4: US2 | T082-T100 | US2 | ✅ Complete |
| Phase 5: US3 | T101-T114 | US3 | ✅ Complete |
| Phase 7: Polish | T124-T185 | — | Ongoing (cross-cutting) |
| Phase 8: Optimization | T186-T210 | — | Ongoing (continuous) |

New features are tracked individually in `features/` — see transition note below.

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

---

## Phase 8: Code Optimization & Architecture Health

**Purpose**: Continuous improvement of codebase quality, performance, and maintainability. This phase runs in parallel with feature development and should be revisited regularly.

**Review Cadence**: Architecture review every 2 weeks or after major feature completion.

### Immediate Priority (Sprint 1) ✅

- [x] T186 [P] Fix thread-safety in singleton patterns (src/storage/__init__.py, src/mcp/client.py) - add threading.Lock for concurrent initialization (double-checked locking)
- [x] T187 [P] Replace deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` across codebase (~50 instances in 27 files: src/agents/, src/graph/, src/storage/, src/dal/, src/mcp/, src/sandbox/, src/tracing/, src/api/, tests/)
- [x] T188 [P] Add rate limiting middleware to expensive API endpoints using slowapi: discovery (5/min), chat (10/min), analyze (5/min), deploy/rollback (5/min) in src/api/rate_limit.py
- [x] T189 [P] Escape special characters in DAL search queries (src/dal/entities.py, src/dal/services.py) to prevent ILIKE wildcard injection via _escape_ilike() helper

### Short-term Priority (Sprint 2-3)

- [ ] T190 Fix N+1 query pattern in Architect entity context building (src/agents/architect.py _get_entity_context) - batch domain queries
- [ ] T191 [P] Add database indexes for frequently queried columns:
  - Composite index on HAEntity(domain, state)
  - Index on Message(conversation_id, created_at)
  - Index on AutomationProposal(status, created_at)
- [ ] T192 [P] Add pg_trgm extension and GIN index for full-text entity search in src/dal/entities.py
- [ ] T193 Improve type annotations - replace `Any` with specific types for session parameters across DAL and agent modules
- [ ] T194 [P] Optimize MessageRepository.get_last_n() - remove subquery, use simpler desc().limit().reverse() pattern
- [ ] T195 Refactor duplicate workflow code in ArchitectWorkflow (start_conversation/continue_conversation) into shared helper

### Medium-term Priority (Sprint 4+)

- [ ] T196 Implement connection pooling strategy for SandboxRunner - consider warm container pool for frequent analysis
- [ ] T197 Add streaming/pagination for MCP list_entities to reduce memory usage on large HA instances
- [ ] T198 [P] Add request/response sanitization for MLflow logging - hash or redact sensitive message content
- [ ] T199 Implement consistent LLM instance caching strategy across agents (get_llm vs get_default_llm)
- [ ] T200 Add comprehensive edge case tests:
  - Concurrent conversation updates
  - MCP client connection failures and retry logic
  - Sandbox timeout handling
  - Large entity list pagination

### Architecture Review Checklist (Recurring)

**Run this checklist every 2 weeks or after completing a major feature.**

**Full healthcheck document**: [`docs/code-healthcheck.md`](../../docs/code-healthcheck.md) — point the AI assistant at this file to run a comprehensive, automated code healthcheck with dynamically updated findings.

The healthcheck covers all items below plus detailed findings, severity ratings, and action items:

- [ ] T201 [RECURRING] Review singleton patterns for thread-safety issues
- [ ] T202 [RECURRING] Audit database queries for N+1 patterns (use SQLAlchemy echo=True in dev)
- [ ] T203 [RECURRING] Check for new TODO/FIXME/HACK comments and create tasks
- [ ] T204 [RECURRING] Review error handling - no bare `except Exception` without logging
- [ ] T205 [RECURRING] Verify type annotations on new code - minimize `Any` usage
- [ ] T206 [RECURRING] Run performance profiling on critical paths (discovery, chat, analyze)
- [ ] T207 [RECURRING] Review MLflow tracing coverage - all agent operations should be traced
- [ ] T208 [RECURRING] Check test coverage on new code - maintain 80%+ overall
- [ ] T209 [RECURRING] Audit dependencies for security updates (uv audit or safety check)
- [ ] T210 [RECURRING] Review API response times and add indexes if queries slow down

**After each healthcheck run**, the assistant updates `docs/code-healthcheck.md` with current findings, so the next run starts from the latest known state rather than rediscovering the same issues.

### Technical Debt Tracking

| ID | Issue | Location | Impact | Status |
|----|-------|----------|--------|--------|
| TD001 | Thread-unsafe singletons | storage/__init__.py, mcp/client.py | High | ✅ Fixed (T186) |
| TD002 | Deprecated datetime.utcnow() | Multiple files | Medium | ✅ Fixed (T187) |
| TD003 | N+1 queries in Architect | agents/architect.py | High | Open |
| TD004 | Missing rate limiting | api/main.py | High | ✅ Fixed (T188) |
| TD005 | Bare exception handling | agents/architect.py:282 | Low | Open |
| TD006 | Incomplete TODO items | cli/main.py:653,691 | Medium | Open |
| TD007 | Missing database indexes | dal/entities.py | Medium | Open |
| TD008 | ILIKE wildcard injection | dal/entities.py, dal/services.py | Medium | ✅ Fixed (T189) |

### Performance Benchmarks (Track Over Time)

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Entity discovery (1000 entities) | <30s | TBD | Measure after T190 |
| NL query response | <500ms | TBD | Requires indexes |
| Chat response (first token) | <2s | TBD | LLM dependent |
| Sandbox script execution | <30s | TBD | Policy enforced |
| API cold start | <5s | TBD | DB connection time |

---

## Feature Implementation Transition

**Effective**: 2026-02-06 | **Constitution**: v1.6.0 (Feature Delivery Standards)

Starting from this date, new features are no longer tracked as phases in this file. Instead, each feature has its own directory under `features/` with dedicated spec, plan, and tasks files. This enables:

- Historical tracing of architecture evolution (each feature's build plan is preserved)
- Independent feature tracking without monolithic task lists
- Clearer ownership and scope boundaries

### Migrated Features

The following uncompleted features were migrated from this file:

| Feature | Original Phase | New Location |
|---------|---------------|--------------|
| Custom Dashboard Generation (US4) | Phase 6 | [`features/01-dashboard-generation/`](./features/01-dashboard-generation/) |
| Intelligent Optimization (US5) | Phase 6b | [`features/03-intelligent-optimization/`](./features/03-intelligent-optimization/) |

### New Features

| Feature | Location | Status |
|---------|----------|--------|
| Diagnostic Collaboration | [`features/02-C-diagnostic-collaboration/`](./features/02-C-diagnostic-collaboration/) | ✅ Complete |
| HA Registry Management | [`features/04-ha-registry-management/`](./features/04-ha-registry-management/) | Planned |
| Calendar & Presence Integration | [`features/05-calendar-presence-integration/`](./features/05-calendar-presence-integration/) | Planned |
| HA Diagnostics & Troubleshooting | [`features/06-C-ha-diagnostics-troubleshooting/`](./features/06-C-ha-diagnostics-troubleshooting/) | ✅ Complete |
| Diagnostics API & CLI | [`features/07-diagnostics-api-cli/`](./features/07-diagnostics-api-cli/) | Planned |

### What Stays in This File

- **Phases 1-5**: Completed phases remain as historical record
- **Phase 7 (Polish)**: Cross-cutting concerns that affect multiple features
- **Phase 8 (Optimization)**: Continuous architecture health tasks
- **MCP Gap Summary**: Shared reference for all features
