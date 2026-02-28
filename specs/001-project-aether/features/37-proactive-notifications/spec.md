# Feature Specification: Proactive Insight Notifications

**Feature Branch**: `feat/37-proactive-notifications`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "Proactively surface insights via push notifications when scheduled or event-triggered analysis finds actionable results."

## User Scenarios & Testing

### User Story 1 - Push Notifications for Actionable Insights (Priority: P1)

As a user, I want to receive push notifications on my phone/watch when the system discovers actionable insights (e.g., energy spikes, device health issues) so I don't have to manually check the insights page.

**Why this priority**: Core value -- connects existing insight generation to existing push notification infrastructure.

**Independent Test**: Run a scheduled analysis that produces a high-impact insight, verify a push notification is sent to the configured device.

**Acceptance Scenarios**:

1. **Given** a scheduled analysis produces an insight with impact "high", **When** the analysis completes, **Then** a push notification is sent with the insight title and confidence.
2. **Given** a scheduled analysis produces only "low" impact insights, **When** the analysis completes, **Then** no push notification is sent (below default threshold).
3. **Given** the user taps "Investigate" on the notification, **When** the action callback fires, **Then** the app opens to a chat session with the insight context pre-loaded.

---

### User Story 2 - Notification Preferences (Priority: P2)

As a user, I want to configure notification preferences (minimum impact threshold, quiet hours, enable/disable) so I control when and how often I'm notified.

**Why this priority**: User control prevents notification fatigue.

**Independent Test**: Set quiet hours to 22:00-07:00, generate a high-impact insight at 23:00, verify no notification is sent. Generate one at 08:00, verify it is sent.

**Acceptance Scenarios**:

1. **Given** I set the minimum impact threshold to "critical", **When** a "high" impact insight is generated, **Then** no notification is sent.
2. **Given** I configure quiet hours 22:00-07:00, **When** an insight is generated at 23:30, **Then** the notification is suppressed until 07:00 (or dropped, based on preference).
3. **Given** I disable insight notifications, **When** any insight is generated, **Then** no push notifications are sent.

---

### User Story 3 - Batch Notifications (Priority: P3)

As a user, I want multiple insights from a single analysis run batched into one notification so I'm not spammed with individual alerts.

**Why this priority**: Prevents notification fatigue during comprehensive analysis runs.

**Independent Test**: Run an analysis that produces 5 high-impact insights, verify a single summary notification is sent.

**Acceptance Scenarios**:

1. **Given** an analysis produces 5 actionable insights, **When** the notifier runs, **Then** a single summary notification is sent: "5 new insights found. Tap to review."
2. **Given** an analysis produces 1 actionable insight, **When** the notifier runs, **Then** a detailed notification is sent with the insight title.

---

### Edge Cases

- Notify service not configured: log warning, skip notification silently.
- HA Companion App not installed: notification fails gracefully, logged as warning.
- Insight dismissed before notification callback: "Investigate" opens insights page (not a specific insight).
- Multiple analysis runs complete simultaneously: each batch is notified independently.

## Requirements

### Functional Requirements

- **FR-001**: System MUST send push notifications when scheduled or event-triggered analysis produces actionable insights.
- **FR-002**: Notifications MUST respect user-configured impact threshold (default: "high").
- **FR-003**: Notifications MUST respect quiet hours configuration.
- **FR-004**: Multiple insights from one analysis MUST be batched into a single notification.
- **FR-005**: Notification actions MUST include "Investigate" (opens chat with context) and "Dismiss" (marks insight as dismissed).
- **FR-006**: Notification preferences MUST be stored in `AppSettings` and configurable via the settings API.
- **FR-007**: System MUST degrade gracefully when push notification service is unavailable.

### Key Entities

- **InsightNotifier**: Service that filters insights by preferences and sends notifications.
- **AppSettings** (extended): Adds `notifications` JSONB field with threshold, quiet_hours, enabled.

## Success Criteria

### Measurable Outcomes

- **SC-001**: High-impact insights generate push notification within 10 seconds of analysis completion.
- **SC-002**: Quiet hours suppression works correctly across timezone boundaries.
- **SC-003**: Batch notifications reduce notification count by 80%+ for multi-insight analyses.
- **SC-004**: System operates normally when push notifications are disabled or unavailable.
