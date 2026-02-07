**Completed**: 2026-02-07

# Feature 11: Live Agent Activity Trace

**Status**: Complete

## Summary

Add a real-time agent activity visualization to the Chat page. When a user sends a message, a collapsible right panel shows which agents are active, how they delegate to each other, and a timeline of trace events. This makes the "thinking" process visible and debuggable.

## Architecture

### Phase 1 — Post-hoc Trace Replay (current backend)

The current backend runs the full workflow before streaming the response. Phase 1 fetches the trace tree after message completion and animates through it:

```
User sends message
        │
        ▼
Backend runs workflow → returns response + trace_id (already implemented)
        │
        ▼
Frontend fetches GET /v1/traces/{trace_id}/spans
        │
        ▼
Panel animates through the span tree with relative timing
```

During streaming (before completion), the panel shows a simulated "Architect thinking..." state since the Architect is always the entry point.

### Phase 2 — Real-Time Trace Events (Implemented)

Trace events are emitted as SSE events before text chunks. Since the backend runs the full workflow synchronously before streaming, `_build_trace_events()` extracts the event sequence from the completed state and emits them upfront:

```
data: {"type":"trace","agent":"architect","event":"start","ts":1700000000.05}
data: {"type":"trace","agent":"data_scientist","event":"start","ts":1700000000.15}
data: {"type":"trace","agent":"data_scientist","event":"tool_call","tool":"analyze_energy","ts":1700000000.20}
data: {"type":"trace","agent":"data_scientist","event":"tool_result","ts":1700000000.25}
data: {"type":"trace","agent":"data_scientist","event":"end","ts":1700000000.30}
data: {"type":"trace","agent":"architect","event":"end","ts":1700000000.35}
data: {"type":"trace","event":"complete","agents":["architect","data_scientist"],"ts":1700000000.40}
data: {"choices":[{"delta":{"content":"Based on the analysis..."}}]}
```

**Tool-to-agent mapping** in `_build_trace_events()`:
- `analyze_energy`, `run_custom_analysis`, `diagnose_issue` → `data_scientist`
- `create_insight_schedule`, `seek_approval`, `execute_service` → `system`
- All other tools remain under `architect`

**Frontend handling**: Both the ChatPage and InlineAssistant process trace events via the shared `handleTraceEvent()` utility, updating agent activity state in real time. Background requests (title generation, suggestions) skip trace emission.

No additional WebSocket infrastructure — piggybacks on the existing SSE chat stream.

## UI Design

### Agent Activity Panel (right side of Chat page)

```
┌──────────────────────────────────────┬─────────────────────┐
│  Chat Messages                       │  Agent Activity  [×]│
│                                      │                     │
│  You: Analyze my energy usage        │  ┌─ Agent Flow ──┐  │
│                                      │  │               │  │
│  Aether: Based on the analysis...    │  │  [Architect]──┐│  │
│                                      │  │      ◉ active ││  │
│                                      │  │       │       ││  │
│                                      │  │       ▼       ││  │
│                                      │  │  [Data Sci.]  ││  │
│                                      │  │      ◉ active ││  │
│                                      │  │       │       ││  │
│                                      │  │       ▼       ││  │
│                                      │  │  [Sandbox]    ││  │
│                                      │  │      ✓ done   ││  │
│                                      │  └───────────────┘│  │
│                                      │                     │
│                                      │  ── Timeline ─────  │
│                                      │  0.0s ⚡ Architect   │
│                                      │        Thinking...  │
│                                      │  1.2s 🔧 Tool call  │
│                                      │        analyze_     │
│                                      │        energy()     │
│                                      │  1.3s 📊 Data Sci.  │
│                                      │        Generating   │
│                                      │        script...    │
│                                      │  3.1s 🐍 Sandbox    │
│                                      │        Executing... │
│                                      │  4.8s ✅ Complete    │
│                                      │        (4.8s total) │
└──────────────────────────────────────┴─────────────────────┘
```

**Two sections:**

1. **Agent Topology (top)** — Small flow diagram. Agents shown as nodes with icons. Active agent pulses/glows with `framer-motion`. Lines show delegation arrows. Completed agents get a checkmark.

2. **Trace Timeline (bottom)** — Scrollable event log with relative timestamps. Each entry shows the agent, event type (thinking, tool_call, sandbox_exec, complete), and a brief detail. Expandable for tool call arguments / results.

### Panel Toggle

A small button in the chat header: `[◉ Activity]` that toggles the panel. Badge shows active agent count during streaming.

### Sidebar Enhancement

The sidebar footer currently shows `● System Healthy`. During agent processing:

```
Before:  ● System Healthy
During:  ◉ Architect → Data Scientist  (pulse animation)
After:   ● System Healthy
```

## Backend API

