---
name: "OpenTelemetry for Runtime Observability"
overview: |
  Adopt OpenTelemetry (OTel) for runtime observability — request tracing, latency, error rates,
  agent execution spans. Retain MLflow specifically for ML ops: LLM evaluation, custom scorers,
  trace quality assessment, and feedback. This gives enterprise-standard observability
  (Grafana/Jaeger/Datadog compatible) while keeping MLflow where it excels.
status: draft
priority: medium
estimated_effort: "L (multi-sprint)"
risk: "Medium — touches tracing infrastructure across the entire call stack"
---

# 1. Problem

MLflow is used for two distinct jobs:

1. **Runtime observability**: request tracing, per-node spans, latency metrics, error tracking,
   health checks — the kind of thing ops teams expect from OTel/Jaeger/Datadog.
2. **ML ops**: LLM evaluation, custom scorers (`response_latency`, `tool_usage_safety`,
   `agent_delegation_depth`), human feedback, experiment tracking.

The fit for job #1 is imperfect — evidenced by the defensive graceful-degradation patterns
throughout `src/tracing/` (safe imports, guard-before-use, try/except wrappers, lazy imports,
health-check degradation). Enterprise ops teams expect OpenTelemetry; "we use MLflow for
tracing" is an unusual conversation.

# 2. Target Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application code                     │
│  Agents, Graph nodes, HA client, API routes             │
└───────────┬───────────────────────────────┬─────────────┘
            │                               │
    ┌───────▼────────┐              ┌───────▼────────┐
    │  OpenTelemetry  │              │    MLflow       │
    │  (runtime)      │              │  (ML ops)       │
    │                 │              │                 │
    │  • Request spans│              │  • Evaluations  │
    │  • Agent spans  │              │  • Scorers      │
    │  • HA call spans│              │  • Feedback     │
    │  • Error rates  │              │  • Experiments  │
    │  • Latency      │              │  • Artifacts    │
    └───────┬────────┘              └───────┬────────┘
            │                               │
    ┌───────▼────────┐              ┌───────▼────────┐
    │  OTLP Exporter  │              │  MLflow Server  │
    │  → Jaeger/Tempo │              │  (sqlite/http)  │
    │  → Grafana      │              │                 │
    │  → Datadog      │              │                 │
    └────────────────┘              └────────────────┘
```

# 3. Plan

## Phase 1 — OTel SDK setup (src/tracing/otel.py)

- [ ] Add dependencies: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`
- [ ] Create `init_otel()`: configure `TracerProvider`, `Resource` (service name, version),
      OTLP exporter (configurable endpoint), `BatchSpanProcessor`
- [ ] Add settings: `otel_enabled`, `otel_exporter_endpoint`, `otel_service_name`
- [ ] Graceful degradation: if OTel init fails, log warning and continue without tracing
- [ ] Call `init_otel()` from FastAPI lifespan (alongside existing `init_mlflow()`)

## Phase 2 — OTel tracing primitives (replace mlflow_spans.py)

- [ ] Create `src/tracing/otel_spans.py`:
  - `traced_node(name, fn)` → OTel span with attributes (node name, workflow, agent)
  - `trace_with_uri(name, span_type, attributes)` → OTel decorator
  - `trace_span(name, attributes)` → context manager using OTel `tracer.start_as_current_span`
- [ ] Map existing span types to OTel `SpanKind`:
  - `CHAIN` → `SpanKind.INTERNAL`
  - `RETRIEVER` → `SpanKind.CLIENT`
  - `LLM` → `SpanKind.CLIENT`
  - `TOOL` → `SpanKind.INTERNAL`
- [ ] Preserve session ID correlation via OTel `Baggage` or span attributes

## Phase 3 — Migrate runtime spans (incremental, per-subsystem)

### 3a — HA client spans
- [ ] `src/ha/base.py`: replace `_trace_ha_call` MLflow spans with OTel spans
- [ ] Preserve `ha.request.{method}.duration_ms` as OTel metric (via `Meter`)
- [ ] Add HTTP semantic conventions: `http.method`, `http.url`, `http.status_code`

### 3b — Graph node spans
- [ ] `src/graph/workflows/*.py`: replace `@trace_with_uri` / `@mlflow.trace` with OTel equivalents
- [ ] `src/tracing/mlflow_spans.py` `traced_node` → OTel `traced_node`
- [ ] Discovery, conversation, analysis workflow nodes

