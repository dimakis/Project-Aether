# Code Healthcheck

**Purpose**: Living document for assessing codebase health. Point the AI assistant at this file to run a full healthcheck. Each section includes what to check, how to check it, and the findings from the last run.

**How to use**: Tell the assistant: *"Run the code healthcheck at `docs/code-healthcheck.md`"*

**Last run**: 2026-02-06 (post-fix) | **Branch**: `001-project-aether` | **Overall**: GOOD

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
| PASS | `datetime.utcnow` | 0 | — (fixed: was 5 in `runner.py`, `state.py`, `schemas/__init__.py`) |
| PASS | `datetime.utcfromtimestamp` | 0 | — |

**Task Reference**: T187 (resolved)

---

## 2. Error Handling Quality

**What**: Audit `except Exception` blocks for proper logging, specificity, and no silent swallows.

**How to check**:
- Search `src/` for `except Exception` — count occurrences per module
- Flag any `except Exception:` (no `as e`) that don't log — these silently swallow errors
- Flag broad catches that should use specific exception types

### Last Findings

| Module | `except Exception as e` (logged) | `except Exception:` (debug-logged) | `except Exception:` (silent) | Total |
|--------|-----------------------------------|-------------------------------------|------------------------------|-------|
| `src/agents/__init__.py` | 1 | 11 | 0 | 12 |
| `src/tracing/mlflow.py` | 10 | 0 | 5 | 15 |
| `src/tools/ha_tools.py` | 12 | 0 | 0 | 12 |
| `src/tools/agent_tools.py` | 4 | 0 | 0 | 4 |
| `src/sandbox/runner.py` | 2 | 0 | 2 | 4 |
| `src/agents/data_scientist.py` | 3 | 0 | 1 | 4 |
| `src/api/routes/system.py` | 3 | 0 | 0 | 3 |
| `src/graph/nodes.py` | 1 | 0 | 1 | 2 |
| `src/cli/main.py` | 6 | 0 | 0 | 6 |
| `src/agents/developer.py` | 1 | 0 | 1 | 2 |
| Other (8 files) | 8 | 0 | 0 | 8 |
| **TOTAL** | **51** | **11** | **10** | **72** |

**Severity**: OK — `src/agents/__init__.py` silent catches now all use `logger.debug()` with `exc_info=True`. Remaining 10 silent catches are in `tracing/mlflow.py` (5, by design), `sandbox/runner.py` (2), and scattered agent code (3) — tracing/observability code where crashes must be suppressed.

**Guidance**: Silent catches in `tracing/mlflow.py` are acceptable by design (tracing should never crash the app). The remaining few in `sandbox/runner.py` and agents should be reviewed if they cause debugging difficulty.

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
| `src/graph/nodes.py` | 16 | Highest — LangGraph state dicts |
| `src/graph/workflows.py` | 14 | LangGraph compiled graph types |
| `src/agents/developer.py` | 7 | MCP response handling |
| `src/tracing/mlflow.py` | 7 | MLflow API flexibility |
| `src/agents/architect.py` | 6 | LLM response parsing |
| `src/agents/data_scientist.py` | 5 | Script output parsing |
| `src/agents/__init__.py` | 5 | Base agent generics |
| `src/dal/queries.py` | 4 | Dynamic query building |
| `src/tools/agent_tools.py` | 3 | Tool return types |
| Other (6 files) | 6 | 1 each |
| **TOTAL** | **73** | — |

