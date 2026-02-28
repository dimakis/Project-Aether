# Tasks: Proactive Insight Notifications

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1 -- Notification Preferences

- [ ] T3701 Add `notifications` JSONB field to `AppSettings` in `src/storage/entities/app_settings.py` -- schema: `{enabled: bool, min_impact: str, quiet_hours_start: str, quiet_hours_end: str}`
- [ ] T3702 Add migration for the new column (or verify JSONB field is additive and needs no migration if AppSettings already uses flexible JSONB)
- [ ] T3703 Expose notification preferences in `src/api/routes/settings.py` -- GET and PUT

**Checkpoint**: Preferences configurable via API

---

## Phase 2 -- Insight Notifier (US1, US3)

- [ ] T3704 Create `InsightNotifier` in `src/hitl/insight_notifier.py` -- `notify_if_actionable(insights: list[Insight])` method
- [ ] T3705 Implement threshold filtering: skip insights below configured `min_impact`
- [ ] T3706 Implement quiet hours check: suppress notifications during configured window
- [ ] T3707 Implement batch logic: single summary notification for multiple insights, detailed for single
- [ ] T3708 [P] Unit tests in `tests/unit/hitl/test_insight_notifier.py` -- threshold filtering, quiet hours, batching, no notify service configured

**Checkpoint**: Notifier logic complete and tested

---

## Phase 3 -- Push Notification Integration (US1)

- [ ] T3709 Add `send_insight_notification()` to `src/hitl/push_notification.py` -- format notification with title, confidence, action buttons ("Investigate", "Dismiss")
- [ ] T3710 Wire `InsightNotifier.notify_if_actionable()` call into `_execute_scheduled_analysis()` in `src/scheduler/service.py` -- call after successful analysis
- [ ] T3711 Add webhook handler for insight notification actions in `src/api/routes/webhooks.py` -- "INVESTIGATE_{insight_id}" opens chat, "DISMISS_{insight_id}" marks dismissed

**Checkpoint**: End-to-end notification flow works

---

## Phase 4 -- Polish

- [ ] T3712 Verify existing HITL approval notifications still work (no regressions)
- [ ] T3713 Integration test: mock scheduled analysis -> insight creation -> notification sent -> action callback processed

---

`[P]` = Can run in parallel (different files, no dependencies)
