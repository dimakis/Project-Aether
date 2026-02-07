# Implementation Plan: Intelligent Optimization & Multi-Agent Collaboration

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-02-06 (migrated from project tasks.md)  
**Updated**: 2026-02-07 (reconciled with feature 08-C decisions)

## Summary

Extend the Data Scientist agent with behavioral analysis capabilities and enable DS-to-Architect automation suggestions via tool-delegation.

## Reconciliation with Feature 08-C

Feature 08-C (Model Routing & Multi-Agent, completed 2026-02-07) implemented a simpler
tool-delegation pattern for multi-agent communication. This supersedes the originally
planned AgentCoordinator, AgentMessage, and ds_architect_bridge module:

- **AgentCoordinator** → Cancelled. Tool-delegation via `agent_tools.py` handles coordination.
- **AgentMessage model** → Cancelled. Structured tool returns suffice.
- **ds_architect_bridge.py** → Simplified. `AutomationSuggestion` model lives in `state.py`.
- **Inter-agent tools** → Adapted. Add `propose_automation` to existing `agent_tools.py`.

See [spec.md Design Decisions](./spec.md) for full rationale.

## Technical Approach

### New MCP Capabilities

- `get_logbook()` method on MCPClient — fetch logbook entries from `/api/logbook/{timestamp}`
- `src/mcp/logbook.py` — LogbookHistoryClient with parsing, filtering, and aggregation
- Logbook parsers in `src/mcp/parsers.py`

### New Analysis Types

Extend `AnalysisType` enum with: BEHAVIOR_ANALYSIS, AUTOMATION_ANALYSIS, AUTOMATION_GAP_DETECTION, CORRELATION_DISCOVERY, DEVICE_HEALTH, COST_OPTIMIZATION

### Data Scientist Extensions

- `src/mcp/behavioral.py` — BehavioralAnalysisClient (button usage, automation effectiveness, correlations, gap detection, device health)
- Extended analysis prompts for each new type
- `_collect_behavioral_data()` method for logbook aggregation

### Insight Types Extension

New InsightType values: AUTOMATION_GAP, AUTOMATION_INEFFICIENCY, CORRELATION, DEVICE_HEALTH, BEHAVIORAL_PATTERN (COST_SAVING already exists)

### Agent-to-Agent Communication (Simplified per 08-C)

- `propose_automation` tool in `src/tools/agent_tools.py` — DS proposes automation to Architect via tool delegation
- `AutomationSuggestion` Pydantic model in `src/graph/state.py` — structured suggestion with pattern, entities, trigger, action, confidence, evidence
- Existing `analyze_energy`/`diagnose_issue` tools already handle Architect→DS delegation

### DS-Architect Integration (Simplified per 08-C)

- `AutomationSuggestion` model in `src/graph/state.py` replaces separate bridge module
- `ArchitectAgent.receive_suggestion()` method accepts structured suggestions
- `propose_automation` tool in `agent_tools.py` drives the suggestion-to-proposal flow
- Combined DS analysis → Architect proposal via optimization workflow graph

### API & CLI

- `src/api/routes/optimization.py` — optimization endpoints
- `aether optimize` and `aether analyze behavior` CLI commands

## Constitution Check

- **Safety First**: Automation suggestions go through existing HITL approval
- **Isolation**: Analysis scripts run in gVisor sandbox
- **Observability**: All agent interactions traced via MLflow
- **State**: LangGraph for workflow state, PostgreSQL for persistence
