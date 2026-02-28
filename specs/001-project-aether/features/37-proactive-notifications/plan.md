# Implementation Plan: Proactive Insight Notifications

**Feature**: [spec.md](./spec.md)
**Status**: Planned
**Date**: 2026-02-27

## Summary

Wire the insight system to push notifications. When scheduled or event-triggered analysis finds actionable insights, send notifications to the user's phone/watch with configurable thresholds, quiet hours, and batching.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, existing HITL push notification system
**Storage**: PostgreSQL (`AppSettings.notifications` JSONB)
**Testing**: pytest with async fixtures, mock notification service
**Target Platform**: Linux server (Docker/K8s)

## Constitution Check

- **Safety First**: Notifications are informational only. No HA mutations triggered by notifications.
- **Isolation**: No script execution.
- **Observability**: Notification sends logged. Failed sends logged as warnings.
- **State**: Preferences in AppSettings (existing single-row pattern).

## Architecture

```
_execute_scheduled_analysis()
    |-- run_analysis_workflow()
    |-- Extract insights from result
    v
InsightNotifier.notify_if_actionable(insights)
    |-- Load preferences from AppSettings
    |-- Filter by impact threshold
    |-- Check quiet hours
    |-- Batch if multiple
    v
send_insight_notification()  (src/hitl/push_notification.py)
    |-- HA notify service (existing)
    v
User's phone/watch
    |-- Tap "Investigate" -> POST /webhooks/ha -> open chat
    |-- Tap "Dismiss" -> POST /webhooks/ha -> mark insight dismissed
```

## Key Design Decisions

- **Reuse existing HITL notification system**: Same `notify.mobile_app_*` service, same webhook callback pattern.
- **Preferences in AppSettings**: Single JSONB field, consistent with existing chat/dashboard/data_science settings.
- **Batch by analysis run**: One notification per `_execute_scheduled_analysis` call, not per insight.
- **Action callbacks**: Reuse existing webhook handler pattern from approval notifications.

## Files to Create

- `src/hitl/insight_notifier.py` -- `InsightNotifier` class
- `tests/unit/hitl/test_insight_notifier.py` -- Threshold filtering, quiet hours, batching

## Files to Modify

- `src/scheduler/service.py` -- Call notifier after scheduled analysis
- `src/hitl/push_notification.py` -- Add `send_insight_notification()`
- `src/storage/entities/app_settings.py` -- Add notification preferences to schema
- `src/api/routes/webhooks.py` -- Handle insight notification action callbacks
- `src/api/routes/settings.py` -- Expose notification preferences
