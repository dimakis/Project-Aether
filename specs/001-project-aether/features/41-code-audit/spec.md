# Feature 41: Code Audit & Health Check

## Overview

Comprehensive code quality audit covering code smells, error handling,
modularity, and agent response time optimization across the Aether codebase
(~28,500 lines across 270+ Python files in `src/`).

## Audit Findings

### 1. Files That Need Modularization (Too Long)

| File | Lines | Issue | Action |
|------|-------|-------|--------|
| `src/api/routes/proposals.py` | 1,287 | Single file with 15+ route handlers AND 3 deployment strategies AND YAML generation | Split into `proposals/routes.py`, `proposals/deploy.py`, `proposals/yaml.py` |
| `src/tools/agent_tools.py` | 781 | 6 tool functions each with identical model_context boilerplate (lines 67-85 pattern repeated 3×) | Extract `_with_model_context()` helper; split formatters to `agent_tools_format.py` |
| `src/dal/agents.py` | 727 | 3 large repository classes in one file | Split into `agents/agent_repo.py`, `agents/config_version_repo.py`, `agents/prompt_version_repo.py` |
| `src/api/routes/openai_compat/handlers.py` | 682 | Single streaming handler is 490 lines with deeply nested event processing | Extract `_handle_distributed_stream()` and `_handle_monolith_stream()` into separate functions or a handler class |
| `src/dal/sync.py` | 624 | Discovery sync service with 4 sync methods + delta sync + convenience functions | Already well-structured; extract `_sync_automation_entities` to separate file |
| `src/storage/checkpoints.py` | 594 | Checkpoint model + saver + write model + write saver in one file | Split model from saver: `checkpoint_models.py` / `checkpoint_saver.py` |
| `src/scheduler/service.py` | 595 | Scheduler with many job definitions inline | Extract job definitions to `scheduler/jobs.py` |

### 2. Error Handling / Swallowing Issues

#### Critical: Bare `except Exception` That Swallows Errors

**33 instances** of `except Exception:` across `src/` — many silently swallow errors:

- `src/api/routes/proposals.py` (5×): Lines 87, 768, 821, 931, 1144 — HA client failures logged at debug/warning but user gets no feedback
- `src/tools/agent_tools.py` (6×): Every tool returns `f"I wasn't able to..."` on ANY exception — hides timeouts, auth failures, DB errors behind a generic string
- `src/tools/diagnostic_tools.py` (5×): Same pattern — returns error string that swallows the root cause
- `src/api/routes/openai_compat/handlers.py` (3×): Line 215 swallows stream timeout resolution; line 373 swallows distributed streaming failure; line 680 catches all streaming errors
- `src/hitl/insight_notifier.py` (2×): Silent swallow of notification failures
- `src/ha/event_handler.py` (2×): Event processing failures silently dropped

**Fix priority**: HIGH — These mask real failures (auth token expired, DB connection lost, HA unreachable) behind generic messages.

#### Mutable Default Argument

```python
# src/api/routes/proposals.py:444
body: dict[str, Any] = {},  # noqa: B006
```

The `# noqa` suppresses a legitimate Ruff B006 (mutable default). Should use `Body(default={})` from FastAPI.

### 3. Code Smells

#### 3a. Duplicated Model Context Boilerplate

`src/tools/agent_tools.py` repeats this 15-line block 3 times (lines 68-85, 442-459, 598-615):

```python
from src.agents.model_context import get_model_context, model_context
ctx = get_model_context()
parent_span_id = None
try:
    from src.tracing import get_active_span
    active_span = get_active_span()
    if active_span and hasattr(active_span, "span_id"):
        parent_span_id = active_span.span_id
except (AttributeError, LookupError):
    logger.debug(...)
with model_context(model_name=..., temperature=..., parent_span_id=...):
```

Should be a single `@with_inherited_model_context` decorator.

#### 3b. Redundant Import of `logging` Inside Methods

`src/sandbox/runner.py:348` and `src/dal/sync.py:183` both do:
```python
import logging
logging.getLogger(__name__).warning(...)
```
despite `logger = logging.getLogger(__name__)` already being defined at module level.

#### 3c. Sequential I/O in Discovery Sync

`src/dal/sync.py:_sync_automation_entities()` fetches automation configs sequentially:
```python
for entity in automations:
    config = await self.ha.get_automation_config(ha_automation_id)
```
With 50+ automations, this is 50 sequential HTTP calls. Should use `asyncio.gather()` with concurrency limiting.

