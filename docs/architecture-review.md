# Architecture Review: Project Aether

**Date**: 2026-02-10
**Branch**: `docs/architecture-review` (from `main` at `186eb60`)
**Scope**: Full health assessment + architecture readiness for Jarvis pivot (Features 29/30)
**Status**: Complete

---

## Executive Summary

Project Aether is a mature, well-tested HA-focused multi-agent system. Code quality is high: ruff and mypy pass cleanly, test coverage is broad (154 source modules, 180+ unit tests), and the existing healthcheck shows steady improvement. The codebase is ready for incremental evolution toward the Jarvis pivot.

However, the pivot from an Architect-centric HA tool to a domain-agnostic Orchestrator with dynamic agents and workflows requires changes across all layers. The **agent layer**, **routing**, **tool registry**, and **data schema** all need extension. No layer requires a rewrite -- the existing patterns are sound and extensible -- but several coupling points need to be loosened before Features 29/30 can land cleanly.

**Top risks**: (1) HITL enforcement is Architect-specific and must be centralized before adding mutation-capable domain agents, (2) Feature 23 (Agent Configuration) is half-implemented -- DB/API exist but runtime doesn't consume them, and (3) `workflows.py` at 1161 lines is the largest file and will grow further with dynamic compilation unless split first.

**Recommended approach**: Address the 8 pre-pivot refactoring items (Section 6) before starting Feature 30, then implement Feature 30 Phase 1 (Orchestrator + routing) before Feature 29 (dynamic composition).

---

## Table of Contents

