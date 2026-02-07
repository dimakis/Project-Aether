**Completed**: 2026-02-07

# Feature: Intelligent Optimization & Multi-Agent Collaboration

**Status**: Complete  
**Priority**: P3  
**User Story**: US5  
**Migrated from**: `specs/001-project-aether/tasks.md` Phase 6b  
**Depends on**: US2 (Architect), US3 (Data Scientist)

## Goal

Extend the Data Scientist with behavioral analysis, automation gap detection, and agent-to-agent communication with the Architect for intelligent automation suggestions.

## Description

The Data Scientist gains the ability to analyze logbook data for behavioral patterns, detect manual actions that could be automated, score automation effectiveness, and discover entity correlations. Through tool-delegation, the Data Scientist can propose automation suggestions to the Architect, who refines them into full proposals for user approval via the existing HITL workflow.

## Independent Test

DS analyzes usage patterns, identifies automation opportunities, collaborates with Architect to propose optimized automations.

## MCP Tools Used

- `get_history` — historical data for correlation analysis
- `/api/logbook` (new) — logbook entries for behavioral analysis
- `list_automations` — automation metadata
- `list_entities` — entity context

## Design Decisions

### Reconciliation with Feature 08-C (2026-02-07)

Feature 08-C (Model Routing & Multi-Agent) implemented a simpler approach to multi-agent
communication that supersedes the originally planned AgentCoordinator/AgentMessage architecture.
The following decisions apply:

**1. Tool-delegation instead of AgentCoordinator**

The original plan called for `src/agents/coordinator.py` with an `AgentCoordinator` class
for agent registration, inter-agent queries, handoffs, and insight broadcasting. Feature 08-C
demonstrated that the existing tool-delegation pattern (agents invoke each other via tools
in `src/tools/agent_tools.py` with model context propagation) is simpler and sufficient for
a single-user system. No coordinator class is needed.

**2. Structured state instead of AgentMessage queue**

The original plan called for an `AgentMessage` model with message types (query, response,
handoff, insight) and an async message queue. Feature 08-C showed that structured tool
returns (e.g., the `automation_suggestion` field on `AnalysisState`) provide equivalent
communication without the complexity of a message queue. For single-user, single-session
operation, synchronous tool delegation is sufficient.

**3. AutomationSuggestion in state.py instead of ds_architect_bridge.py**

Rather than a separate `ds_architect_bridge.py` module, the `AutomationSuggestion` Pydantic
model is added directly to `src/graph/state.py`. The suggestion-to-proposal conversion logic
lives in `src/tools/agent_tools.py` (the `propose_automation` tool) and `src/agents/architect.py`
(the `receive_suggestion()` method). This keeps the architecture flat and follows the existing
pattern where agent delegation tools live in `agent_tools.py`.

**4. Reuse of reverse-communication pattern**

The `AnalysisState.automation_suggestion` field (already implemented in US3) provides
the mechanism for the Data Scientist to signal automation opportunities back to the calling
agent. This feature extends that pattern from a plain string to a structured
`AutomationSuggestion` model, enabling richer proposals.

**Reference**: See `features/08-C-model-routing-multi-agent/` for full rationale.

## MCP Gap Report (Expected)

- `/api/logbook` available via HA REST API
- `get_history` sufficient for correlation analysis
- `list_automations` provides automation metadata
- Automation trigger counts may require recorder database for accuracy
- Real-time pattern detection requires `subscribe_events` MCP tool
