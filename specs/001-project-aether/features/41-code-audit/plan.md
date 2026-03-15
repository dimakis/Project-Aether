# Feature 41: Code Audit — Implementation Plan

## Phase 1: Quick Wins (P0 — this session)

### T1. Fix mutable default in proposals route
- File: `src/api/routes/proposals.py:444`
- Change: Replace `body: dict[str, Any] = {}` with `body: dict[str, Any] = Body(default={})`

### T2. Narrow error handling in tool functions
- Files: `src/tools/agent_tools.py`, `src/tools/diagnostic_tools.py`
- Change: Replace `except Exception as e: return f"..."` with specific exceptions
  and structured error responses that preserve diagnostic information.

### T3. Fix N+1 query in list_proposals
- File: `src/api/routes/proposals.py:116-120`
- Change: Replace per-status loop with single `repo.list_all()` query

### T4. Extract model_context boilerplate
- File: `src/tools/agent_tools.py`
- Change: Create reusable `_run_with_model_context()` helper to eliminate 3× duplication

## Phase 2: Performance (P1 — this session)

### T5. Use fast model for orchestrator classification
- File: `src/agents/orchestrator.py`
- Change: Override model selection in `_get_classification_llm()` to use a fast/cheap
  model regardless of user-selected model

### T6. Concurrent automation config fetches in discovery sync
- File: `src/dal/sync.py:_sync_automation_entities()`
- Change: Use `asyncio.gather()` with semaphore for concurrent config fetches

### T7. Fix orchestrator session management
- File: `src/agents/orchestrator.py:173-189`
- Change: Use `async with get_session()` context manager

## Phase 3: Modularity (P2 — future session)

### T8. Split proposals.py into subpackage
### T9. Split handlers.py streaming logic
### T10. Add public method for HA entity state lookup
### T11. Split dal/agents.py into per-repository files

## Phase 4: Polish (P3 — future session)

### T12. Remove redundant logging imports
### T13. Split checkpoints.py model/saver
### T14. Extract scheduler job definitions
