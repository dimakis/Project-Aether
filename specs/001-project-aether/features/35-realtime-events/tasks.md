# Tasks: Real-Time HA Event Stream

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1 -- WebSocket Infrastructure (US1)

### Auth extraction

- [ ] T3501 Extract shared WebSocket auth into `_authenticate(ws, token)` helper in `src/ha/websocket.py`, reuse in existing `_execute()`
- [ ] T3502 Make `BaseHAClient._get_ws_url()` public (remove leading underscore or add public wrapper)

### Event stream core

- [ ] T3503 Create `HAEventStream` in `src/ha/event_stream.py` -- persistent connection, auth, `subscribe_events`, event dispatch to callback
- [ ] T3504 Add exponential backoff reconnect loop (1s, 2s, 4s... 60s ceiling) with logging
- [ ] T3505 [P] Unit tests in `tests/unit/ha/test_event_stream.py` -- connection, auth, subscription, reconnect, max backoff

**Checkpoint**: WebSocket subscription works, reconnects reliably

---

## Phase 2 -- Event Handler (US1)

- [ ] T3506 Create `EventHandler` in `src/ha/event_handler.py` -- bounded `asyncio.Queue(maxsize=1000)`, consumer task
- [ ] T3507 Add per-entity debounce: track latest state per entity_id, only write the most recent
- [ ] T3508 Add batch upsert: collect events for configurable window (default 1.5s), single `EntityRepository.upsert_many()` call
- [ ] T3509 [P] Unit tests in `tests/unit/ha/test_event_handler.py` -- debounce, batching, queue overflow handling, entity creation for unknown entities

**Checkpoint**: Events flow from WebSocket to DB efficiently

---

## Phase 3 -- Lifecycle Integration (US1, US3)

- [ ] T3510 Wire `HAEventStream` + `EventHandler` startup/shutdown into app lifespan in `src/api/main.py`
- [ ] T3511 Update `src/scheduler/service.py` -- disable/reduce delta sync interval when event stream is active
- [ ] T3512 Add fallback logic: if WebSocket fails after max retries, re-enable delta sync and log warning
- [ ] T3513 Close `subscribe_events` gap in `src/ha/gaps.py`

**Checkpoint**: Event stream runs in production, falls back gracefully

---

## Phase 4 -- Event-Driven Triggers (US2)

- [ ] T3514 Add `EVENT` to `TriggerType` enum in `src/storage/entities/insight_schedule.py`
- [ ] T3515 Add event trigger matching logic in `EventHandler` -- check entity_id against active event-trigger schedules, fire analysis on match
- [ ] T3516 [P] Unit tests for event trigger matching and schedule firing
- [ ] T3517 Update insight schedule API to accept `event` trigger type with entity filter configuration

**Checkpoint**: Event-driven insight triggers work end-to-end

---

## Phase 5 -- Polish

- [ ] T3518 Add health check endpoint or metric for event stream connection status
- [ ] T3519 Verify existing discovery sync tests pass
- [ ] T3520 Integration test: simulate HA state change via mock WS server, verify DB update within 2s

---

`[P]` = Can run in parallel (different files, no dependencies)
