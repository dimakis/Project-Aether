# Feature Specification: Real-Time HA Event Stream

**Feature Branch**: `feat/35-realtime-events`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "WebSocket subscription to HA event bus for real-time entity state updates instead of polling."

## User Scenarios & Testing

### User Story 1 - Persistent Event Subscription (Priority: P1)

As the system, I want a persistent WebSocket connection to Home Assistant's event bus so that entity state changes are received in real time and the local database is always fresh.

**Why this priority**: Core infrastructure -- everything else depends on having a live event stream.

**Independent Test**: Start the event stream, change an entity in HA, verify the DB is updated within 2 seconds without any polling.

**Acceptance Scenarios**:

1. **Given** the event stream is connected, **When** a light is toggled in HA, **Then** the `ha_entities` table reflects the new state within 2 seconds.
2. **Given** the WebSocket connection drops, **When** HA restarts, **Then** the event stream reconnects with exponential backoff and resumes receiving events.
3. **Given** a burst of 100 entity changes in 1 second, **When** processed, **Then** events are batched into a single DB upsert operation without data loss.

---

### User Story 2 - Event-Driven Insight Triggers (Priority: P2)

As a user, I want insight schedules that trigger on entity events (e.g., "run energy analysis when consumption exceeds threshold") in addition to cron and webhook triggers.

**Why this priority**: Extends the scheduling system with a powerful new trigger type. Requires US1.

**Independent Test**: Create an insight schedule with event trigger, simulate the matching entity change, verify analysis runs.

**Acceptance Scenarios**:

1. **Given** an insight schedule with trigger type `event` and entity filter `sensor.energy_total`, **When** that entity's state changes, **Then** the scheduled analysis fires.
2. **Given** an event trigger with a threshold condition, **When** the entity state crosses the threshold, **Then** the analysis fires only on threshold crossing (debounced).

---

### User Story 3 - Graceful Degradation (Priority: P2)

As the system, I want the event stream to degrade gracefully to periodic polling when WebSocket connectivity is unavailable (HA behind a proxy that blocks WS, network issues, etc.).

**Why this priority**: Reliability -- the system must work even when real-time events are unavailable.

**Independent Test**: Block WebSocket traffic, verify the system falls back to delta sync polling automatically.

**Acceptance Scenarios**:

1. **Given** the WebSocket connection cannot be established after all retries, **When** the backoff ceiling is reached, **Then** the system falls back to periodic delta sync and logs a warning.
2. **Given** the event stream reconnects after a fallback period, **When** connection is restored, **Then** a one-time delta sync runs to catch up, then real-time streaming resumes.

---

### Edge Cases

- HA sends events for entities not yet in the DB: upsert creates the entity.
- Event flood from misbehaving integration: bounded queue drops oldest events when full, logs warning.
- Multiple HA zones: one event stream per zone (mirrors multi-zone client pattern).
- Entity removed from HA: `entity_registry_updated` event triggers cleanup if subscribed.

## Requirements

### Functional Requirements

- **FR-001**: System MUST maintain a persistent WebSocket connection to HA's event bus.
- **FR-002**: System MUST subscribe to `state_changed` events and update the local entity DB.
- **FR-003**: DB writes MUST be batched (1-2 second window) to avoid per-event write overhead.
- **FR-004**: System MUST reconnect with exponential backoff (1s to 60s ceiling) on connection loss.
- **FR-005**: System MUST support an `event` trigger type for insight schedules.
- **FR-006**: System MUST fall back to periodic delta sync when WebSocket is unavailable.
- **FR-007**: Event processing MUST use a bounded queue to prevent memory exhaustion.

### Key Entities

- **HAEventStream**: Manages persistent WebSocket connection, authentication, subscription, reconnection.
- **EventHandler**: Consumes events from queue, debounces per entity_id, batches DB upserts.
- **InsightSchedule** (extended): Adds `event` to `TriggerType` enum.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Entity state changes reflected in DB within 2 seconds of HA event.
- **SC-002**: WebSocket reconnection completes within 60 seconds of connection loss.
- **SC-003**: System handles 100 events/second without data loss or memory growth.
- **SC-004**: Periodic delta sync is automatically disabled when event stream is active.
- **SC-005**: Event-driven insight triggers fire within 5 seconds of matching entity change.
