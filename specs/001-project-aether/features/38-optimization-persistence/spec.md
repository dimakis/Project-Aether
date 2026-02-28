# Feature Specification: Optimization Persistence

**Feature Branch**: `feat/38-optimization-persistence`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "Persist optimization jobs and suggestions to the database (currently in-memory) and polish the existing UI."

## User Scenarios & Testing

### User Story 1 - Persistent Optimization Jobs (Priority: P1)

As a user, I want optimization jobs to survive server restarts so I can view past results, track job history, and resume where I left off.

**Why this priority**: Core durability issue -- all job data is currently lost on restart.

**Independent Test**: Run an optimization job, restart the server, verify the job and its results are still accessible.

**Acceptance Scenarios**:

1. **Given** an optimization job completes, **When** the server restarts, **Then** `GET /optimize/{job_id}` still returns the job with all results.
2. **Given** multiple jobs have been run over a week, **When** I call `GET /optimize/jobs`, **Then** I see the full history with status, timestamps, and counts.
3. **Given** a job is running when the server crashes, **When** the server restarts, **Then** the job is marked as `failed` with an appropriate error message.

---

### User Story 2 - Persistent Automation Suggestions (Priority: P1)

As a user, I want automation suggestions to persist in the database so I can review, accept, or reject them at any time -- not just while the server is running.

**Why this priority**: Suggestions are the primary output of optimization. Losing them defeats the purpose.

**Independent Test**: Generate suggestions from an optimization run, restart the server, verify suggestions are still listed and actionable.

**Acceptance Scenarios**:

1. **Given** an optimization job produces 3 suggestions, **When** I call `GET /optimize/suggestions/list`, **Then** all 3 are returned with correct metadata.
2. **Given** I accept a suggestion, **When** I call `GET /optimize/suggestions/list` later, **Then** the suggestion shows status "accepted" with the linked proposal ID.
3. **Given** suggestions exist from different job runs, **When** I filter by job_id, **Then** only suggestions from that job are returned.

---

### User Story 3 - UI Job History (Priority: P2)

As a user, I want to see a history of past optimization jobs in the UI so I can review what analyses have been run and their outcomes.

**Why this priority**: Makes the optimization page useful beyond single-session usage.

**Independent Test**: Run 3 optimization jobs, navigate to the optimization page, verify all 3 appear in a history section.

**Acceptance Scenarios**:

1. **Given** multiple completed jobs exist, **When** I view the optimization page, **Then** I see a job history section with status, date, insight/suggestion counts.
2. **Given** I click on a past job, **When** the detail expands, **Then** I see the recommendations and linked suggestions.

---

### Edge Cases

- Job in "running" state when server crashes: mark as "failed" on startup reconciliation.
- Very old jobs: no automatic cleanup (admin can delete via API if needed).
- Suggestion accepted but proposal creation fails: suggestion stays "pending", error logged.

## Requirements

### Functional Requirements

- **FR-001**: Optimization jobs MUST be persisted to PostgreSQL.
- **FR-002**: Automation suggestions MUST be persisted with FK to their parent job.
- **FR-003**: Existing API contract MUST be preserved (no breaking changes to response schemas).
- **FR-004**: Jobs in "running" state at startup MUST be reconciled to "failed".
- **FR-005**: UI MUST show job history with filtering by status.
- **FR-006**: System MUST support listing suggestions filtered by job_id.

### Key Entities

- **OptimizationJob**: UUID PK, status, analysis_types (JSONB), hours_analyzed, insight_count, suggestion_count, recommendations (JSONB), error, started_at, completed_at, timestamps.
- **AutomationSuggestion**: UUID PK, job_id (FK), pattern, entities (JSONB), proposed_trigger, proposed_action, confidence, source_insight_type, status, timestamps.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Job data survives server restart with zero data loss.
- **SC-002**: Suggestion accept/reject operations complete in under 200ms.
- **SC-003**: Job history page loads in under 500ms with 100+ jobs.
- **SC-004**: Existing optimization API tests pass without modification.
