# Tasks: Streaming Tool Executor Refactor

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1 — Extract and Decompose

### Package setup

- [x] T3101 Create `src/agents/streaming/__init__.py` with public exports
- [x] T3102 Create `tests/unit/streaming/__init__.py` and `conftest.py` with shared fixtures

### StreamConsumer

- [x] T3103 [P] Define `StreamConsumer` in `src/agents/streaming/consumer.py` — async generator consuming `astream`, yielding token events, returning tool call buffer
- [x] T3104 Add tests in `tests/unit/streaming/test_consumer.py` — token accumulation, tool chunk merging, mixed token+tool chunks, empty stream

### ToolCallParser

- [x] T3105 [P] Define `ParsedToolCall` dataclass and `parse()` in `src/agents/streaming/parser.py` — JSON decode args, classify mutating via `_is_mutating_tool`
- [x] T3106 Add tests in `tests/unit/streaming/test_parser.py` — valid args, malformed JSON fallback, mutating classification, multiple tool calls

### ToolDispatcher

- [x] T3107 [P] Define `ToolDispatcher` in `src/agents/streaming/dispatcher.py` — per-tool execution_context, progress_queue, timeout/deadline, yields StreamEvents
- [x] T3108 Add tests in `tests/unit/streaming/test_dispatcher.py` — tool_start/tool_end events, progress event forwarding, timeout handling, mutating tool approval_required

### ProposalTracker

- [x] T3109 [P] Define `ProposalTracker` in `src/agents/streaming/proposals.py` — extract seek_approval results, inline proposal detection
- [x] T3110 Add tests in `tests/unit/streaming/test_proposals.py` — proposal extraction, no-proposal path, multiple proposals

### Orchestrator integration

- [x] T3111 Refactor `stream_conversation` to compose StreamConsumer, ToolCallParser, ToolDispatcher, ProposalTracker
- [x] T3112 Add orchestrator integration test in `tests/unit/streaming/test_orchestrator.py` — full stream with tool calls, multi-turn loop, fallback path
- [x] T3113 Verify all existing architect streaming tests pass (no regressions)
- [x] T3114 Remove duplicated stream consumption blocks from architect.py

---

## Phase 2 — Parallel Streaming Tool Execution

### ProgressMuxer

- [x] T3115 [P] Define `ProgressMuxer` in `src/agents/streaming/muxer.py` — multiplex N progress queues into single ordered event stream
- [x] T3116 Add tests in `tests/unit/streaming/test_muxer.py` — single queue, multiple queues, per-tool ordering invariant, empty queues, queue completion

### Parallel dispatch

- [x] T3117 Update `ToolDispatcher` to run read-only tools via `asyncio.gather` with per-tool progress queues fed through ProgressMuxer
- [x] T3118 Add tests for parallel dispatch — verify wall time < sequential, event ordering preserved, mutating tools still sequential
- [x] T3119 Verify no regression in SSE event ordering via integration test

---

## Documentation

- [x] T3120 Update `docs/architecture.md` with streaming component diagram
- [x] T3121 Update `specs/001-project-aether/plan.md` streaming section

---

`[P]` = Pair with corresponding test task (TDD cycle)
