# Tasks: Comprehensive MLflow Tracing

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1 -- Core Infrastructure

- [ ] T3901 Create `traced_node()` wrapper in `src/tracing/node_tracer.py` — wraps any async LangGraph node function with `mlflow.start_span()`, captures name, duration, inputs/outputs, errors
- [ ] T3902 [P] Unit tests in `tests/unit/tracing/test_node_tracer.py` — success span, error span, attribute truncation, graceful degradation when MLflow unavailable
- [ ] T3903 Export `traced_node` from `src/tracing/__init__.py`
- [ ] T3904 Add `@trace_with_uri("sandbox.execute")` to `SandboxRunner.run()` in `src/sandbox/runner.py` — log policy, exit_code, duration, timed_out, artifact_count as span attributes
- [ ] T3905 [P] Unit test for sandbox tracing — verify span created with correct attributes

**Checkpoint**: Tracing primitives ready

---

## Phase 2 -- Optimization Workflow (US1, US2)

- [ ] T3906 Wrap all 4 optimization nodes with `traced_node` in `src/graph/workflows/optimization.py` — collect_behavioral_data, analyze_and_suggest, architect_review, present_recommendations
- [ ] T3907 Add span attributes to `collect_behavioral_data_node` — entity count, time range, data size
- [ ] T3908 Add span attributes to `analyze_and_suggest_node` — script line count, insight count
- [ ] T3909 Add span attributes to `execute_sandbox_node` — exit code, duration, timed_out (via sandbox tracing from T3904)
- [ ] T3910 Verify optimization trace produces full span tree in MLflow UI

**Checkpoint**: Optimization workflow fully traced

---

## Phase 3 -- All Other Workflows (US3)

- [ ] T3911 Add trace context (`start_experiment_run`) to `run_discovery_workflow` in `src/graph/workflows/discovery.py` + wrap nodes
- [ ] T3912 [P] Add trace context to `build_dashboard_graph` in `src/graph/workflows/dashboard.py` + wrap nodes
- [ ] T3913 [P] Add trace context to `build_review_graph` in `src/graph/workflows/review.py` + wrap nodes
- [ ] T3914 [P] Add trace context to `build_team_analysis_graph` in `src/graph/workflows/team_analysis.py` + wrap nodes
- [ ] T3915 Add trace context to `build_conversation_graph` in `src/graph/workflows/conversation.py` + wrap nodes (conversation already has top-level trace; add per-node spans)
- [ ] T3916 Add trace context to `build_automation_builder_graph` in `src/graph/workflows/automation_builder.py` + wrap nodes

**Checkpoint**: All 9 workflow types produce traces with per-node spans

---

## Phase 4 -- Delegations & Scheduled Jobs (US4, US5)

- [ ] T3917 Add delegation spans in `src/tools/ds_team_tool.py` — wrap DS Team invocation with `mlflow.start_span("delegation.ds_team")`
- [ ] T3918 [P] Add delegation spans in `src/tools/specialist_consult_tools.py` — wrap each specialist invocation
- [ ] T3919 Wrap `_execute_scheduled_analysis()` in `src/scheduler/service.py` with `start_experiment_run("scheduled_analysis")` + log schedule_id, trigger_type, analysis_type
- [ ] T3920 [P] Wrap `_execute_discovery_sync()` and `_execute_trace_evaluation()` with trace contexts

**Checkpoint**: Delegations and scheduled jobs traced

---

## Phase 5 -- Polish

- [ ] T3921 Add attribute truncation to `traced_node` — cap stdout/stderr at 4KB, state values at 2KB
- [ ] T3922 Verify graceful degradation — disable MLflow, run all workflows, confirm zero crashes
- [ ] T3923 Verify no performance regression — benchmark optimization workflow with/without tracing, confirm < 5ms overhead per span
- [ ] T3924 Update `docs/architecture.md` observability section with trace coverage table

---

`[P]` = Can run in parallel (different files, no dependencies)
