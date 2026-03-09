---
name: "Domain Message Types — Decouple from LangChain"
overview: |
  Replace LangChain message types (HumanMessage, AIMessage, ToolMessage, SystemMessage) as
  the internal lingua franca with project-owned Pydantic models. LangChain types remain at the
  LLM boundary only (ResilientLLM / LangGraph nodes). This isolates the domain from upstream
  serialization-format changes and simplifies the A2A wire format, checkpoint storage, and
  conversation history.
status: draft
priority: high
estimated_effort: "L (multi-sprint)"
risk: "Medium — wide blast radius across agents, state, serialization, and tests"
---

# 1. Problem

LangChain `BaseMessage` subclasses are imported in 40+ files spanning agents, graph state,
A2A serialization, API routes, CLI, and tests. If LangChain changes their serialization format
(which has happened multiple times), it breaks checkpoints, the A2A wire format, the database
reconstruction path, and the conversation API — all at once.

Additionally, `src/api/routes/chat.py` line ~316 already has a bug where assistant messages
from DB are reconstructed with `type("AIMessage", (), {...})()` instead of real `AIMessage`,
which can break `add_messages` and other code expecting proper LangChain types.

# 2. Target Architecture

```
┌──────────────────────────────────────────────────────┐
│                   External boundary                  │
│  ResilientLLM  ←→  LangChain BaseMessage types       │
│  LangGraph add_messages (if retained)                │
└──────────────┬───────────────────────────┬───────────┘
               │  to_langchain() / from_langchain()    │
┌──────────────▼───────────────────────────▼───────────┐
│                   Internal domain                    │
│  AetherMessage  (role, content, tool_calls, …)       │
│  Used in: state, A2A wire, DB reconstruction, API,   │
│           agents (message building), tests           │
└──────────────────────────────────────────────────────┘
```

# 3. Plan

## Phase 1 — Define domain message types (src/models/messages.py)

- [ ] Create `AetherMessage` Pydantic model with fields:
  - `role: Literal["system", "human", "ai", "tool"]`
  - `content: str | list[ContentBlock]`  (text or multimodal blocks)
  - `name: str | None`
  - `tool_calls: list[ToolCallBlock] | None`
  - `tool_call_id: str | None`  (for role=tool only)
  - `id: str | None`  (message ID for deduplication)
  - `metadata: dict[str, Any]`  (extensible)
- [ ] Create `ToolCallBlock` model: `id`, `name`, `args: dict`
- [ ] Create `ContentBlock` union type for future multimodal support
- [ ] Export from `src/models/__init__.py`

## Phase 2 — Conversion layer (src/models/langchain_compat.py)

- [ ] `to_langchain(msg: AetherMessage) -> BaseMessage` — maps role → class
- [ ] `from_langchain(msg: BaseMessage) -> AetherMessage` — extracts role, content, tool_calls
- [ ] `to_langchain_many(msgs) -> list[BaseMessage]`
- [ ] `from_langchain_many(msgs) -> list[AetherMessage]`
- [ ] Handle edge cases: `AIMessageChunk`, `ToolMessage` with artifact, `FunctionMessage` (legacy)
- [ ] Unit tests with round-trip property: `from_langchain(to_langchain(m)) == m`

## Phase 3 — Migrate A2A serialization (lowest risk, highest value)

- [ ] Replace `dumpd` / `load` in `a2a_service.py` with `AetherMessage.model_dump()` / `AetherMessage.model_validate()`
- [ ] `pack_state_to_data()`: convert `state.messages` → `[m.model_dump() for m in domain_messages]`
- [ ] `_extract_state_from_context()`: reconstruct `AetherMessage` from plain dicts, then `to_langchain_many` at graph entry
- [ ] Update A2A tests

## Phase 4 — Migrate conversation history & DB reconstruction

- [ ] `src/api/routes/chat.py`: build `list[AetherMessage]` from DB rows; convert to LangChain only at graph entry
- [ ] `src/cli/commands/chat.py`: same pattern
- [ ] Fix the `type("AIMessage", ...)` bug in chat.py
- [ ] `src/api/routes/openai_compat/utils.py`: `_convert_to_langchain_messages` → convert OpenAI → AetherMessage → LangChain

## Phase 5 — Migrate agents (message building)

- [ ] In each agent's `_build_messages` / prompt assembly, construct `list[AetherMessage]`
- [ ] Convert to LangChain only at `llm.ainvoke()` / `llm.astream()` call site
- [ ] Replace `isinstance(msg, HumanMessage)` checks with `msg.role == "human"`
- [ ] Affected files (14 agent files): orchestrator, architect/agent, architect/review,
      architect/workflow, knowledge, data_scientist/agent, dashboard_designer,
      energy_analyst, behavioral_analyst, diagnostic_analyst, analyst_config_mixin,
      base_analyst, developer, librarian

## Phase 6 — Migrate graph state (most coupled to LangGraph)

- [ ] If LangGraph is retained: keep `MessageState.messages` as `list[AnyMessage]` but convert
      at graph entry/exit boundaries only. Internal node functions work with AetherMessage.
- [ ] If LangGraph is dropped: replace `MessageState` with `messages: list[AetherMessage]`
      and handle the `add_messages` reducer logic manually (dedup by ID, append)
- [ ] Update `traced_node` wrappers if they inspect message types

## Phase 7 — Migrate tests

- [ ] Update unit tests to construct `AetherMessage` instead of LangChain types
- [ ] Keep a small set of integration tests that verify the LangChain conversion layer

# 4. Migration Strategy

**Parallel-safe approach**: Phases 1–2 are additive (no existing code changes). Phases 3–5
can proceed independently — each is a self-contained PR. Phase 6 depends on the LangGraph
decision. Phase 7 follows each phase incrementally.

**Rollback**: The conversion layer is bidirectional, so any phase can be reverted by
switching back to direct LangChain usage.

# 5. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LangGraph `add_messages` requires LangChain types | Convert at graph boundary; keep Phase 6 last |
| Checkpoint deserialization of old data | LangGraph handles its own checkpoint serde; not affected until Phase 6 |
| A2A backward compatibility | Version the wire format; support reading old `_lc_messages` format during migration |
| Test coverage gap | Round-trip property tests in Phase 2; incremental migration per phase |

# 6. Success Criteria

- Zero direct imports of `langchain_core.messages` outside of `src/models/langchain_compat.py`
  and `src/llm/` (and LangGraph graph definitions if retained)
- A2A wire format uses plain JSON-serializable dicts (no LangChain `dumpd`)
- DB reconstruction uses `AetherMessage` intermediary
- All existing tests pass
