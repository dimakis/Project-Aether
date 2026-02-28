# Feature Specification: Comprehensive MLflow Tracing

**Feature Branch**: `feat/39-comprehensive-tracing`
**Created**: 2026-02-28
**Status**: Draft
**Input**: Audit found significant tracing blind spots — LangGraph nodes, sandbox executions, inter-agent delegations, and most workflows are not traced.

## User Scenarios & Testing

### User Story 1 - Per-Node Workflow Tracing (Priority: P1)

As a developer, I want every LangGraph node execution to produce an MLflow span so I can see exactly which step is slow, failed, or produced unexpected output.

**Why this priority**: Without per-node spans, debugging workflow issues requires printf-style log reading. This is the highest-value tracing gap.

**Independent Test**: Run an optimization workflow, open MLflow UI, verify a span tree showing each node (collect_behavioral_data, analyze_and_suggest, architect_review, present_recommendations) with individual timings.

**Acceptance Scenarios**:

1. **Given** an optimization workflow runs, **When** I view the trace in MLflow, **Then** I see a parent span for the workflow with child spans for each node including duration, inputs, and outputs.
2. **Given** a node fails mid-workflow, **When** I view the trace, **Then** the failed node's span shows the exception and all prior nodes show success.
3. **Given** a conversation workflow runs with tool calls, **When** I view the trace, **Then** I see architect_propose -> tool calls -> approval_gate -> developer_deploy as distinct spans.

---

### User Story 2 - Sandbox Execution Tracing (Priority: P1)

As a developer, I want sandbox script executions traced with duration, exit code, stdout/stderr size, and policy name so I can diagnose slow or failing analysis scripts.

**Why this priority**: Sandbox execution is a major time component (30-60s) with no visibility. Script failures are currently only visible in DB records.

**Independent Test**: Run an energy analysis, verify MLflow shows a TOOL span for the sandbox execution with duration, exit code, and artifact metadata.

**Acceptance Scenarios**:

1. **Given** a sandbox script runs successfully, **When** I view the trace, **Then** I see a span with duration, exit_code=0, stdout size, and policy name.
2. **Given** a sandbox script times out, **When** I view the trace, **Then** the span shows timed_out=true with the timeout threshold.
3. **Given** artifacts are produced, **When** I view the trace, **Then** the span shows artifact count and rejected count.

---

### User Story 3 - All Workflows Traced (Priority: P2)

As a developer, I want all workflow types (discovery, dashboard, review, team_analysis, automation_builder) to produce MLflow traces, not just conversation and optimization.

**Why this priority**: Currently only 2 of 9 workflows create MLflow runs. The others are invisible.

**Independent Test**: Trigger each workflow type, verify each produces an MLflow trace with the workflow type as a tag.

**Acceptance Scenarios**:

1. **Given** a discovery sync runs, **When** I check MLflow, **Then** I see a trace tagged `workflow=discovery` with node spans.
2. **Given** a dashboard generation runs, **When** I check MLflow, **Then** I see a trace tagged `workflow=dashboard`.
3. **Given** a scheduled analysis runs, **When** I check MLflow, **Then** I see a trace tagged `workflow=scheduled_analysis` with the schedule ID.

---

### User Story 4 - Inter-Agent Delegation Spans (Priority: P2)

As a developer, I want inter-agent delegations (Architect -> DS Team, Architect -> Dashboard Designer) to appear as distinct spans showing the delegation boundary, not just the tool call.

**Why this priority**: Multi-agent interactions are the hardest to debug. Seeing the delegation boundary in the trace tree makes agent interaction visible.

**Independent Test**: Ask the Architect to analyze energy, verify the trace shows Architect span -> consult_data_science_team tool span -> DS Team span as a nested hierarchy.

**Acceptance Scenarios**:

1. **Given** the Architect delegates to the DS Team, **When** I view the trace, **Then** I see a parent Architect span containing a delegation span containing the DS Team's work.
2. **Given** the DS Team internally routes to the Behavioral Analyst, **When** I view the trace, **Then** specialist selection and execution appear as child spans.

---

### User Story 5 - Scheduled Job Tracing (Priority: P3)

As a developer, I want scheduled analysis runs (cron and webhook triggers) to produce MLflow traces so I can audit what happened during unattended analysis.

**Why this priority**: Scheduled jobs run without user interaction. Without tracing, failures are only visible in logs.

**Independent Test**: Create a cron schedule, let it fire, verify an MLflow trace exists with the schedule ID and trigger type.

**Acceptance Scenarios**:

1. **Given** a cron schedule fires at 2am, **When** I check MLflow the next morning, **Then** I see a trace with tags `trigger=cron`, `schedule_id=...`, and the full node span tree.

---

### Edge Cases

- MLflow unavailable: all tracing degrades gracefully (no crashes, warning logged once).
- Trace within a trace: nested workflow calls (e.g., optimization -> DS Team) should produce child spans under the parent, not separate traces.
- Very long traces: sandbox executions producing large stdout should truncate span attributes to avoid MLflow storage issues.
- Concurrent workflows: each gets its own trace context via ContextVars.

## Requirements

### Functional Requirements

- **FR-001**: Every LangGraph node execution MUST produce an MLflow span with name, duration, and status.
- **FR-002**: Sandbox executions MUST produce MLflow spans with exit_code, duration, timed_out, policy_name, artifact_count.
- **FR-003**: All 9 workflow types MUST create MLflow traces with workflow type tags.
- **FR-004**: Inter-agent delegations MUST produce spans showing the delegation boundary.
- **FR-005**: Scheduled analysis runs MUST produce MLflow traces with trigger metadata.
- **FR-006**: All tracing MUST degrade gracefully when MLflow is unavailable.
- **FR-007**: Span attributes MUST truncate large values (stdout > 4KB, stderr > 2KB).

### Key Entities

- No new DB entities. This feature adds MLflow spans/traces to existing code paths.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of workflow types produce MLflow traces (currently 2/9).
- **SC-002**: Every LangGraph node in every workflow produces a span (currently 0%).
- **SC-003**: Sandbox executions appear in traces with timing data (currently 0%).
- **SC-004**: Inter-agent delegations visible as span boundaries (currently 0%).
- **SC-005**: Zero performance regression — tracing overhead < 5ms per span.
