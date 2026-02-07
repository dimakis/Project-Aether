# Feature 22: Weekly System Diagnostic Reports

## Summary

Deliver a weekly diagnostic report to the user via their preferred HA notification channel. The report aggregates LLM token usage, system health, agent activity, automation lifecycle, and HA error summaries. Introduces a user preferences KV store (first use: notification channel selection) and extends the Developer agent to own all HA notification delivery.

## Architecture

Three-agent collaboration with a new user preferences system:

- **Data Scientist** generates the report via a new `system_diagnostic` analysis type (reuses InsightSchedule)
- **Developer** delivers it to HA via the user's preferred notification channel (code-first, LLM fallback)
- **Architect** can trigger the flow conversationally via a `send_ha_notification` delegation tool

```
                          ┌─────────────────────────┐
  ┌──── Cron trigger ────►│                         │
  │   (InsightSchedule)   │   Data Scientist        │
  │                       │   system_diagnostic     │──► Insight persisted
  │                       │   analysis type         │    to DB
  └──── On-demand ───────►│                         │
        (API / chat)      └────────────┬────────────┘
                                       │
                                       ▼
                          ┌─────────────────────────┐
                          │   Developer Agent        │
                          │                         │
                          │   1. Read user prefs     │
                          │   2. Try preferred       │──► HA Notification
                          │      channel (mobile)    │    (mobile_app / persistent)
                          │   3. Fallback chain      │
                          │   4. LLM fallback        │
                          └─────────────────────────┘
```

## User Preferences System

A new foundational KV store for user preferences. Single-user for now (`default_user`), schema supports multi-user via `user_id` FK.

### Data Model

```sql
CREATE TABLE user_preferences (
    id          VARCHAR(36) PRIMARY KEY,
    user_id     VARCHAR(100) NOT NULL DEFAULT 'default_user',
    key         VARCHAR(255) NOT NULL,
    value       JSONB NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE(user_id, key)
);
```

### Initial Preference Keys

| Key | Default | Description |
|-----|---------|-------------|
| `notification.channel` | `"mobile_app"` | Primary notification service |
| `notification.service_target` | `null` | Specific service name (auto-discovered if null) |
| `notification.fallback` | `"persistent_notification"` | Fallback channel |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/preferences` | Get all preferences for current user |
| `GET` | `/api/v1/preferences/{key}` | Get single preference |
| `PUT` | `/api/v1/preferences/{key}` | Set/update a preference |
| `DELETE` | `/api/v1/preferences/{key}` | Delete preference (revert to default) |

## Report Content

The diagnostic report aggregates data for the reporting period (default: 7 days):

- **LLM Token Usage** — Total tokens consumed, per-conversation breakdown, estimated cost
- **Conversation Activity** — Count, avg messages per conversation, busiest days
- **Agent Invocations** — Breakdown by agent role (Architect, Data Scientist, Librarian, Developer)
- **System Health** — Uptime, API error counts, HA connectivity status
- **Automation Proposals** — Created, approved, deployed counts for the period
- **Insights Generated** — Count by analysis type, scheduled vs on-demand
- **Entity Discovery** — New entities found, unavailable entity count
- **HA Error Log Summary** — Top recurring errors/warnings from HA logs

## Developer Notification Delivery

The Developer agent is extended to own all HA notification delivery (consistent with its role as the HA write executor).

### Notification Resolution

1. Read `notification.channel` from user preferences (default: `mobile_app`)
2. Resolve to concrete HA service (e.g., `mobile_app` → auto-discover `notify.mobile_app_<device>` from HA, or use `notification.service_target` if set)
3. Try preferred channel via `mcp.call_service()`
4. On failure → try `notification.fallback` (default: `persistent_notification`)
5. On failure → LLM fallback to reason about alternatives (split long messages, try other targets)

### Code-First Design

The happy path is pure code — no LLM invocation needed. The Developer calls `mcp.call_service("notify", ...)` directly. LLM is only invoked as a fallback for error recovery, keeping the weekly report delivery fast and zero-cost.

## Architect Delegation Tool

A new `send_ha_notification` tool is added to the Architect's tool set, following the same delegation pattern as `deploy_automation`:

```python
@tool("send_ha_notification")
async def send_ha_notification(title: str, message: str) -> str:
    """Send a notification to HA via the Developer agent.
    Uses the user's preferred notification channel."""
```

This routes through `DeveloperWorkflow.send_notification()`, keeping the Architect as orchestrator and the Developer as executor.

## Token Extraction Fix (Prerequisite)

The `Message.tokens_used` column exists but is never populated. LLM responses include token usage in `response.response_metadata["token_usage"]` — this needs to be extracted in the Architect agent and passed through to `MessageRepository.create()`.

Files to modify:
- `src/agents/architect.py` — Extract tokens from `response.response_metadata`
- `src/api/routes/chat.py` — Pass `tokens_used` to `msg_repo.create()`

## Default Schedule

A weekly InsightSchedule is seeded via migration:

- **Name**: "Weekly System Diagnostic"
- **Analysis type**: `system_diagnostic`
- **Trigger**: Cron `0 9 * * 1` (Monday 9am)
- **Enabled**: true

The notification uses a stable `notification_id` (`aether_weekly_diagnostic`) so persistent notifications get replaced each week rather than accumulating. Mobile app notifications always create new entries.

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/storage/entities/user_preference.py` | New — SQLAlchemy model |
| `src/dal/user_preferences.py` | New — Repository (get, set, get_all, delete) |
| `src/api/routes/preferences.py` | New — CRUD endpoints |
| `src/api/schemas/preferences.py` | New — Pydantic schemas |
| `src/diagnostics/weekly_report.py` | New — Report generator with DB aggregate queries |
| `alembic/versions/0XX_user_preferences.py` | New — Migration + seed defaults |
| `alembic/versions/0XX_weekly_diagnostic_schedule.py` | New — Seed InsightSchedule |
| `src/storage/entities/__init__.py` | Modified — Export UserPreference |
| `src/api/routes/__init__.py` | Modified — Register preferences router |
| `src/agents/developer.py` | Modified — Add `send_notification()` with preference resolution |
| `src/agents/architect.py` | Modified — Extract token usage from LLM responses |
| `src/api/routes/chat.py` | Modified — Pass tokens_used to message creation |
| `src/tools/agent_tools.py` | Modified — Add `send_ha_notification` delegation tool |
| `src/tools/__init__.py` | Modified — Register notification tool |
| `src/dal/conversations.py` | Modified — Add `get_token_usage_since()`, `get_conversation_stats_since()` |
| `src/agents/data_scientist.py` | Modified — Add `system_diagnostic` analysis type |
| `src/graph/workflows.py` | Modified — Handle `system_diagnostic` in `run_analysis_workflow()` |
| `src/scheduler/service.py` | Modified — Post-analysis notification delivery |

## Agent Responsibility Boundaries

This feature clarifies and extends agent roles:

- **Architect**: Orchestrator. Delegates "send notification" to Developer via tool. Never calls MCP write ops directly.
- **Data Scientist**: Analyst. Generates the diagnostic report. No HA write operations.
- **Developer**: Executor. Owns all MCP write operations — deployment AND notification delivery. Code-first, preference-aware, with LLM fallback.

The Developer becomes the general-purpose HA write agent, setting up for future delivery operations (dashboard deployment, script creation, etc.).

## Out of Scope

- Email/SMS/push notification channels beyond HA notify services
- Historical report storage beyond the Insight table
- UI for managing preferences (API-only for now)
- Configurable report sections (all sections included by default)
- Multi-user preference isolation (single user for now, schema supports it)
