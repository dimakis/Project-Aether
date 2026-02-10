# Code Healthcheck

**Purpose**: Living document for assessing codebase health. Point the AI assistant at this file to run a full healthcheck. Each section includes what to check, how to check it, and the findings from the last run.

**How to use**: Tell the assistant: *"Run the code healthcheck at `docs/code-healthcheck.md`"*

**Last run**: 2026-02-10 | **Branch**: `docs/architecture-review` (from `main`) | **Overall**: GOOD

---

## Table of Contents

1. [Deprecated API Usage](#1-deprecated-api-usage)
2. [Error Handling Quality](#2-error-handling-quality)
3. [Type Safety](#3-type-safety)
4. [Thread Safety & Concurrency](#4-thread-safety--concurrency)
5. [Security & Input Validation](#5-security--input-validation)
6. [TODO / FIXME / HACK Audit](#6-todo--fixme--hack-audit)
7. [Test Coverage Mapping](#7-test-coverage-mapping)
8. [Database & Query Health](#8-database--query-health)
9. [Observability Coverage](#9-observability-coverage)
10. [Dependency Health](#10-dependency-health)
11. [API Rate Limiting](#11-api-rate-limiting)
12. [Technical Debt Tracker](#12-technical-debt-tracker)
13. [Performance Benchmarks](#13-performance-benchmarks)

---

## 1. Deprecated API Usage

**What**: Catch deprecated stdlib/library calls before they break on upgrade.

**How to check**:
- Search `src/` for `datetime.utcnow` (deprecated since Python 3.12, use `datetime.now(timezone.utc)`)
- Search `src/` for `datetime.utcfromtimestamp` (same)
- Search for any other deprecated patterns relevant to current dependency versions

### Last Findings

| Status | Pattern | Occurrences | Files |
|--------|---------|-------------|-------|
| PASS | `datetime.utcnow` | 0 | -- |
| PASS | `datetime.utcfromtimestamp` | 0 | -- |

**Task Reference**: T187 (resolved)

---

## 2. Error Handling Quality

**What**: Audit `except Exception` blocks for proper logging, specificity, and no silent swallows.

**How to check**:
- Search `src/` for `except Exception` -- count occurrences per module
- Flag any `except Exception:` (no `as e`) that don't log -- these silently swallow errors
- Flag broad catches that should use specific exception types

### Last Findings

| Module | Logged (`as e`) | Debug-logged | Silent | Total |
|--------|-----------------|--------------|--------|-------|
| `src/tracing/mlflow.py` | 19 | 3 | 3 | 25 |
| `src/tools/ha_tools.py` | 13 | 0 | 0 | 13 |
| `src/agents/__init__.py` | 0 | 12 | 0 | 12 |
| `src/tools/specialist_tools.py` | 8 | 1 | 1 | 10 |
| `src/tools/agent_tools.py` | 3 | 3 | 3 | 9 |
| `src/agents/architect.py` | 7 | 0 | 0 | 7 |
| `src/tools/diagnostic_tools.py` | 4 | 1 | 2 | 7 |
| `src/tools/approval_tools.py` | 4 | 1 | 0 | 5 |
| `src/sandbox/runner.py` | 1 | 1 | 3 | 5 |
| `src/agents/data_scientist.py` | 5 | 0 | 0 | 5 |
| `src/llm.py` | 3 | 1 | 1 | 5 |
| `src/api/routes/diagnostics.py` | 5 | 0 | 0 | 5 |
| `src/agents/behavioral_analyst.py` | 4 | 0 | 0 | 4 |
| `src/scheduler/service.py` | 4 | 0 | 0 | 4 |
| `src/api/routes/ha_registry.py` | 3 | 0 | 0 | 3 |
| `src/api/routes/system.py` | 3 | 0 | 0 | 3 |
| `src/api/routes/traces.py` | 2 | 0 | 1 | 3 |
| `src/api/routes/openai_compat.py` | 1 | 0 | 2 | 3 |
| `src/graph/workflows.py` | 2 | 0 | 1 | 3 |
| `src/ha/base.py` | 3 | 0 | 0 | 3 |
| `src/graph/nodes/analysis.py` | 3 | 0 | 0 | 3 |
| `src/agents/diagnostic_analyst.py` | 3 | 0 | 0 | 3 |
| `src/dal/sync.py` | 3 | 0 | 0 | 3 |
| `src/cli/commands/status.py` | 3 | 0 | 0 | 3 |
| Others (32 modules, 1-2 each) | 45 | 0 | 2 | 47 |
| **TOTAL** | **~157** | **~23** | **~13** | **193** |

**Severity**: OK -- Growth from 112 to 193 is proportional to new features (DS team specialists, diagnostic tools, review tools, dashboard tools, passkey routes). Silent catches remain concentrated in `tracing/mlflow.py` (by design) and defensive fallbacks. The 23 debug-logged catches in `agents/__init__.py` and tool span-ID fallbacks are acceptable patterns.

**Guidance**: Consider adding debug logging to the remaining ~13 silent catches if debugging becomes difficult. The `tracing/mlflow.py` silent catches (return None) are acceptable by design.

**Task Reference**: T204 (partially resolved for `agents/__init__.py`)

---

## 3. Type Safety

**What**: Minimize `Any` usage; ensure public APIs have full type annotations.

**How to check**:
- Count `: Any` annotations per module in `src/`
- Check for functions missing return type annotations
- Run `mypy --strict` and count errors

### Last Findings

| Module | `Any` Count | Notes |
|--------|-------------|-------|
| `src/api/routes/traces.py` | 12 | MLflow trace object handling |
| `src/llm.py` | 7 | Dynamic LLM kwargs |
| `src/agents/__init__.py` | 5 | Base agent generics |
| `src/schema/core.py` | 4 | Schema flexibility |
| `src/tracing/mlflow.py` | 4 | MLflow API flexibility |
| `src/tools/agent_tools.py` | 4 | Tool return types |
| `src/api/routes/agents.py` | 3 | Agent config handling |
| `src/diagnostics/integration_health.py` | 3 | Response parsing |
| `src/diagnostics/entity_health.py` | 3 | Response parsing |
| `src/storage/entities/automation_proposal.py` | 2 | Trigger/action unwrapping |
| `src/agents/synthesis.py` | 2 | Synthesis generics |
| `src/agents/base_analyst.py` | 2 | Base analyst generics |
| `src/ha/logbook.py` | 2 | HA client type |
| Others (21 modules, 1 each) | 21 | Various |
| **TOTAL** | **74** | -- |

**Severity**: IMPROVED -- Down from 87 to 74. `graph/nodes.py` (was 16) and `graph/workflows.py` (was 14) no longer contribute -- the refactoring into `graph/nodes/*.py` sub-modules and type improvements resolved these. `api/routes/traces.py` (12) is the new highest concentration due to MLflow trace object handling.

**Mypy**: `Success: no issues found in 176 source files` (clean pass).

**Ruff**: `All checks passed!` (clean pass).

**Task Reference**: T193, T205

---

## 4. Thread Safety & Concurrency

**What**: Verify singleton patterns use proper async locking for concurrent access.

**How to check**:
- Search for `_instance`, `_engine`, `_session_factory` singleton patterns
- Verify each has `asyncio.Lock` protection
- Check for double-checked locking anti-patterns without locks

### Last Findings

| Singleton | File | Has Lock | Status |
|-----------|------|----------|--------|
| `_engine` / `_session_factory` | `src/storage/__init__.py` | YES (`threading.Lock` + double-checked locking) | PASS |
| `get_ha_client()` | `src/ha/base.py` | YES (`threading.Lock` + double-checked locking) | PASS |
| `_discovery_instance` | `src/api/services/model_discovery.py` | NO (class has internal `asyncio.Lock` but singleton getter unprotected) | WARN |
| `SchedulerService._instance` | `src/scheduler/service.py` | NO (set during startup, no concurrent access expected) | PASS |
| `_app` | `src/api/main.py` | NO (acceptable -- single-threaded startup) | PASS |

**Severity**: WARN -- `_discovery_instance` singleton getter in `model_discovery.py` lacks lock protection. The `ModelDiscovery` class has an internal `asyncio.Lock` for its methods, but the singleton getter itself is not thread-safe. However, it's only accessed during startup, so risk is low.

**Note**: `get_mcp_client()` in previous healthcheck is now `get_ha_client()` in `src/ha/base.py` (Feature 25 rename).

**Task Reference**: T186 (resolved), T201

---

## 5. Security & Input Validation

**What**: Check for injection vectors, unsanitized inputs, and CORS misconfiguration.

**How to check**:
- Search for raw string interpolation in SQL (SQLAlchemy `text()` with f-strings)
- Check ILIKE patterns for proper escaping
- Verify CORS configuration is environment-appropriate
- Check for sensitive data in logs or traces

### Last Findings

| Check | Status | Details |
|-------|--------|---------|
| ILIKE injection (T189) | PASS | `_escape_ilike()` helper exists in `src/dal/entities.py` |
| Raw SQL injection | PASS | All queries use SQLAlchemy ORM / parameterized |
| CORS configuration | PASS | Uses `settings.cors_origins` (env-configurable) |
| MLflow sensitive data | WARN | Message content logged to MLflow traces -- consider T198 |
| API input validation | PASS | Pydantic schemas on all route handlers |
| Security headers | PASS | X-Content-Type-Options, X-Frame-Options, HSTS, CSP, Permissions-Policy |
| Auth fail-closed | PASS | Production fails closed if no auth configured |

**Task Reference**: T189 (resolved), T198 (open)

---

## 6. TODO / FIXME / HACK Audit

**What**: Track open code-level TODOs and ensure they have corresponding task IDs.

**How to check**:
- Search `src/` for `TODO`, `FIXME`, `HACK`, `XXX` comments
- Verify each has a task reference (TXXX) or create one

### Last Findings

| File | Line | Comment | Has Task? |
|------|------|---------|-----------|
| (none) | -- | -- | -- |

**Severity**: PASS -- 0 TODOs remaining in `src/`. Previous TODO in `src/api/routes/ha_registry.py:440` (`TODO(T170)`) has been resolved.

**Task Reference**: T203

---

## 7. Test Coverage Mapping

**What**: Map source modules to test files. Identify untested modules.

**How to check**:
- List all `src/**/*.py` modules (excluding `__init__.py`)
- List all `tests/**/*.py` test files
- Match source modules to test files
- Flag modules with no corresponding tests

### Last Findings

**Source modules**: 154 files (excluding `__init__.py`) | **Test files**: 200 (excluding conftest/factories/mocks) | **Unit tests**: 180+

#### Modules WITH Tests

| Source Module | Test File(s) |
|---------------|-------------|
| `src/agents/architect.py` | `test_architect_agent.py`, `test_architect_tools.py`, `test_architect_prompt.py`, `test_architect_seek_approval.py` |
| `src/agents/data_scientist.py` | `test_data_scientist.py` |
| `src/agents/developer.py` | `test_developer_agent.py`, `test_developer_deploy.py` |
| `src/agents/librarian.py` | `test_librarian.py`, `test_agents_librarian.py` |
| `src/agents/__init__.py` | `test_agent_tracing.py`, `test_agents_init.py`, `test_base_agent_progress.py` |
| `src/agents/base_analyst.py` | `test_base_analyst.py` |
| `src/agents/behavioral_analyst.py` | `test_agents_behavioral_analyst.py`, `test_behavioral_analyst.py` |
| `src/agents/diagnostic_analyst.py` | `test_agents_diagnostic_analyst.py`, `test_diagnostic_analyst.py` |
| `src/agents/energy_analyst.py` | `test_energy_analyst.py` |
| `src/agents/synthesis.py` | `test_synthesis.py` |
| `src/agents/dashboard_designer.py` | `test_dashboard_designer.py` |
| `src/agents/model_context.py` | `test_model_context.py`, `test_model_propagation.py` |
| `src/agents/config_cache.py` | `test_dal_agent_config.py` |
| `src/agents/execution_context.py` | `test_execution_context.py` |
| `src/dal/areas.py` | `test_dal_areas.py` |
| `src/dal/devices.py` | `test_dal_devices.py` |
| `src/dal/entities.py` | `test_dal_entities.py` |
| `src/dal/insights.py` | `test_dal_insights.py` |
| `src/dal/queries.py` | `test_dal_queries.py` |
| `src/dal/conversations.py` | `test_dal_conversations.py`, `test_storage_conversations.py` |
| `src/dal/sync.py` | `test_dal_sync.py`, `test_delta_sync.py` |
| `src/dal/automations.py` | `test_dal_automations.py` |
| `src/dal/services.py` | `test_dal_services.py` |
| `src/dal/flow_grades.py` | `test_dal_flow_grades.py` |
| `src/dal/ha_zones.py` | `test_dal_ha_zones.py` |
| `src/dal/insight_schedules.py` | `test_dal_insight_schedules.py` |
| `src/dal/llm_usage.py` | `test_dal_llm_usage.py` |
| `src/dal/system_config.py` | `test_system_config_dal.py` |
| `src/ha/client.py` | `test_ha_client.py`, `test_ha_url_preference.py` |
| `src/ha/history.py` | `test_mcp_history.py` |
| `src/ha/parsers.py` | `test_mcp_parsers.py` |
| `src/ha/workarounds.py` | `test_mcp_workarounds.py` |
| `src/ha/automation_deploy.py` | `test_automation_yaml.py` |
| `src/ha/base.py` | `test_ha_base.py`, `test_mcp_db_config.py` |
| `src/ha/behavioral.py` | `test_ha_behavioral.py`, `test_behavioral_analysis.py`, `test_ds_behavioral.py` |
| `src/ha/entities.py` | `test_ha_entities.py`, `test_mcp_area_registry.py` |
| `src/ha/automations.py` | `test_ha_automations.py` |
| `src/ha/gaps.py` | `test_ha_gaps.py` |
| `src/ha/logbook.py` | `test_mcp_logbook.py` |
| `src/sandbox/runner.py` | `test_sandbox_runner.py`, `test_sandbox_packages.py` |
| `src/tools/agent_tools.py` | `test_agent_tools.py`, `test_multi_turn_tools.py` |
| `src/tools/ha_tools.py` | `test_ha_tools.py`, `test_ha_tools_db.py` |
| `src/tools/approval_tools.py` | `test_seek_approval_tool.py`, `test_architect_seek_approval.py` |
| `src/tools/diagnostic_tools.py` | `test_diagnostic_tools.py`, `test_mcp_client_diagnostics.py` |
| `src/tools/specialist_tools.py` | `test_specialist_tools.py`, `test_specialist_progress.py` |
| `src/tools/analysis_tools.py` | `test_tools_analysis.py` |
| `src/tools/dashboard_tools.py` | `test_dashboard_tools.py` |
| `src/tools/review_tools.py` | `test_review_tool.py` |
| `src/tools/insight_schedule_tools.py` | `test_tools_insight_schedule.py` |
| `src/storage/entities/insight.py` | `test_insight_model.py`, `test_insight_schemas.py` |
| `src/storage/entities/automation_proposal.py` | `test_approval_state.py`, `test_proposal_model_extension.py` |
| `src/storage/checkpoints.py` | `test_storage_checkpoints.py` |
| `src/storage/__init__.py` | `test_storage_init.py` |
| `src/graph/state.py` | `test_approval_state.py`, `test_team_analysis_state.py`, `test_review_state.py`, `test_dashboard_state.py`, `test_workflow_presets.py` |
| `src/graph/workflows.py` | `test_team_analysis_workflow.py`, `test_review_workflow.py`, `test_dashboard_workflow.py` (+ integration tests) |
| `src/graph/nodes/analysis.py` | `test_graph_nodes_analysis.py` |
| `src/graph/nodes/conversation.py` | `test_graph_nodes_conversation.py` |
| `src/graph/nodes/discovery.py` | `test_graph_nodes_discovery.py` |
| `src/graph/nodes/review.py` | `test_review_nodes.py` |
| `src/llm.py` | `test_llm.py`, `test_llm_resilience.py` |
| `src/llm_pricing.py` | `test_llm_pricing.py` |
| `src/diagnostics/*.py` | `test_config_validator.py`, `test_integration_health.py`, `test_entity_health.py`, `test_error_patterns.py`, `test_log_parser.py` |
| `src/schema/core.py` | `test_schema_core.py` |
| `src/schema/ha/automation.py` | `test_schema_ha_automation.py` |
| `src/schema/ha/common.py` | `test_schema_ha_common.py` |
| `src/schema/ha/dashboard.py` | `test_schema_ha_dashboard.py` |
| `src/schema/ha/script.py` + `scene.py` | `test_schema_ha_script_scene.py` |
| `src/schema/ha/registry_cache.py` | `test_ha_registry_cache.py` |
| `src/schema/semantic.py` | `test_semantic_validator.py` |
| `src/tracing/mlflow.py` | `test_tracing_mlflow.py` |
| `src/tracing/context.py` | `test_tracing_context.py` |
| `src/tracing/scorers.py` | `test_tracing_scorers.py` |
| `src/api/routes/openai_compat.py` | `test_openai_compat.py`, `test_api_openai_compat.py` |
| `src/api/routes/optimization.py` | `test_api_optimization.py`, `test_optimization_flow.py` |
| `src/api/routes/chat.py` | `test_api_chat.py` |
| `src/api/routes/entities.py` | `test_api_entities.py` |
| `src/api/routes/insights.py` | `test_api_insights.py` |
| `src/api/routes/agents.py` | `test_api_agents.py`, `test_api_agents_routes.py` |
| `src/api/routes/proposals.py` | `test_api_proposals.py` |
| `src/api/routes/system.py` | `test_api_system.py` |
| `src/api/routes/traces.py` | `test_api_traces.py` |
| `src/api/routes/ha_registry.py` | `test_api_ha_registry.py`, `test_api_registry.py` |
| `src/api/routes/webhooks.py` | `test_api_webhooks.py`, `test_webhook_entity_registry.py` |
| `src/api/routes/insight_schedules.py` | `test_api_insight_schedules.py` |
| `src/api/routes/areas.py` | `test_api_areas.py` |
| `src/api/routes/devices.py` | `test_api_devices.py` |
| `src/api/routes/passkey.py` | `test_api_passkey.py` |
| `src/api/routes/evaluations.py` | `test_api_evaluations.py` |
| `src/api/routes/flow_grades.py` | `test_api_flow_grades.py` |
| `src/api/routes/ha_zones.py` | `test_api_ha_zones.py` |
| `src/api/routes/diagnostics.py` | `test_diagnostics_api.py` |
| `src/api/routes/auth.py` | `test_api_auth.py`, `test_auth_ha_login.py`, `test_auth_jwt.py`, `test_auth_setup.py` |
| `src/api/routes/model_ratings.py` | `test_model_ratings_api.py` |
| `src/api/routes/usage.py` | `test_usage_api.py` |
| `src/api/main.py` | `test_api_main.py` |
| `src/api/auth.py` | `test_auth_jwt.py`, `test_auth_password_db.py`, `test_auth_passkey.py`, `test_google_oauth.py` |
| `src/api/ha_verify.py` | `test_ha_verify.py` |
| `src/api/metrics.py` | `test_api_metrics.py` |
| `src/scheduler/service.py` | `test_scheduler_service.py`, `test_scheduler_discovery.py` |
| `src/exceptions.py` | `test_exceptions.py` |
| `src/cli/commands/*.py` | `test_cli_analyze.py`, `test_cli_chat.py`, `test_cli_discover.py`, `test_cli_evaluate.py`, `test_cli_list.py`, `test_cli_proposals.py`, `test_cli_serve.py`, `test_cli_status.py` |
| `src/cli/main.py` | `test_cli_main.py` |

#### Modules WITHOUT Dedicated Tests

| Source Module | Risk | Notes |
|---------------|------|-------|
| `src/ha/constants.py` | LOW | Static data |
| `src/ha/diagnostics.py` | LOW | Utility, covered transitively via diagnostic tools |
| `src/sandbox/policies.py` | LOW | Static policy definitions |
| `src/settings.py` | LOW | Pydantic settings (self-validating) |
| `src/logging_config.py` | LOW | Logging setup |
| `src/llm_call_context.py` | LOW | Context utility |
| `src/api/middleware.py` | LOW | Covered via `test_security_headers.py`, `test_api_main.py` |
| `src/api/rate_limit.py` | LOW | Covered transitively |
| `src/api/utils.py` | LOW | Utility functions |
| `src/api/schemas/*.py` | LOW | Pydantic schemas (self-validating), partially covered |
| `src/api/services/model_discovery.py` | LOW | Model listing utility |
| `src/api/routes/activity_stream.py` | MEDIUM | Activity stream endpoint |
| `src/api/routes/workflows.py` | MEDIUM | Workflow presets endpoint |
| `src/cli/utils.py` | LOW | CLI helpers |
| `src/storage/models.py` | LOW | Base model mixins (covered transitively) |
| `src/storage/entities/*.py` (remaining) | LOW | Covered transitively via DAL tests |
| `src/dal/base.py` | LOW | Base repository (covered transitively) |

**Severity**: GOOD -- Major improvement since last healthcheck. `src/dal/sync.py` (previously HIGH risk, untested) now has `test_dal_sync.py` and `test_delta_sync.py`. `src/dal/automations.py` and `src/dal/services.py` now have dedicated tests. Remaining untested modules are low-risk (static data, utilities, self-validating schemas).

**Task Reference**: T136 (resolved), T208 (resolved for dal/sync.py)

---

## 8. Database & Query Health

**What**: Check for missing indexes, N+1 patterns, and slow query potential.

**How to check**:
- Review SQLAlchemy models for missing indexes on FK/query columns
- Search for query patterns inside loops (N+1)
- Check for `selectinload` / `joinedload` usage on relationships

### Last Findings

| Check | Status | Details |
|-------|--------|---------|
| N+1 in Architect entity context | PASS | Refactored to use `list_by_domains()` batch query (T190 resolved) |
| Index on `HAEntity(domain, state)` | PASS | `ix_ha_entities_domain_state` already exists |
| Index on `Message(conversation_id, created_at)` | PASS | `ix_messages_conversation_created` added (migration 006) |
| Index on `AutomationProposal(status, created_at)` | PASS | `ix_proposals_status_created` added (migration 006) |
| `pg_trgm` GIN index for search | MISSING | Full-text entity search (T192) |
| `MessageRepository.get_last_n()` subquery | WARN | Could use simpler pattern (T194) |
| Relationship eager loading | OK | No obvious missing eager loads |
| Migration count | OK | 25 migrations, all additive, clean patterns |

**Severity**: OK -- Critical indexes added. Remaining items are optimization opportunities.

**Task Reference**: T190 (resolved), T191 (resolved), T192, T194

---

## 9. Observability Coverage

**What**: Verify all agent operations, workflows, and HA client calls are traced via MLflow.

**How to check**:
- Search for `trace_span`, `@trace_with_uri`, `mlflow.trace` usage across agents and HA client
- Verify all agent classes extend `BaseAgent` (which provides tracing)
- Check that workflow entry points call `session_context()`

### Last Findings

| Component | Traced | Method |
|-----------|--------|--------|
| `ArchitectAgent` | YES | `BaseAgent.trace_span()` |
| `LibrarianAgent` | YES | `BaseAgent.trace_span()` |
| `DeveloperAgent` | YES | `BaseAgent.trace_span()` |
| `DataScientistAgent` | YES | `BaseAgent.trace_span()` + `parent_span_id` from `ModelContext` |
| `EnergyAnalyst` | YES | `BaseAgent.trace_span()` via `BaseAnalyst` |
| `BehavioralAnalyst` | YES | `BaseAgent.trace_span()` via `BaseAnalyst` |
| `DiagnosticAnalyst` | YES | `BaseAgent.trace_span()` via `BaseAnalyst` |
| `DashboardDesignerAgent` | YES | `BaseAgent.trace_span()` |
| `HAClient` methods | YES | `@trace_with_uri` decorators |
| Discovery workflow | YES | `session_context()` at entry |
| Conversation workflow | YES | `session_context()` at entry |
| Analysis workflow | YES | `session_context()` at entry |
| Team analysis workflow | YES | `session_context()` at entry |
| Review workflow | YES | `session_context()` at entry |
| Dashboard workflow | YES | `session_context()` at entry |
| Inter-agent delegation | YES | `model_context()` carries `parent_span_id` for parent-child linking |
| CLI commands | PARTIAL | `discover` traced, `chat` traced, others not |
| API routes | NO | No per-request tracing middleware |

**Severity**: OK -- All agent operations and workflows fully traced. Inter-agent trace linking via `ModelContext.parent_span_id` works for same-context delegation. API route-level tracing is a nice-to-have (T128).

**Note**: For the Jarvis pivot, Orchestrator will need explicit spans for intent classification and routing decisions. See `docs/architecture-review.md` Section 7.

**Task Reference**: T207, T128

---

## 10. Dependency Health

**What**: Check for outdated/vulnerable dependencies.

**How to check**:
- Run `uv pip audit` or `pip-audit` for known CVEs
- Run `uv lock --check` to verify lockfile is current
- Review `pyproject.toml` minimum versions against latest releases

### Last Findings

| Check | Status | Details |
|-------|--------|---------|
| Known CVEs | RUN MANUALLY | `uv pip audit` -- requires network |
| Lockfile sync | RUN MANUALLY | `uv lock --check` -- requires network |
| Minimum versions | OK | All min versions are recent (2024-2025 era) |

**Note**: Dependency audit requires network access. Run manually with:
```bash
uv pip audit
uv lock --check
```

**Task Reference**: T209

---

## 11. API Rate Limiting

**What**: Verify expensive endpoints have rate limiting applied.

**How to check**:
- Check that `slowapi` limiter is configured in `src/api/main.py`
- Search for `@limiter.limit()` decorators on expensive routes
- Verify limits are appropriate for each endpoint type

### Last Findings

| Check | Status | Details |
|-------|--------|---------|
| Limiter configured | PASS | `slowapi.Limiter` in `src/api/rate_limit.py` with 60/min default |
| Limiter added to app | PASS | `app.state.limiter` and `RateLimitExceeded` handler registered in `main.py` |
| `POST /v1/chat/completions` | PASS | `@limiter.limit("10/minute")` |
| `POST /chat` | PASS | `@limiter.limit("10/minute")` |
| `POST /chat/stream` | PASS | `@limiter.limit("10/minute")` |
| `POST /proposals/{id}/deploy` | PASS | `@limiter.limit("5/minute")` |
| `POST /proposals/{id}/rollback` | PASS | `@limiter.limit("5/minute")` |
| `POST /proposals/{id}/approve` | PASS | `@limiter.limit("10/minute")` |
| `POST /proposals/from-suggestion` | PASS | `@limiter.limit("5/minute")` |
| `POST /proposals` | PASS | `@limiter.limit("5/minute")` |
| `POST /optimization/run` | PASS | `@limiter.limit("5/minute")` |
| `POST /optimization/analyze` | PASS | `@limiter.limit("10/minute")` |
| `POST /optimization/energy` | PASS | `@limiter.limit("10/minute")` |
| `POST /insights/analyze` | PASS | `@limiter.limit("5/minute")` |
| `POST /insights` (various) | PASS | `@limiter.limit("10/minute")` x4 |
| `POST /entities/query` | PASS | `@limiter.limit("10/minute")` |
| `POST /entities/sync` | PASS | `@limiter.limit("5/minute")` |
| `POST /webhooks/{schedule_id}` | PASS | `@limiter.limit("30/minute")` |
| `POST /ha-registry/sync` | PASS | `@limiter.limit("5/minute")` |
| `POST /ha-registry/services/call` | PASS | `@limiter.limit("10/minute")` |
| `GET /ha-registry/automations` | PASS | `@limiter.limit("5/minute")` |
| `POST /insight-schedules/trigger` | PASS | `@limiter.limit("5/minute")` |
| `POST /agents/*/prompt/generate` | PASS | `@limiter.limit("10/minute")` |
| `POST /agents/*/promote-all` | PASS | `@limiter.limit("10/minute")` |
| `POST /agents/seed` | PASS | `@limiter.limit("5/minute")` |
| Agent config endpoints | PASS | `@limiter.limit("10/minute")` x2 |

**Severity**: PASS -- 29 rate-limited endpoints across all expensive routes. Coverage expanded since last healthcheck to include agents, insight schedules, and HA registry endpoints.

**Task Reference**: T188 (resolved)

---

## 12. Technical Debt Tracker

**What**: Centralized tracking of known technical debt items.

| ID | Issue | Location | Impact | Status | Task |
|----|-------|----------|--------|--------|------|
| TD001 | Thread-unsafe singletons | `storage/__init__.py`, `ha/base.py` | High | **Resolved** | T186 |
| TD002 | Deprecated `datetime.utcnow()` | Multiple | Medium | **Resolved** | T187 |
| TD003 | N+1 queries in Architect | `agents/architect.py` | High | **Resolved** | T190 |
| TD004 | Rate limiting not applied to routes | `api/routes/*.py` | High | **Resolved** | T188 |
| TD005 | Silent exception handling | ~13 silent catches remaining | Low | **Stable** | T204 |
| TD006 | Dead CLI chat stubs | `cli/main.py` | Medium | **Resolved** | -- |
| TD007 | Missing database indexes | `storage/entities/*.py` | Medium | **Resolved** | T191 |
| TD008 | Missing `sync.py` unit tests | `dal/sync.py` | High | **Resolved** | T183 |
| TD009 | Untracked TODO in ha_registry | `api/routes/ha_registry.py` | Low | **Resolved** | T170 |
| TD010 | `Any` type annotations | 74 annotations (down from 87) | Medium | **Improved** | T193 |
| TD011 | `pg_trgm` GIN index for search | `dal/entities.py` | Low | Open | T192 |
| TD012 | `MessageRepository.get_last_n()` subquery | `dal/conversations.py` | Low | Open | T194 |
| TD013 | Stale `src/mcp/` references in docs | `docs/code-healthcheck.md`, `docs/architecture.md` | Low | **New** | -- |
| TD014 | Feature 23 config not wired to runtime | `agents/`, `tools/__init__.py` | High | **New** | -- |
| TD015 | HITL enforcement is Architect-specific | `agents/architect.py` | High | **New** | -- |
| TD016 | `workflows.py` at 1161 lines | `graph/workflows.py` | Medium | **New** | -- |
| TD017 | `_discovery_instance` singleton unprotected | `api/services/model_discovery.py` | Low | Open | T201 |

---

## 13. Performance Benchmarks

**What**: Track key performance metrics over time. Update after optimization work.

| Metric | Target | Current | Last Measured | Notes |
|--------|--------|---------|---------------|-------|
| Entity discovery (1000 entities) | <30s | TBD | -- | Measure after T190 |
| NL query response | <500ms | TBD | -- | Requires indexes (T191) |
| Chat response (first token) | <2s | TBD | -- | LLM dependent |
| Sandbox script execution | <30s | TBD | -- | Policy enforced |
| API cold start | <5s | TBD | -- | DB connection time |

**How to measure**: Run with timing:
```bash
# Discovery
time aether discover

# Chat (first response)
time curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "architect", "messages": [{"role": "user", "content": "hello"}]}'

# Entity query
time curl -X POST http://localhost:8000/api/v1/entities/query \
  -H "Content-Type: application/json" \
  -d '{"query": "all lights in the living room"}'
```

---

## Healthcheck Run Instructions

When asked to run this healthcheck, follow these steps:

### Step 1: Automated Scans
Run these searches across the codebase and update the findings above:

1. `rg "datetime\.utcnow|datetime\.utcfromtimestamp" src/` -- Deprecated APIs
2. `rg "except Exception" src/` -- Error handling (count per module, flag silent catches)
3. `rg ": Any\b" src/` -- Type safety (count per module)
4. `rg "_instance|_engine|_session_factory" src/` -- Singleton patterns -> check for locks
5. `rg "TODO|FIXME|HACK|XXX" src/` -- Code comments audit
6. `rg "@limiter\.limit" src/` -- Rate limiting coverage
7. Cross-reference `src/**/*.py` modules against `tests/**/*.py` -- Test coverage mapping

### Step 2: Manual / Network-Required Checks
These require running commands with network access:

```bash
# Lint check
uv run ruff check src/ tests/

# Type check
uv run mypy src/

# Dependency security audit
uv pip audit

# Lockfile freshness
uv lock --check

# Test coverage
uv run pytest --cov=src --cov-report=term-missing tests/unit/
```

### Step 3: Update This File
After running checks:

1. Update the "Last run" date and branch at the top
2. Update each section's "Last Findings" tables with current data
3. Add/remove items from the Technical Debt Tracker
4. Update Performance Benchmarks if measurements were taken
5. Commit the updated file: `docs: update code healthcheck results`

### Step 4: Create Action Items
After updating, identify the top 3-5 highest-priority items and propose them as the next sprint's work.

---

## Changelog

| Date | Branch | Run By | Key Changes |
|------|--------|--------|-------------|
| 2026-02-10 | `docs/architecture-review` | Full architecture review | Updated all 13 sections with fresh data. Type safety improved: 74 `Any` (down from 87). Error handling: 193 total (up from 112, proportional to new features). TODOs: 0 remaining. Test coverage: 154 source modules, 200 test files, `dal/sync.py` now tested (TD008 resolved). Added TD013-TD017 for architecture review findings. Stale `src/mcp/` refs noted (TD013). Feature 23 runtime gap flagged (TD014). HITL centralization needed (TD015). |
| 2026-02-07 | `001-project-aether` | Healthcheck run | Updated all 13 sections with fresh data. Error handling: 112 total exceptions (75 logged, 11 debug-logged, 26 silent). Type safety: 87 `Any` annotations (up from 73, +11 in traces.py). Thread safety: `_discovery_instance` singleton getter lacks lock (low risk). Rate limiting: Expanded coverage (14 endpoints). Test coverage: 98 source modules, 71 test files. All other sections verified. |
| 2026-02-07 | `001-project-aether` | Feature update | Added: model context propagation (`src/agents/model_context.py`), per-agent model settings, inter-agent trace linking, automation suggestion reverse communication. Tests: +33 (test_model_context, test_model_propagation, test_insight_suggestions). Feature: `08-C-model-routing-multi-agent`. Updated T173-T177 scope. |
| 2026-02-06 | `001-project-aether` | Post-fix update | Fixed: datetime.utcnow (T187), rate limiting (T188), N+1 query (T190), DB indexes (T191), silent catches in agents/__init__.py, dead CLI stubs (TD006), untracked TODO (TD009). Corrected: thread safety was already PASS (T186). |
| 2026-02-06 | `001-project-aether` | Initial creation | Baseline healthcheck with all sections populated |
