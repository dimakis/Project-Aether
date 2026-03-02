# Implementation Plan: Real-Time HA Event Stream

**Feature**: [spec.md](./spec.md)
**Status**: Planned
**Date**: 2026-02-27

## Summary

Add a persistent WebSocket subscription to HA's event bus, replacing periodic polling with push-based entity state updates. Includes debounced batch DB writes, exponential backoff reconnection, event-driven insight triggers, and graceful fallback to polling.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: websockets (existing), asyncio, SQLAlchemy (async)
**Storage**: PostgreSQL (entity state updates via `EntityRepository.upsert_many()`)
**Testing**: pytest with async fixtures, mock WebSocket server
**Target Platform**: Linux server (Docker/K8s)

## Constitution Check

- **Safety First**: No HA mutations. Read-only event subscription.
- **Isolation**: No script execution.
- **Observability**: Event stream health metrics logged. Reconnection events traced.
- **State**: Entity state persisted to Postgres. No LangGraph state changes.

## Architecture

```
HA Event Bus
    |-- WebSocket (persistent)
    v
HAEventStream (src/ha/event_stream.py)
    |-- authenticate (reuse from websocket.py)
    |-- subscribe_events(event_type="state_changed")
    |-- reconnect loop (1s, 2s, 4s... 60s backoff)
    v
asyncio.Queue(maxsize=1000)
    v
EventHandler (src/ha/event_handler.py)
    |-- debounce per entity_id (keep latest state)
    |-- batch upsert every 1-2 seconds
    |-- check event triggers for insight schedules
    v
EntityRepository.upsert_many() / InsightSchedule triggers
```

## Key Design Decisions

- **Single connection**: One WebSocket per HA zone. Managed as an asyncio Task in the app lifespan.
- **Bounded queue**: Prevents memory exhaustion under event floods. Drops oldest on overflow.
- **Debounce**: If an entity changes 10 times in 1 second, only the latest state is written.
- **Batch writes**: Collect events for 1-2 seconds, then single `upsert_many()` call.
- **Fallback**: If WebSocket fails after max retries, re-enable periodic delta sync.
- **Auth reuse**: Extract shared authentication logic from `websocket.py` for both one-shot and persistent connections.

## Files to Create

- `src/ha/event_stream.py` -- `HAEventStream` class
- `src/ha/event_handler.py` -- `EventHandler` with batching and debounce
- `tests/unit/ha/test_event_stream.py` -- Connection, reconnect, auth tests
- `tests/unit/ha/test_event_handler.py` -- Batching, debounce, trigger tests

## Files to Modify

- `src/ha/websocket.py` -- Extract shared auth into `_authenticate(ws, token)` helper
- `src/ha/base.py` -- Make `_get_ws_url()` public
- `src/scheduler/service.py` -- Disable delta sync when event stream is active
- `src/storage/entities/insight_schedule.py` -- Add `EVENT` to `TriggerType` enum
- `src/ha/gaps.py` -- Close `subscribe_events` gap
- `src/api/main.py` -- Start/stop event stream in lifespan
