# Implementation Plan: Streaming Tool Executor Refactor

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-02-13

## Summary

Decompose `ArchitectWorkflow.stream_conversation` (~340 lines, architect.py L988-1328) into 5 focused components. Phase 1 is a pure refactor with no behavior change. Phase 2 introduces `ProgressMuxer` for parallel streaming tool execution.

## Architecture

### Current flow (monolithic)

```
stream_conversation (340 lines)
  ├── Build messages + entity context
  ├── First astream → accumulate tokens + tool chunks [DUPLICATED]
  ├── while tool_calls_buffer:
  │     ├── Parse buffer → full tool calls
  │     ├── For each tool (sequential):
  │     │     ├── Classify mutating vs read-only
  │     │     ├── Setup progress_queue + execution_context
  │     │     ├── asyncio.create_task(tool.ainvoke)
  │     │     ├── Drain progress_queue while running (asyncio.wait)
  │     │     └── Drain remaining, yield tool_end
  │     ├── Build follow-up messages
  │     ├── Follow-up astream → accumulate tokens + tool chunks [DUPLICATED]
  │     └── Break if no more tool calls
  ├── Fallback content generation
  └── Inline proposal extraction + yield state
```

### Target flow (composed)

```
stream_conversation (~60 lines)
  ├── Build messages + entity context
  ├── StreamConsumer.consume(astream) → yields tokens, returns tool_call_chunks
  ├── while tool_calls_buffer:
  │     ├── ToolCallParser.parse(buffer) → typed tool calls
  │     ├── ToolDispatcher.execute(tool_calls, tools) → yields StreamEvents
  │     │     └── (Phase 2) ProgressMuxer for parallel read-only tools
  │     ├── Build follow-up messages
  │     ├── StreamConsumer.consume(follow_up_astream)
  │     └── Break if no more tool calls
  ├── ProposalTracker.extract(content, tool_results) → proposals
  └── yield state
```

## Implementation Details

### Phase 1 — Extract and decompose

All new components live in `src/agents/streaming/`.

**StreamConsumer** (`src/agents/streaming/consumer.py`)
- Async generator: consumes `astream`, yields `StreamEvent(type="token")`, returns accumulated tool call buffer
- Eliminates the duplicated block at L1048-1071 and L1259-1277

**ToolCallParser** (`src/agents/streaming/parser.py`)
- Pure function: `parse(tool_calls_buffer) -> list[ParsedToolCall]`
- Extracts the JSON decoding + buffer merging logic at L1081-1107
- `ParsedToolCall` dataclass: name, args (dict), id, is_mutating (bool)

**ToolDispatcher** (`src/agents/streaming/dispatcher.py`)
- Async generator: takes parsed tool calls, tool lookup, settings
- Manages per-tool `execution_context`, `progress_queue`, timeout/deadline logic
- Yields `StreamEvent` (tool_start, progress, tool_end, approval_required)
- Encapsulates the 90-line nested async flow at L1108-1208

**ProposalTracker** (`src/agents/streaming/proposals.py`)
- Extracts proposal detection + `_create_proposal` calls from L1297-1328
- Takes collected_content + tool_results, returns proposal summaries

**StreamOrchestrator** (refactored `stream_conversation`)
- Thin composition of the above components
- Retains the multi-turn while loop and message building
- ~60 lines

### Phase 2 — Parallel streaming tool execution

**ProgressMuxer** (`src/agents/streaming/muxer.py`)
- Takes N `asyncio.Queue[ProgressEvent]`, yields events in arrival order
- Uses `asyncio.wait` on N `queue.get()` tasks with FIRST_COMPLETED
- Guarantees per-tool event ordering (events from tool A arrive in order; interleaving with tool B is fine)

**ToolDispatcher update**
- Classify tools: read-only tools run via `asyncio.gather` with individual progress queues
- Mutating tools (require approval) still run sequentially
- ProgressMuxer merges events from concurrent tools

## Files Changed

- `src/agents/streaming/__init__.py` — New package, public exports
- `src/agents/streaming/consumer.py` — StreamConsumer
- `src/agents/streaming/parser.py` — ToolCallParser + ParsedToolCall
- `src/agents/streaming/dispatcher.py` — ToolDispatcher
- `src/agents/streaming/proposals.py` — ProposalTracker
- `src/agents/streaming/muxer.py` — ProgressMuxer (Phase 2)
- `src/agents/architect.py` — Refactor stream_conversation to use new components
- `tests/unit/streaming/test_consumer.py` — StreamConsumer tests
- `tests/unit/streaming/test_parser.py` — ToolCallParser tests
- `tests/unit/streaming/test_dispatcher.py` — ToolDispatcher tests
- `tests/unit/streaming/test_proposals.py` — ProposalTracker tests
- `tests/unit/streaming/test_muxer.py` — ProgressMuxer tests (Phase 2)
- `tests/unit/streaming/test_orchestrator.py` — Integration test of composed pipeline

## Risks

- **Regression in SSE event ordering**: Mitigated by Phase 1 being a pure refactor with full existing test pass
- **Progress queue semantics change**: ProgressMuxer must preserve per-tool ordering invariant; dedicated fuzz/property tests recommended
- **execution_context contextvar propagation**: Each tool task needs its own contextvar copy; verify via asyncio.create_task (inherits by default in Python 3.12+)
