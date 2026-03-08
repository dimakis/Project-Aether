# Implementation Plan: Comprehensive MLflow Tracing

**Feature**: [spec.md](./spec.md)
**Status**: Planned
**Date**: 2026-02-28

## Summary

Close all MLflow tracing blind spots: add per-node spans to every LangGraph workflow, trace sandbox executions, wrap inter-agent delegations, and ensure scheduled jobs produce traces. No new DB entities — purely adding MLflow instrumentation to existing code paths.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: mlflow (existing), LangGraph, LangChain
**Storage**: MLflow tracking server (existing)
**Testing**: pytest with mlflow mock/in-memory tracking
**Target Platform**: Linux server (Docker/K8s)

## Constitution Check

- **Safety First**: No HA mutations. Read-only instrumentation.
- **Isolation**: No changes to sandbox security.
- **Observability**: This IS the observability improvement. Constitution Principle III.
- **State**: No state changes. MLflow traces are append-only.

## Architecture

The approach uses three mechanisms:

### 1. Node-Level Tracing Wrapper

A reusable decorator/wrapper that instruments any LangGraph node function:

```python
async def traced_node(name: str, fn, state, **kwargs):
    with mlflow.start_span(name=name, span_type="CHAIN") as span:
        span.set_inputs({"node": name, "state_keys": list(state.keys())})
        try:
            result = await fn(state, **kwargs)
            span.set_outputs(result)
            span.set_status("OK")
            return result
        except Exception as e:
            span.set_status("ERROR")
            span.set_attribute("error", str(e))
            raise
```

Applied in each workflow's `build_*_graph()` function by wrapping node functions.

### 2. Sandbox Span

Wrap `SandboxRunner.run()` with `@trace_with_uri("sandbox.execute")`:

```python
@trace_with_uri(name="sandbox.execute", span_type="TOOL")
async def run(self, script, ...):
    # existing code
    # span auto-captures duration; we log attributes:
    log_param("sandbox.policy", policy.name)
    log_param("sandbox.exit_code", result.exit_code)
    log_metric("sandbox.duration_s", result.duration_seconds)
```

### 3. Workflow-Level Trace Context

Each workflow entry point creates a trace context:

```python
async def run_discovery_workflow(...):
    with start_experiment_run("discovery_workflow"):
        mlflow.set_tag("workflow", "discovery")
        # ... compile and run graph
```

## Target Span Tree

After implementation, an optimization workflow trace looks like:

```
optimization_workflow (RUN)
  ├── collect_behavioral_data (CHAIN, 12.3s)
  │     └── ha.get_logbook_stats (RETRIEVER, 8.1s)
  ├── analyze_and_suggest (CHAIN, 45.2s)
  │     ├── DataScientist.generate_script (CHAIN, 5.1s)
  │     │     └── llm.ainvoke (LLM, 4.8s) [autologged]
  │     ├── sandbox.execute (TOOL, 28.4s)
  │     │     └── exit_code=0, policy=standard, artifacts=2
  │     └── DataScientist.extract_insights (CHAIN, 11.7s)
  │           └── llm.ainvoke (LLM, 10.2s) [autologged]
  ├── architect_review (CHAIN, 8.1s)
  │     └── Architect.receive_suggestion (CHAIN, 7.9s)
  │           └── llm.ainvoke (LLM, 6.3s) [autologged]
  └── present_recommendations (CHAIN, 0.1s)
```

## Files to Create

- `src/tracing/node_tracer.py` — `traced_node()` wrapper for LangGraph nodes
- `tests/unit/tracing/test_node_tracer.py` — wrapper tests

## Files to Modify

### Phase 1: Core Infrastructure
- `src/tracing/__init__.py` — export `traced_node`
- `src/sandbox/runner.py` — add `@trace_with_uri` to `SandboxRunner.run()`

### Phase 2: Optimization Workflow (highest value)
- `src/graph/workflows/optimization.py` — wrap all 4 nodes with `traced_node`
- `src/graph/nodes/analysis.py` — add span attributes for data sizes, entity counts

### Phase 3: All Other Workflows
- `src/graph/workflows/conversation.py` — wrap nodes
- `src/graph/workflows/discovery.py` — add trace context + wrap nodes
- `src/graph/workflows/dashboard.py` — add trace context + wrap nodes
- `src/graph/workflows/review.py` — add trace context + wrap nodes
- `src/graph/workflows/team_analysis.py` — add trace context + wrap nodes
- `src/graph/workflows/automation_builder.py` — add trace context + wrap nodes

### Phase 4: Delegations & Scheduled Jobs
- `src/agents/execution_context.py` — wrap `emit_delegation` with span
- `src/scheduler/service.py` — wrap `_execute_scheduled_analysis` with trace context
- `src/tools/ds_team_tool.py` — add delegation span around DS Team invocation
- `src/tools/specialist_consult_tools.py` — add spans for specialist routing