### GET /v1/traces/{trace_id}/spans

Returns the MLflow trace tree for visualization:

```json
{
  "trace_id": "abc123",
  "status": "OK",
  "duration_ms": 4800,
  "root_span": {
    "span_id": "s1",
    "name": "conversation_turn",
    "agent": "architect",
    "type": "chain",
    "start_ms": 0,
    "end_ms": 4800,
    "status": "OK",
    "children": [
      {
        "span_id": "s2",
        "name": "ChatOpenAI",
        "agent": "architect",
        "type": "llm",
        "start_ms": 50,
        "end_ms": 1200,
        "status": "OK",
        "attributes": { "model": "gpt-4o", "tokens": 450 }
      },
      {
        "span_id": "s3",
        "name": "analyze_energy",
        "agent": "architect",
        "type": "tool",
        "start_ms": 1200,
        "end_ms": 4500,
        "status": "OK",
        "children": [
          {
            "span_id": "s4",
            "name": "DataScientist.analyze",
            "agent": "data_scientist",
            "type": "chain",
            "start_ms": 1300,
            "end_ms": 4200,
            "children": [
              {
                "span_id": "s5",
                "name": "sandbox_execute",
                "agent": "data_scientist",
                "type": "tool",
                "start_ms": 3100,
                "end_ms": 4100,
                "status": "OK"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

Implementation reads from MLflow's trace storage:
```python
@router.get("/traces/{trace_id}/spans")
async def get_trace_spans(trace_id: str):
    client = mlflow.MlflowClient()
    trace = client.get_trace(trace_id)
    # Transform trace.data.spans into nested tree
    return build_span_tree(trace)
```

Agent identification heuristic:
- Span name contains "architect" or "Architect" → `architect`
- Span name contains "data_scientist" or "DataScientist" or "analyze" → `data_scientist`
- Span name contains "sandbox" → `sandbox`
- Span name contains "librarian" or "discover" → `librarian`
- Span type is "LLM" → inherit parent agent
- Default → `system`

## Agent Registry

Known agents for the topology view:

| Agent | Icon | Color | Description |
|-------|------|-------|-------------|
| Architect | `⚡` Brain | Blue | Orchestrator, handles chat and delegation |
| Data Scientist | `📊` Chart | Green | Analysis, script generation, insights |
| Sandbox | `🐍` Code | Orange | Script execution environment |
| Librarian | `📚` Book | Purple | Entity discovery and cataloging |
| Developer | `🔧` Wrench | Amber | Automation deployment |

## Files Created/Modified

### Phase 1 (Post-hoc Trace Replay)
| File | Action |
|------|--------|
| `src/api/routes/traces.py` | New — Trace spans endpoint |
| `src/api/routes/__init__.py` | Modified — register traces router |
| `ui/src/api/client.ts` | Modified — add `getTraceSpans()` function |
| `ui/src/api/hooks.ts` | Modified — add `useTraceSpans()` hook |
| `ui/src/components/chat/agent-activity-panel.tsx` | New — Collapsible panel container |
| `ui/src/components/chat/agent-topology.tsx` | New — Agent flow diagram with animations |
| `ui/src/components/chat/trace-timeline.tsx` | New — Scrollable event timeline |
| `ui/src/pages/chat/index.tsx` | Modified — panel toggle, trace fetch on message complete |
| `ui/src/layouts/app-layout.tsx` | Modified — sidebar agent indicator |
| `ui/src/lib/types.ts` | Modified — TraceSpan types |
| `ui/src/lib/agent-activity-store.ts` | New — Global store for agent activity |

### Phase 2 (Real-Time Trace Events)
| File | Action |
|------|--------|
| `src/api/routes/openai_compat.py` | Modified — `_build_trace_events()` helper + SSE emission |
| `ui/src/api/client.ts` | Modified — `StreamChunk` trace variant + parser |
| `ui/src/lib/trace-event-handler.ts` | New — Maps trace events to activity state |
| `ui/src/pages/chat/index.tsx` | Modified — Handle trace events in stream loop |
| `ui/src/components/InlineAssistant.tsx` | Modified — Handle trace events with local indicator |

### Test Files (Phase 2)
| File | Tests |
|------|-------|
| `tests/unit/test_trace_events.py` | 15 tests — `_build_trace_events` + SSE emission |
| `ui/src/api/__tests__/client.test.ts` | 2 new tests — trace event parsing |
| `ui/src/lib/__tests__/trace-event-handler.test.ts` | 9 tests — event-to-activity mapping |

## Out of Scope

- True real-time streaming mid-workflow (requires Feature 09 — real LLM streaming with LangGraph node callbacks)
- Trace comparison between messages
- Full MLflow trace viewer (use MLflow UI for that)
- Agent topology for non-chat workflows (discovery, optimization)
