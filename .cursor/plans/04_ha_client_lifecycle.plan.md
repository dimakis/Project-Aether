---
name: "HA Client Lifecycle — FastAPI DI & Proper Shutdown"
overview: |
  Replace the module-level singleton dict pattern for HA clients with FastAPI lifespan
  management and dependency injection. Ensures httpx.AsyncClient connections are properly
  closed on shutdown, preventing connection pool exhaustion and stale connections in
  long-running services.
status: draft
priority: high
estimated_effort: "S (1 sprint)"
risk: "Low — well-scoped refactor with clear boundaries"
---

# 1. Problem

`get_ha_client()` uses a module-level `_clients: dict[str, HAClient]` with `threading.Lock()`.
Each `HAClient` holds a shared `httpx.AsyncClient` (max 100 connections, 20 keepalive) that is
**never closed** during normal application shutdown. The FastAPI lifespan shuts down the DB,
scheduler, and event stream, but never iterates `_clients` to call `close()`.

Additionally, `reset_ha_client()` clears the cache without calling `close()` on evicted clients,
which leaks connections.

For a long-running service making hundreds of HA API calls, this risks:
- Connection pool exhaustion
- Stale/half-closed TCP connections
- Resource leak warnings on shutdown

# 2. Plan

## Phase 1 — Add cleanup to reset and shutdown

- [ ] `reset_ha_client()`: call `await client.close()` on evicted clients before clearing cache
  - Handle sync context: if called from sync code, schedule close via `asyncio.get_event_loop()`
- [ ] Create `close_all_ha_clients()` async function that iterates `_clients`, calls `close()` on each
- [ ] Call `close_all_ha_clients()` in FastAPI lifespan shutdown (alongside `close_db()`, etc.)

## Phase 2 — FastAPI dependency injection

- [ ] Create `src/api/deps.py` dependency (or add to existing):
  ```python
  async def get_ha(zone_id: str = "__default__") -> HAClient:
      return await get_ha_client_async(zone_id)
  ```
- [ ] Update API routes that call `get_ha_client()` to use `Depends(get_ha)`:
  - HA entity tools, automation tools, input tools, script/scene tools, utility tools
  - Any route handler that directly calls `get_ha_client()`
- [ ] This makes HA client access consistent with existing DI patterns (`RequireAPIKey`)

## Phase 3 — Connection health monitoring

- [ ] Add connection pool stats to `/status` health check:
  - Active connections, idle connections, pool utilization
  - Last successful HA API call timestamp
- [ ] Add `httpx.AsyncClient` event hooks for connection lifecycle logging at DEBUG level
- [ ] Consider `httpx.AsyncClient` timeout configuration review:
  - Current: uses httpx defaults (5s connect, 5s read)
  - Recommended: explicit `httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=10.0)`

## Phase 4 — Tests

- [ ] Unit test: `close_all_ha_clients()` calls `close()` on all cached clients
- [ ] Unit test: `reset_ha_client()` calls `close()` before clearing
- [ ] Unit test: FastAPI lifespan shutdown closes HA clients
- [ ] Unit test: `Depends(get_ha)` returns cached client

# 3. Implementation Notes

- The `threading.Lock()` in `get_ha_client()` is for thread safety in sync contexts. The async
  path (`get_ha_client_async`) also uses this lock, which blocks the event loop. Consider
  replacing with `asyncio.Lock` for the async path, keeping `threading.Lock` for sync.
- The DI approach doesn't eliminate the cache — it just provides a cleaner access pattern and
  ensures the lifespan manages the lifecycle.

# 4. Success Criteria

- `httpx.AsyncClient.aclose()` is called on every cached HA client during app shutdown
- `reset_ha_client()` closes evicted clients before clearing the cache
- No "unclosed client" warnings in logs on shutdown
- HA client accessible via FastAPI `Depends()` in route handlers
- Connection pool stats visible in `/status`
