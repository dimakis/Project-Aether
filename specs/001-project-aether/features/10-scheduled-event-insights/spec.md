# Feature 10: Scheduled & Event-Driven Insights

## Summary

Enable insights to run on a schedule (cron) or in response to Home Assistant events (webhook). Currently insights only run on-demand via `POST /insights/analyze` or through the optimization workflow. This feature adds persistent scheduling and HA event-driven triggering so that analysis happens automatically.

## Architecture

**Hybrid approach** — two trigger mechanisms, one analysis pipeline:

```
                          ┌─────────────────────────┐
  ┌──── Cron trigger ────►│                         │
  │   (APScheduler)       │   Existing analysis     │
  │                       │   pipeline              │──► Insight persisted
  │                       │   (DataScientistAgent    │    to DB
  └──── Webhook trigger ─►│    + sandbox)           │
        (HA automation)   │                         │
                          └─────────────────────────┘
```

### 1. Cron Schedules (Aether-native)

APScheduler runs inside Aether's FastAPI lifespan, backed by PostgreSQL for persistence across restarts. Supports standard cron expressions.

Examples:
- `0 2 * * *` — Daily energy analysis at 2am
- `0 8 * * 1` — Weekly behavioral pattern check on Mondays at 8am
- `*/30 * * * *` — Device health check every 30 minutes

### 2. HA Webhook Triggers (HA-native events)

Aether exposes `POST /api/v1/webhooks/ha` which receives events from HA automations. When an event matches a registered trigger, the corresponding analysis runs.

Flow:
```
HA detects state change (e.g., device unavailable)
        │
        ▼
HA automation fires webhook:
  POST /api/v1/webhooks/ha
  { "event_type": "state_changed",
    "entity_id": "sensor.grid_power",
    "data": { "old_state": "on", "new_state": "unavailable" } }
        │
        ▼
Aether matches against registered webhook triggers
        │
        ▼
Runs Data Scientist analysis (same pipeline as POST /insights/analyze)
        │
        ▼
Insight persisted, visible in UI
```

The Architect agent can also create the HA automation for the user — e.g., "Run energy analysis whenever there's a power outage" creates both the Aether trigger record and the HA automation webhook.

## Data Model

### InsightSchedule

```sql
CREATE TABLE insight_schedules (
    id              VARCHAR(36) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    enabled         BOOLEAN NOT NULL DEFAULT true,

    -- What to run
    analysis_type   VARCHAR(50) NOT NULL,    -- energy, behavioral, anomaly, device_health, etc.
    entity_ids      JSON,                     -- scope to specific entities (null = all)
    hours           INTEGER NOT NULL DEFAULT 24, -- lookback window
    options         JSON NOT NULL DEFAULT '{}',  -- extra analysis params

    -- Trigger configuration
    trigger_type    VARCHAR(20) NOT NULL,     -- 'cron' or 'webhook'
    cron_expression VARCHAR(100),             -- e.g., '0 2 * * *' (cron only)
    webhook_event   VARCHAR(100),             -- event label, e.g., 'device_offline' (webhook only)
    webhook_filter  JSON,                     -- match criteria, e.g., {"entity_id": "sensor.*", "to_state": "unavailable"}

    -- Execution tracking
    last_run_at     TIMESTAMP WITH TIME ZONE,
    last_result     VARCHAR(20),              -- 'success', 'failed', 'timeout'
    last_error      TEXT,
    run_count       INTEGER NOT NULL DEFAULT 0,

    -- Metadata
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

## API Endpoints

### Schedule CRUD

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/insight-schedules` | List all schedules |
| `POST` | `/insight-schedules` | Create a new schedule |
| `GET` | `/insight-schedules/{id}` | Get schedule details |
| `PUT` | `/insight-schedules/{id}` | Update a schedule |
| `DELETE` | `/insight-schedules/{id}` | Delete a schedule |
| `POST` | `/insight-schedules/{id}/run` | Manually trigger a scheduled job |

### Webhook Receiver

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhooks/ha` | Receive HA automation webhook events |

Webhook request body:
```json
{
  "event_type": "state_changed",
  "entity_id": "sensor.grid_power",
  "data": {
    "old_state": "on",
    "new_state": "unavailable",
    "attributes": {}
  }
}
```

Webhook authentication: HA long-lived token in `Authorization: Bearer <token>` header, validated against the configured `ha_token`.

## Scheduler Service

Uses `apscheduler[asyncio]` with PostgreSQL job store:

```python
# src/scheduler/service.py

class SchedulerService:
    """Manages cron-based insight schedules via APScheduler."""

    async def start(self):
        """Start the scheduler (called in lifespan startup)."""

    async def stop(self):
        """Graceful shutdown (called in lifespan shutdown)."""

    async def sync_jobs(self):
        """Sync DB schedules → APScheduler jobs."""

    async def add_schedule(self, schedule: InsightSchedule):
        """Add or update a cron job for a schedule."""

    async def remove_schedule(self, schedule_id: str):
        """Remove a cron job."""

    async def execute_schedule(self, schedule_id: str):
        """Called by APScheduler when a job fires.
        Runs the analysis via the existing pipeline."""
```

Lifespan integration:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing init ...
    scheduler = SchedulerService()
    await scheduler.start()
    yield
    await scheduler.stop()
    await close_db()
```

## Settings

```python
# Added to src/settings.py
scheduler_enabled: bool = True
scheduler_timezone: str = "UTC"
webhook_secret: str | None = None  # Optional shared secret for webhook auth
```

## Dependencies

```
apscheduler>=4.0.0a5   # Async-native, PostgreSQL job store
```

Note: APScheduler v4 is async-native. If v4 alpha is too unstable, fall back to v3 with `AsyncIOScheduler`.

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/storage/entities/insight_schedule.py` | New — SQLAlchemy model |
| `alembic/versions/008_insight_schedules.py` | New — DB migration |
| `src/dal/insight_schedules.py` | New — Repository |
| `src/scheduler/service.py` | New — APScheduler wrapper |
| `src/scheduler/__init__.py` | New — Exports |
| `src/api/routes/insight_schedules.py` | New — CRUD endpoints |
| `src/api/routes/webhooks.py` | New — Webhook receiver |
| `src/api/routes/__init__.py` | Modified — register new routers |
| `src/api/main.py` | Modified — scheduler in lifespan |
| `src/settings.py` | Modified — scheduler settings |
| `pyproject.toml` | Modified — add apscheduler dependency |

## Out of Scope

- UI for managing schedules (separate task, can be done later)
- Complex webhook filter expressions (simple glob matching on entity_id for now)
- Webhook retry/dead-letter queue
- Distributed scheduling (single-instance APScheduler is sufficient)