### 3c — Agent spans
- [ ] `src/agents/base.py` `trace_span()`: switch to OTel tracer
- [ ] `src/agents/execution_context.py` `emit_delegation()`: OTel span for delegation boundaries
- [ ] Preserve agent attributes: `agent`, `agent_role`, `session.id`

### 3d — AetherTracer
- [ ] `src/tracing/mlflow_tracer.py`: replace with OTel-based `AetherTracer`
- [ ] Log `workflow.duration_ms`, `workflow.status`, `workflow.error` as OTel span attributes

## Phase 4 — OTel metrics (src/tracing/otel_metrics.py)

- [ ] Create `Meter` for application metrics
- [ ] Migrate `mlflow.log_metric` calls to OTel counter/histogram instruments:
  - `ha.request.{method}.duration_ms` → histogram
  - `entities_found`, `entities_added` → counters
  - `workflow.duration_ms` → histogram
- [ ] Add new metrics: `agent.invocations` counter, `llm.tokens` counter, `tool.calls` counter

## Phase 5 — Session / trace correlation

- [ ] Replace `mlflow.trace.session` tag with OTel Baggage `session.id`
- [ ] `src/tracing/context.py`: set OTel Baggage alongside existing ContextVar
- [ ] Ensure trace ID propagation through A2A calls (W3C Trace Context headers)
- [ ] API endpoints: extract trace context from incoming requests (`TraceContextTextMapPropagator`)

## Phase 6 — Refine MLflow to ML-ops-only role

- [ ] Remove runtime span creation from MLflow (now handled by OTel)
- [ ] Keep: `src/tracing/scorers.py`, `src/tracing/mlflow_feedback.py`,
      evaluation endpoints, nightly trace eval cron
- [ ] Bridge: OTel traces → MLflow evaluations (export OTel trace IDs to MLflow for scorer correlation)
- [ ] Simplify `mlflow_init.py`: remove trace backend check, autolog for tracing
- [ ] Keep `mlflow.openai.autolog()` for LLM token/cost tracking if needed, or replace with OTel

## Phase 7 — API and UI updates

- [ ] Update `/status` health check: add OTel collector health
- [ ] Replace `/diagnostics/traces/recent` with OTel-backed trace query (or keep as MLflow for eval traces)
- [ ] Update `/traces/{trace_id}/spans` to query OTel backend (Jaeger/Tempo API)
- [ ] Update Agent Activity panel in UI to consume OTel trace format

## Phase 8 — Cleanup

- [ ] Remove `src/tracing/mlflow_spans.py` (replaced by `otel_spans.py`)
- [ ] Remove `src/tracing/mlflow_tracer.py` (replaced by OTel `AetherTracer`)
- [ ] Simplify `src/tracing/mlflow_logging.py` (only ML-ops logging remains)
- [ ] Update all graceful degradation patterns to use OTel's built-in NoOp tracer
- [ ] Remove `src/tracing/mlflow_runs.py` if no longer needed for runtime

# 4. Migration Strategy

**Dual-write period**: During Phases 2–3, both OTel and MLflow spans are emitted. This allows
validation without cutting over. A feature flag `otel_tracing_enabled` (default false) gates
the new path. Once validated, flip the flag and remove MLflow runtime spans in Phase 6.

**No-downtime**: OTel SDK has a NoOp tracer fallback. If the OTLP exporter endpoint is
unreachable, spans are silently dropped (same graceful degradation as current MLflow patterns,
but built into the SDK).

# 5. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| OTel SDK adds latency | `BatchSpanProcessor` is async; measured overhead is <1ms per span |
| MLflow scorers need trace data | Bridge OTel trace IDs to MLflow; scorers query OTel backend |
| Existing MLflow trace queries in API | Dual-write period; gradual API migration |
| Team familiarity with OTel | OTel Python SDK is well-documented; simpler API than MLflow tracing |

# 6. Dependencies

- OTLP-compatible backend (Jaeger, Grafana Tempo, or Datadog Agent)
- For local dev: Jaeger all-in-one container (`jaegertracing/all-in-one`)

# 7. Success Criteria

- All runtime spans (HA calls, agent execution, graph nodes, workflows) emit via OTel
- MLflow is used only for evaluations, scorers, feedback, and experiment tracking
- Traces visible in Jaeger/Grafana with full session correlation
- Graceful degradation patterns reduced to OTel's built-in NoOp behavior
- No increase in p99 latency from tracing overhead
