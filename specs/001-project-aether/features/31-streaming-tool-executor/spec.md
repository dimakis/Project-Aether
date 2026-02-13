# Feature: Streaming Tool Executor Refactor

**Status**: Proposed  
**Priority**: P1  
**Depends on**: US2 (Architect), Feature 02 (Diagnostic Collaboration)

## Goal

Decompose the monolithic `stream_conversation` method (~340 lines) in `src/agents/architect.py` into modular, independently testable components and unlock parallel streaming tool execution without breaking real-time SSE event ordering.

## Problem Statement

`ArchitectWorkflow.stream_conversation` (lines 987-1328) is the primary code path for all user interactions. It handles 6 distinct responsibilities in a single async generator:

1. **LLM stream consumption** — accumulating tokens and tool call chunks
2. **Tool call parsing** — JSON decoding, buffering, merging chunks by index
3. **Tool execution with progress draining** — managing queues, timeouts, deadline tracking, and SSE event forwarding (~90 lines of nested async flow control)
4. **Multi-turn orchestration** — tracking iterations, building follow-up messages
5. **Proposal extraction** — inline JSON parsing, seek_approval tracking
6. **Fallback content generation** — empty-response handling, inline proposal persistence

### Specific issues

- **Duplicated code**: Stream chunk accumulation logic is copy-pasted between lines 1047-1071 (initial stream) and 1253-1273 (follow-up stream).
- **Sequential tool execution**: Tools within a single LLM turn execute one after another because each has its own progress queue managed inside a sequential for-loop. Independent tools (e.g. 3 entity lookups) cannot overlap.
- **Untestable**: The tool execution path (progress queue draining, timeout handling, SSE event forwarding) is deeply nested inside the generator and cannot be unit tested without mocking the entire streaming pipeline.
- **Fragile**: Adding new event types, changing timeout behavior, or modifying the multi-turn loop requires touching a single 340-line method with complex async control flow.

## Target Architecture

```
StreamOrchestrator
  ├── StreamConsumer          — Consume astream, yield tokens, accumulate tool call chunks
  ├── ToolCallParser          — Merge chunk buffers, JSON-decode args, classify mutating vs read-only
  ├── ToolDispatcher          — Execute tool(s) with execution_context, progress queues, timeouts
  │     └── ProgressMuxer     — Multiplex N progress queues into single ordered SSE stream
  └── ProposalTracker         — Track seek_approval results, extract inline proposals
```

### Component responsibilities

| Component | Input | Output | Testable in isolation |
|-----------|-------|--------|-----------------------|
| StreamConsumer | `astream` async iterator | `(tokens, tool_call_chunks)` | Yes — feed mock chunks |
| ToolCallParser | Raw chunk buffers | Parsed tool calls with typed args | Yes — pure function |
| ToolDispatcher | Parsed tool calls, tool lookup | `AsyncGenerator[StreamEvent]` | Yes — mock tools |
| ProgressMuxer | N `asyncio.Queue[ProgressEvent]` | Single ordered event stream | Yes — feed N queues |
| ProposalTracker | Tool results, collected content | Proposal summaries | Yes — pure logic |
| StreamOrchestrator | User message, state, session | `AsyncGenerator[StreamEvent]` | Yes — compose mocks |

### Key insight: ProgressMuxer unlocks parallelism

The UI does not depend on event ordering *between* different tools — it only needs events from each individual tool to arrive in order (start before end). A `ProgressMuxer` that takes N queues and yields events in arrival order preserves this invariant while allowing tools to run concurrently.

## Phases

**Phase 1 — Extract and decompose (no behavior change)**: Pull each responsibility into its own module/class. `stream_conversation` becomes a thin orchestrator that composes the components. All existing tests must continue to pass. The duplicated stream consumption code is eliminated.

**Phase 2 — Parallel streaming tool execution**: Introduce `ProgressMuxer`. Modify `ToolDispatcher` to run independent read-only tools via `asyncio.gather` with multiplexed progress events. Mutating tools (requiring approval) continue to execute sequentially.

## Success Criteria

- `stream_conversation` reduced from ~340 lines to ~60 lines
- Each component has dedicated unit tests
- Duplicated stream consumption code eliminated
- Phase 2: Independent tool calls within a single LLM turn execute in parallel
- No regression in SSE event ordering visible to the UI
- No change to the StreamEvent API contract

## Constitution Check

- **Safety First**: Mutating tools still require HITL approval; no change to approval flow
- **Isolation**: No change to sandbox execution
- **Observability**: Progress events and tracing preserved through refactor
- **State**: No change to state management
- **Reliability**: Each component independently testable; increased test coverage