#### 3d. Sequential I/O in `list_proposals` (N+1 Query Pattern)

`src/api/routes/proposals.py:116-120`:
```python
for s in ProposalStatus:
    proposals.extend(await repo.list_by_status(s, limit=limit))
```
Makes N separate DB queries (one per status). Should be a single `repo.list_all()` query.

#### 3e. Private API Usage

`src/api/routes/proposals.py:83` and `:911`:
```python
state_data = await ha._request("GET", f"/api/states/{entity_id}")
```
Routes calling `_request` (private method) directly instead of using a public API method.

### 4. Agent Response Time Optimization

#### 4a. LLM Factory — Good: Already Cached

`src/llm/factory.py` caches instances per `(provider, model, temperature)`. No action needed.

#### 4b. Orchestrator — Extra LLM Call on Every Request

`src/api/routes/openai_compat/handlers.py:387-391`:
```python
orchestrator = OrchestratorAgent(model_name=request.model)
classification = await orchestrator.classify_intent(...)
plan = await orchestrator.plan_response(...)
```
When `needs_orchestrator=True`, this makes 1-2 extra LLM calls (classify + optionally generate clarification options) before the actual agent even starts. The orchestrator uses the **same model** as the target agent for classification — expensive for frontier models.

**Fix**: Use a fast/cheap model for classification regardless of request model. Cache agent routing for identical recent messages.

#### 4c. Orchestrator DB Query Without Session Context Manager

`src/agents/orchestrator.py:173-189`:
```python
factory = get_session_factory()
session = factory()
try:
    repo = AgentRepository(session)
    agents = await repo.list_all()
finally:
    await session.close()
```
Manually managing session instead of using `async with get_session()`. Also queries DB on every classify call — should be cached with TTL.

#### 4d. Resilient LLM Retry Delays

`src/llm/circuit_breaker.py` defines `RETRY_DELAYS` — need to verify these are reasonable for user-facing latency (imported but not shown in the read). The current retry mechanism adds latency on transient failures.

#### 4e. Discovery Sync — Sequential Automation Config Fetches

As noted in 3c, discovery sync fetches automation configs one at a time. With concurrent fetching, sync time could drop from O(n × latency) to O(latency + n/concurrency × latency).

### 5. Security Issues

#### 5a. Mutable Default in Route Handler

Already noted — `body: dict[str, Any] = {}` in proposals YAML update.

#### 5b. No Timeout on `connect()` in BaseHAClient

`src/ha/base.py:169` uses `timeout=5` for connect check, which is good. But `_request` inherits from `self.config.timeout` (default 30s) — appropriate.

### 6. Positive Findings (No Action Needed)

- **No f-string logging**: Zero instances found. All logging uses lazy `%s` formatting.
- **No TODO/FIXME/HACK comments**: Clean codebase.
- **Good exception hierarchy**: `AetherError` base with proper subclasses.
- **Correlation IDs**: Consistently propagated via middleware.
- **Security headers**: Comprehensive middleware coverage.
- **Connection pooling**: `BaseHAClient._get_http_client()` properly pools connections.
- **LLM cache**: Factory caches instances per config tuple.
- **Rate limiting**: Applied to all mutation endpoints.
- **Batch operations**: `BaseRepository.upsert_many()` is well-implemented.
- **`asyncio.sleep` usage**: Only in legitimate places (retry backoff, event batching).

## Priority Matrix

| Priority | Finding | Impact | Effort |
|----------|---------|--------|--------|
| P0 | Mutable default in proposals route | Security/correctness | 5 min |
| P0 | Error swallowing in tools (agent_tools, diagnostic_tools) | Reliability | 1 hr |
| P1 | Orchestrator uses expensive model for classification | Response time | 30 min |
| P1 | Sequential automation config fetches in sync | Sync performance | 30 min |
| P1 | N+1 query in list_proposals | API latency | 15 min |
| P1 | Duplicated model_context boilerplate | Maintainability | 30 min |
| P2 | Split proposals.py (1287 lines) | Maintainability | 1 hr |
| P2 | Split handlers.py streaming logic | Maintainability | 1 hr |
| P2 | Private _request usage in proposals routes | API hygiene | 15 min |
| P2 | Orchestrator session management | Correctness | 15 min |
| P3 | Split dal/agents.py | Maintainability | 30 min |
| P3 | Split checkpoints.py | Maintainability | 30 min |
| P3 | Redundant logging imports | Clean code | 5 min |