**Severity**: WARN — 73 `Any` annotations. `graph/nodes.py` and `graph/workflows.py` account for 30 (LangGraph's loosely-typed interfaces make this partially unavoidable).

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
| `get_mcp_client()` | `src/mcp/client.py` | YES (`threading.Lock` + double-checked locking) | PASS |
| `_discovery_instance` | `src/api/services/model_discovery.py` | YES (`asyncio.Lock`) | PASS |
| `_app` | `src/api/main.py` | NO (acceptable — single-threaded startup) | PASS |

**Severity**: PASS — All singletons with concurrent access are properly protected with locks.

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
| MLflow sensitive data | WARN | Message content logged to MLflow traces — consider T198 |
| API input validation | PASS | Pydantic schemas on all route handlers |

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
| `src/api/routes/ha_registry.py` | 440 | `TODO(T170): Get from last discovery session` | YES |

**Severity**: PASS — 1 TODO, properly tracked. Dead CLI stubs (TD006) removed entirely.

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

**Source modules**: 77 files | **Test files**: 40 (excluding conftest/factories/mocks)

#### Modules WITH Tests

| Source Module | Test File(s) |
|---------------|-------------|
| `src/agents/architect.py` | `test_architect_agent.py`, `test_architect_tools.py` |
| `src/agents/data_scientist.py` | `test_data_scientist.py` |
| `src/agents/developer.py` | `test_developer_agent.py` |
| `src/agents/librarian.py` | `test_librarian.py` |
| `src/agents/__init__.py` | `test_agent_tracing.py` |
| `src/dal/areas.py` | `test_dal_areas.py` |
| `src/dal/devices.py` | `test_dal_devices.py` |
| `src/dal/entities.py` | `test_dal_entities.py` |
| `src/dal/insights.py` | `test_dal_insights.py` |
| `src/dal/queries.py` | `test_dal_queries.py` |
| `src/dal/conversations.py` | `test_storage_conversations.py` |
| `src/mcp/client.py` | `test_mcp_client_automations.py` |
| `src/mcp/history.py` | `test_mcp_history.py` |
| `src/mcp/parsers.py` | `test_mcp_parsers.py` |
| `src/mcp/workarounds.py` | `test_mcp_workarounds.py` |
| `src/mcp/automation_deploy.py` | `test_automation_yaml.py` |
| `src/sandbox/runner.py` | `test_sandbox_runner.py`, `test_sandbox_packages.py` |
| `src/tools/agent_tools.py` | `test_agent_tools.py` |
| `src/tools/ha_tools.py` | `test_ha_tools.py` |
| `src/storage/entities/insight.py` | `test_insight_model.py`, `test_insight_schemas.py` |
| `src/storage/entities/automation_proposal.py` | `test_approval_state.py` |
| `src/graph/state.py` | `test_approval_state.py` (partial) |
| `src/llm.py` | `test_llm.py` |

#### Modules WITHOUT Dedicated Tests

| Source Module | Risk | Notes |
|---------------|------|-------|
| `src/dal/sync.py` | HIGH | Orchestrates HA sync — critical path |
| `src/dal/automations.py` | MEDIUM | Automation repository CRUD |
| `src/dal/services.py` | MEDIUM | Service registry |
| `src/graph/nodes.py` | MEDIUM | Covered via integration/workflow tests |
| `src/graph/workflows.py` | MEDIUM | Covered via integration tests |
| `src/mcp/gaps.py` | LOW | Diagnostic utility |
| `src/mcp/constants.py` | LOW | Static data |
| `src/tracing/mlflow.py` | LOW | Observability (non-critical path) |
| `src/tracing/context.py` | LOW | Session context management |
| `src/settings.py` | LOW | Pydantic settings (self-validating) |
| `src/logging_config.py` | LOW | Logging setup |
| `src/api/routes/*.py` | MEDIUM | Partially covered by integration API tests |
| `src/api/services/model_discovery.py` | LOW | Model listing utility |
| `src/cli/main.py` | MEDIUM | CLI commands — manual testing common |
| `src/sandbox/policies.py` | LOW | Static policy definitions |
| `src/storage/__init__.py` | LOW | DB init (covered transitively) |

**Severity**: WARN — `src/dal/sync.py` is the highest-risk untested module (critical sync path).

**Task Reference**: T136, T208

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

**Severity**: OK — Critical indexes added. Remaining items are optimization opportunities.

**Task Reference**: T190 (resolved), T191 (resolved), T192, T194

---

## 9. Observability Coverage

**What**: Verify all agent operations, workflows, and MCP calls are traced via MLflow.

**How to check**:
- Search for `trace_span`, `@trace_with_uri`, `mlflow.trace` usage across agents and MCP
- Verify all agent classes extend `BaseAgent` (which provides tracing)
- Check that workflow entry points call `session_context()`

### Last Findings

| Component | Traced | Method |
|-----------|--------|--------|
| `ArchitectAgent` | YES | `BaseAgent.trace_span()` |
| `LibrarianAgent` | YES | `BaseAgent.trace_span()` |
| `DeveloperAgent` | YES | `BaseAgent.trace_span()` |
| `DataScientistAgent` | YES | `BaseAgent.trace_span()` |
| `MCPClient` methods | YES | `@trace_with_uri` decorators |
| Discovery workflow | YES | `session_context()` at entry |
| Conversation workflow | YES | `session_context()` at entry |
| Analysis workflow | YES | `session_context()` at entry |
| CLI commands | PARTIAL | `discover` traced, `chat` traced, others not |
| API routes | NO | No per-request tracing middleware |

**Severity**: OK — Core agent operations fully traced. API route-level tracing is a nice-to-have (T128).

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
| Known CVEs | RUN MANUALLY | `uv pip audit` — requires network |
| Lockfile sync | RUN MANUALLY | `uv lock --check` — requires network |
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
| `POST /entities/sync` | PASS | `@limiter.limit("5/minute")` |
| `POST /entities/query` | PASS | `@limiter.limit("10/minute")` |
| `POST /conversations` | PASS | `@limiter.limit("10/minute")` |
| `POST /conversations/{id}/messages` | PASS | `@limiter.limit("10/minute")` |
| `POST /insights/analyze` | PASS | `@limiter.limit("5/minute")` |
| `POST /proposals/{id}/deploy` | PASS | `@limiter.limit("5/minute")` |
| `POST /proposals/{id}/rollback` | PASS | `@limiter.limit("5/minute")` |
| `POST /v1/chat/completions` | PASS | `@limiter.limit("10/minute")` |

**Severity**: PASS — All expensive endpoints rate-limited.

**Task Reference**: T188 (resolved)

---

## 12. Technical Debt Tracker

**What**: Centralized tracking of known technical debt items.

| ID | Issue | Location | Impact | Status | Task |
|----|-------|----------|--------|--------|------|
| TD001 | Thread-unsafe singletons | `storage/__init__.py`, `mcp/client.py` | High | **Resolved** | T186 |
| TD002 | Deprecated `datetime.utcnow()` | `graph/state.py`, `sandbox/runner.py`, `api/schemas/__init__.py` | Medium | **Resolved** | T187 |
| TD003 | N+1 queries in Architect | `agents/architect.py` | High | **Resolved** | T190 |
| TD004 | Rate limiting not applied to routes | `api/routes/*.py` | High | **Resolved** | T188 |
| TD005 | Silent exception handling | `agents/__init__.py` (now debug-logged), `tracing/mlflow.py` (5 remain) | Low | **Partial** | T204 |
| TD006 | Dead CLI chat stubs | `cli/main.py` | Medium | **Resolved** (removed) | — |
| TD007 | Missing database indexes | `storage/entities/*.py` | Medium | **Resolved** (migration 006) | T191 |
| TD008 | Missing `sync.py` unit tests | `dal/sync.py` | High | Open | T183 |
| TD009 | Untracked TODO in ha_registry | `api/routes/ha_registry.py:440` | Low | **Resolved** (tagged T170) | — |
| TD010 | 73 `Any` type annotations | Multiple modules | Medium | Open | T193 |
| TD011 | `pg_trgm` GIN index for search | `dal/entities.py` | Low | Open | T192 |
| TD012 | `MessageRepository.get_last_n()` subquery | `dal/conversations.py` | Low | Open | T194 |

---

## 13. Performance Benchmarks

**What**: Track key performance metrics over time. Update after optimization work.

| Metric | Target | Current | Last Measured | Notes |
|--------|--------|---------|---------------|-------|
| Entity discovery (1000 entities) | <30s | TBD | — | Measure after T190 |
| NL query response | <500ms | TBD | — | Requires indexes (T191) |
| Chat response (first token) | <2s | TBD | — | LLM dependent |
| Sandbox script execution | <30s | TBD | — | Policy enforced |
| API cold start | <5s | TBD | — | DB connection time |

**How to measure**: Run with timing:
```bash
# Discovery
time aether discover

# Chat (first response)
time curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "architect", "messages": [{"role": "user", "content": "hello"}]}'

# Entity query
time curl -X POST http://localhost:8000/api/entities/query \
  -H "Content-Type: application/json" \
  -d '{"query": "all lights in the living room"}'
```

---

## Healthcheck Run Instructions

When asked to run this healthcheck, follow these steps:

### Step 1: Automated Scans
Run these searches across the codebase and update the findings above:

1. `grep -r "datetime.utcnow\|datetime.utcfromtimestamp" src/` — Deprecated APIs
2. `grep -r "except Exception" src/` — Error handling (count per module, flag silent catches)
3. `grep -r ": Any" src/` — Type safety (count per module)
4. `grep -r "_instance\|_engine\|_session_factory" src/` — Singleton patterns → check for `asyncio.Lock`
5. `grep -r "TODO\|FIXME\|HACK\|XXX" src/` — Code comments audit
6. `grep -r "@limiter.limit" src/` — Rate limiting coverage
7. Cross-reference `src/**/*.py` modules against `tests/**/*.py` — Test coverage mapping

### Step 2: Manual / Network-Required Checks
These require running commands with network access:

```bash
# Dependency security audit
uv pip audit

# Lockfile freshness
uv lock --check

# Lint check
ruff check src/ tests/

# Type check
mypy src/

# Test coverage
pytest --cov=src --cov-report=term-missing tests/unit/
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
| 2026-02-06 | `001-project-aether` | Post-fix update | Fixed: datetime.utcnow (T187), rate limiting (T188), N+1 query (T190), DB indexes (T191), silent catches in agents/__init__.py, dead CLI stubs (TD006), untracked TODO (TD009). Corrected: thread safety was already PASS (T186). |
| 2026-02-06 | `001-project-aether` | Initial creation | Baseline healthcheck with all sections populated |