1. [Current State Findings](#1-current-state-findings)
2. [Agent Layer Extensibility](#2-agent-layer-extensibility)
3. [Routing and Orchestration](#3-routing-and-orchestration)
4. [Workflow Composability](#4-workflow-composability)
5. [Data Layer Readiness](#5-data-layer-readiness)
6. [Security Implications](#6-security-implications)
7. [Observability and Tracing](#7-observability-and-tracing)
8. [Pre-Pivot Refactoring](#8-pre-pivot-refactoring)
9. [Risk Register](#9-risk-register)
10. [Suggested Implementation Order](#10-suggested-implementation-order)

---

## 1. Current State Findings

### 1.1 Code Quality

| Check | Status | Details |
|-------|--------|---------|
| Ruff linter | PASS | 0 issues across all source files |
| Mypy type checker | PASS | 0 issues in 176 source files |
| Deprecated APIs | PASS | 0 `datetime.utcnow` / `utcfromtimestamp` |
| TODO/FIXME/HACK | PASS | 0 remaining in `src/` (was 1) |

### 1.2 Codebase Scale

| Metric | Count |
|--------|-------|
| Source modules (excl. `__init__.py`) | 154 |
| Test files (unit + integration + E2E) | 200 |
| Unit tests | 180+ |
| Alembic migrations | 25 |
| Lines: `workflows.py` | 1161 |
| Lines: `agents/__init__.py` | 502 |
| Lines: `state.py` | 697 |
| Lines: `settings.py` | 289 |
| Lines: `api/main.py` | 467 |

### 1.3 Type Safety

**74 `Any` annotations** (down from 87 at last healthcheck). Key concentrations:

| Module | Count | Reason |
|--------|-------|--------|
| `api/routes/traces.py` | 12 | MLflow trace object handling |
| `llm.py` | 7 | Dynamic LLM kwargs |
| `schema/core.py` | 4 | Schema flexibility |
| `tracing/mlflow.py` | 4 | MLflow API |
| `tools/agent_tools.py` | 4 | Tool return types |
| `agents/__init__.py` | 5 | Base agent generics |
| Others (24 modules) | 38 | 1-3 each |

Improvement: `graph/nodes.py` (was 16) and `graph/workflows.py` (was 14) no longer contribute -- the refactoring into `graph/nodes/*.py` and type improvements resolved these.

### 1.4 Error Handling

**193 `except Exception` catches** (up from 112, proportional to new features).

| Area | Count | Notes |
|------|-------|-------|
| Tools (`src/tools/`) | 51 | Defensive; return error messages to LLM |
| Agents (`src/agents/`) | 37 | 12 in `__init__.py` (debug-logged w/ exc_info) |
| API routes | 34 | Standard HTTP error handling |
| Tracing (`src/tracing/`) | 25 | By design -- tracing must never crash the app |
| HA client (`src/ha/`) | 9 | Network resilience |
| Graph (`src/graph/`) | 9 | Workflow error handling |
| Other (sandbox, scheduler, CLI, DAL, LLM) | 28 | Mixed |

**Breakdown by severity**:
- ~162 logged (with `logger.error/warning/exception` or return error string)
- ~22 debug-logged (with `logger.debug` and `exc_info=True`)
- ~9 silent (return None, set default, or skip) -- mostly in `tracing/mlflow.py` (3, by design), `sandbox/runner.py` (1), `ha/behavioral.py` (1), `api/routes/traces.py` (1), others (3)

### 1.5 Thread Safety

| Singleton | File | Lock | Status |
|-----------|------|------|--------|
| `_engine` / `_session_factory` | `storage/__init__.py` | `threading.Lock` + double-checked | PASS |
| `get_ha_client()` | `ha/base.py` | `threading.Lock` + double-checked | PASS |
| `_discovery_instance` | `api/services/model_discovery.py` | None (startup-only access) | WARN |
| `SchedulerService._instance` | `scheduler/service.py` | None (set during startup) | PASS |
| `_app` | `api/main.py` | None (single-threaded startup) | PASS |

### 1.6 Rate Limiting

**29 rate-limited endpoints** across all LLM-backed and mutation routes. Coverage is comprehensive.

### 1.7 Stale References

`docs/code-healthcheck.md` and `docs/architecture.md` contain **27 references to `src/mcp/`** which was renamed to `src/ha/` in Feature 25. The exception hierarchy still references `MCPError` (now `HAClientError`).

---

## 2. Agent Layer Extensibility

### Current State

- `BaseAgent` provides tracing, progress emission, error handling, and abstract `invoke(state, **kwargs) -> dict`
- 8 concrete agents: Architect, Librarian, Developer, DataScientist, EnergyAnalyst, BehavioralAnalyst, DiagnosticAnalyst, DashboardDesigner
- `AgentRole` is a static enum with 10 values (includes `ORCHESTRATOR` already)
- Feature 23 infrastructure exists: `Agent` DB entity, `AgentConfigVersion`, `AgentPromptVersion`, config cache with `get_agent_runtime_config()`

### Gaps

| Gap | Impact | Effort |
|-----|--------|--------|
| **Feature 23 not wired to runtime** -- `tools_enabled`, `prompt_template`, `model_name` from config cache are unused by agents | HIGH -- blocks dynamic agent behavior | Medium |
| **No agent registry/factory** -- agents are imported explicitly; no way to instantiate by name | MEDIUM -- blocks dynamic agent creation | Low |
| **Tools hardcoded to Architect** -- only `get_architect_tools()` exists; no generic `get_tools_for_agent()` | HIGH -- blocks new domain agents | Medium |
| **AgentRole is static enum** -- new agents require code changes | LOW -- enum is easy to extend | Low |
| **AgentName literal outdated** -- `Literal["librarian", "categorizer", "architect", "developer", "data_scientist", "orchestrator"]` missing specialists | LOW -- only used in `Agent.create()` factory | Low |
| **ConversationState lacks `channel` and `active_agent`** | MEDIUM -- blocks routing and voice | Low |

### Recommendations

1. Wire `BaseAgent` (or subclasses) to consume `AgentRuntimeConfig` for model, temperature, prompt
2. Implement `get_tools_for_agent(agent_name)` that uses `tools_enabled` from config, falling back to agent-specific defaults
3. Add `channel: str | None` and `active_agent: str | None` to `ConversationState`
4. Add agent registry: `AGENT_REGISTRY: dict[str, type[BaseAgent]]` for name-to-class mapping
5. Update `AgentName` literal or remove it in favor of plain `str`

---

## 3. Routing and Orchestration

### Current State

Two separate chat paths exist:

| Path | Entry | Execution |
|------|-------|-----------|
| Chat API (primary) | `openai_compat.py` / `chat.py` | `ArchitectWorkflow` -> `ArchitectAgent` |
| LangGraph conversation | `run_conversation_workflow()` | `StateGraph`: architect_propose -> approval_gate -> deploy |

The Chat API path does **not** use LangGraph -- it calls `ArchitectWorkflow` directly. The LangGraph conversation workflow exists but is not used by the API.

`OrchestratorState` is defined in `state.py` with `intent`, `target_graph`, and per-graph result fields, but is **not used anywhere**.

### Orchestrator Insertion Points

**Option A (recommended)**: Insert before `ArchitectWorkflow` in the API routes:

```
Request → Orchestrator.classify(message) → 
  if agent=="auto": route by intent
  if agent==specific: bypass to that agent
→ Domain Agent (Architect, Knowledge, Research, Food)
```

**Option B**: Build a top-level LangGraph with Orchestrator as the entry node, using `OrchestratorState`. This is cleaner but requires migrating the chat API to use LangGraph.

### Gaps

| Gap | Notes |
|-----|-------|
| No `agent` field in `ChatCompletionRequest` | Feature 30 FR-002 requires this |
| No intent classification logic | Need LLM-based classifier in Orchestrator |
| `ArchitectWorkflow` is the only entry | Need generic `AgentWorkflow` or per-agent workflow resolution |
| No agent picker in UI | Feature 30 FR-005 |

---

## 4. Workflow Composability

### Current State

8 workflows in `WORKFLOW_REGISTRY`, all built imperatively:

```python
WORKFLOW_REGISTRY = {
    "discovery": build_discovery_graph,
    "discovery_simple": build_simple_discovery_graph,
    "conversation": build_conversation_graph,
    "analysis": build_analysis_graph,
    "optimization": build_optimization_graph,
    "team_analysis": build_team_analysis_graph,
    "dashboard": build_dashboard_graph,
    "review": build_review_graph,
}
```

All follow the same pattern: `StateGraph(XState)` -> `add_node` -> `add_edge` -> `compile`.

Nodes are in `src/graph/nodes/` with clear `async def node(state, **kwargs) -> dict` contracts. Dependencies (`session`, `ha_client`) are injected via wrapper closures.

### Feasibility of Declarative Composition

| Aspect | Status | Notes |
|--------|--------|-------|
| Node reusability | Good | Nodes are focused, self-contained functions |
| Dependency injection | Good | Already uses closure pattern for session/ha_client |
| State coupling | Moderate | Different state types per workflow (Discovery, Conversation, Analysis, Review, Dashboard) |
| Dynamic compilation | Feasible | `create_graph()` + `add_node/edge` maps to a declarative definition |
| Main blocker | State heterogeneity | Reusable nodes would need adapters or a shared base state |

A `WorkflowDefinition` model could describe graphs declaratively (nodes, edges, conditional routing). A `WorkflowCompiler` would resolve node references, validate topology, and produce `StateGraph` instances. The existing patterns make this feasible but state type diversity adds complexity.

### Recommendations

1. Split `workflows.py` (1161 lines) before adding dynamic compilation
2. Consider a `WorkflowDefinition` Pydantic model early -- even for static workflows
3. Build a `NodeManifest` registry from decorated node functions
4. Address state heterogeneity via adapters or a shared `BaseWorkflowState`

---

## 5. Data Layer Readiness

### Current State

- Clean SQLAlchemy 2.0 patterns with `Base`, `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin`
- 25 Alembic migrations, all additive
- JSONB used for flexible config fields
- `Agent` entity already has `active_config_version_id` and `active_prompt_version_id`

### Required Schema Extensions

| Change | Table | Type | Complexity |
|--------|-------|------|------------|
| `domain` | `agents` | `String(50)`, nullable | Low |
| `intent_patterns` | `agents` | `JSONB`, nullable | Low |
| `is_routable` | `agents` | `Boolean`, default `False` | Low |
| `capabilities` | `agents` | `JSONB`, nullable | Low |
| `channel` | `conversations` | `String(20)`, nullable | Low |
| `active_agent` | `conversations` | `String(50)` or FK, nullable | Low |
| `workflow_definitions` | New table | Full schema (id, name, config JSONB, status, version) | Low-Medium |

All changes are additive (nullable columns + new table). No existing data migration needed. Estimated: 1-2 Alembic migrations.

---

## 6. Security Implications

### Current Posture (Strong)

- JWT + API key auth with fail-closed in production
- HITL approval for all mutating HA actions
- gVisor sandbox for DS Team scripts (no network, read-only root)
- Security headers on all responses
- Rate limiting on all expensive endpoints
- Pydantic validation on all API inputs

### New Attack Surfaces from Jarvis Pivot

| Concern | Risk | Mitigation |
|---------|------|------------|
| **Intent classification manipulation** | HIGH | Prompt injection could steer routing to wrong agent. Validate intent against whitelist; constrain output format; audit routing decisions. |
| **HITL bypass via new agents** | HIGH | HITL is Architect-specific (`_READ_ONLY_TOOLS` whitelist). New mutation-capable agents (Food -> preheat oven) would bypass it. **Centralize mutation detection** in a shared module before adding domain agents. |
| **Dynamic agent creation** | MEDIUM | User-defined agents could have unsafe prompts or tool access. Require `is_dynamic=true` flag, `draft` status, and HITL approval for promotion. |
| **Dynamic workflow compilation** | MEDIUM | DB-sourced workflow definitions could produce unsafe graphs (loops, missing nodes). Validate topology at compile time; enforce max-step limits at runtime. |
| **Web search tools** | MEDIUM | Research Agent needs network access, breaking the no-network-for-agents assumption. Isolate web search in a dedicated tool with rate limiting and allowed-host restrictions. |
| **Cross-domain delegation** | LOW | Food -> Home delegation goes through tool calls. If tools enforce HITL, delegation is safe. Ensure HITL gates are tool-level, not agent-level. |

### Critical Pre-Pivot Action

**Centralize HITL enforcement**: Move mutation detection from per-agent (`_READ_ONLY_TOOLS` on Architect) to a shared `MutatingToolRegistry` that all agents use. This is the highest-priority security item.

---

## 7. Observability and Tracing

### Current State

- MLflow tracing with automatic parent-child via async ContextVars
- `BaseAgent.trace_span()` creates CHAIN spans per agent invocation
- `@trace_with_uri` decorates HA client methods as TOOL spans
- `ModelContext.parent_span_id` enables inter-agent trace linking
- `session_context()` correlates traces across a conversation
- Scorers: `agent_delegation_depth`, `tool_usage_safety`

### Readiness for Multi-Agent Routing

| Requirement | Status | Gap |
|-------------|--------|-----|
| Same-context delegation (Orchestrator -> Agent) | Works | None -- ContextVars propagate parent-child automatically |
| Intent classification spans | Not present | Add `orchestrator.classify_intent` span with confidence attributes |
| Routing decision spans | Not present | Add `orchestrator.route` span with `target_agent`, `reason` |
| Cross-domain delegation (Food -> Home via tool) | Works | Same async context preserves trace tree |
| Cross-process/cross-context | Not supported | Would need low-level `MlflowClient.start_span(parent_id=...)` |
| Intent confidence scoring | Not present | Add `span.set_attributes({"intent.confidence": ...})` |

### Recommendations

1. Add Orchestrator-specific spans (classify + route) with confidence attributes
2. Add an `orchestrator_routing` scorer that flags low-confidence routing
3. Keep single-process architecture for now -- cross-context tracing is a future concern

---

## 8. Pre-Pivot Refactoring

These items should be addressed **before** starting Feature 30 implementation:

| # | Item | Why | Effort | Priority |
|---|------|-----|--------|----------|
| R1 | **Centralize HITL enforcement** -- move mutation detection from Architect to shared `MutatingToolRegistry` | Security: new agents would bypass HITL without this | Medium | P0 |
| R2 | **Wire Feature 23 to runtime** -- agents consume `AgentRuntimeConfig` for model, temperature, prompt, tools | Feature 30 depends on DB-driven agent configuration | Medium | P0 |
| R3 | **Implement `get_tools_for_agent()`** -- generic tool resolution using `tools_enabled` config | Blocks adding new domain agents with per-agent tool sets | Medium | P0 |
| R4 | **Split `workflows.py`** into `workflows/discovery.py`, `workflows/conversation.py`, etc. | 1161 lines; will grow with Orchestrator and dynamic compilation | Low | P1 |
| R5 | **Add `channel` and `active_agent` to ConversationState** | Required by Feature 30 FR-006 | Low | P1 |
| R6 | **Add agent registry/factory** -- `AGENT_REGISTRY: dict[str, type[BaseAgent]]` | Enables instantiating agents by name from DB/config | Low | P1 |
| R7 | **Fix stale `src/mcp/` references in docs** | 27 references in healthcheck + architecture docs | Low | P2 |
| R8 | **Update `AgentName` literal** or remove in favor of `str` | Outdated, missing specialist agents | Low | P2 |

---

## 9. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| RR1 | HITL bypass -- new domain agent mutates HA without approval | High (if not addressed) | Critical | R1: Centralize HITL before adding agents |
| RR2 | Intent classification manipulation via prompt injection | Medium | High | Whitelist intents, constrain output format, audit decisions |
| RR3 | Feature 23 config not consumed -- agents ignore DB settings | High (known gap) | Medium | R2: Wire config to runtime before Feature 30 |
| RR4 | `workflows.py` becomes unmanageable with dynamic compilation | High | Medium | R4: Split before adding more workflows |
| RR5 | State type heterogeneity blocks workflow composition | Medium | Medium | Design shared base state or adapter pattern |
| RR6 | Backward compatibility regression -- existing HA flows break | Low | High | Comprehensive test suite (180+ unit tests) provides safety net; add Orchestrator integration tests |
| RR7 | Dynamic workflow/agent creation produces unsafe execution | Low | High | Topology validation, max-step limits, HITL for first execution |
| RR8 | Web search tools expose internal network | Low | High | Isolated tool with allowed-host policy, rate limiting |

---

## 10. Suggested Implementation Order

### Phase 0: Pre-Pivot Refactoring (before Feature 30)

1. R1: Centralize HITL enforcement
2. R2 + R3: Wire Feature 23 config + generic tool resolution
3. R4: Split `workflows.py`
4. R5 + R6: ConversationState extensions + agent registry
5. R7 + R8: Doc fixes + `AgentName` cleanup

### Phase 1: Feature 30 -- Domain-Agnostic Orchestration

1. OrchestratorAgent with intent classification
2. `agent` field in ChatCompletionRequest
3. KnowledgeAgent (simplest domain agent, validates routing)
4. AgentPicker in UI
5. Backward compatibility verification

### Phase 2: Feature 30 -- Domain Agents

1. ResearchAgent with web search tools
2. FoodAgent with cross-domain delegation
3. Voice pipeline documentation (HA Assist + Wyoming)
4. Jarvis personality + channel-aware responses

### Phase 3: Feature 29 -- Dynamic Workflow Composition

1. WorkflowDefinition model + NodeManifest
2. WorkflowCompiler (definition -> StateGraph)
3. Workflow CRUD API
4. Chat-based workflow composition
5. Dynamic agent creation
6. Workflow persistence + auto-routing

---

## Appendix: Feature 23 Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| DB schema (`Agent`, `AgentConfigVersion`, `AgentPromptVersion`) | Done | `tools_enabled` field exists |
| API routes (CRUD, promote, rollback, seed) | Done | Full lifecycle management |
| Config cache (`get_agent_runtime_config`, `invalidate`) | Done | Caching works |
| **Runtime consumption by agents** | **Not done** | Agents ignore config for model, temperature, prompt, tools |
| **`tools_enabled` usage** | **Not done** | Stored but never used when resolving tools |
| Agent seed data | Partial | Missing Knowledge, Research, Food, specialist agents |

This is the single most important gap to close before the Jarvis pivot. The infrastructure exists but is disconnected from agent runtime behavior.
