# Implementation Plan: Intelligent Optimization & Multi-Agent Collaboration

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-02-06 (migrated from project tasks.md)

## Summary

Extend the Data Scientist agent with behavioral analysis capabilities and create a multi-agent collaboration framework that enables the DS to propose automation suggestions to the Architect.

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

New InsightType values: AUTOMATION_GAP, AUTOMATION_INEFFICIENCY, CORRELATION, DEVICE_HEALTH, COST_SAVING, BEHAVIORAL_PATTERN

### Agent-to-Agent Communication

- `src/agents/coordinator.py` — AgentCoordinator for registration, queries, handoffs, insight broadcasting
- `AgentMessage` model in state.py
- Inter-agent tools in `src/tools/agent_tools.py`

### DS-Architect Integration

- `src/agents/ds_architect_bridge.py` — AutomationSuggestion model, suggestion-to-proposal flow
- Extended ArchitectAgent to handle DS suggestions
- Combined DS analysis → Architect proposal workflow

### API & CLI

- `src/api/routes/optimization.py` — optimization endpoints
- `aether optimize` and `aether analyze behavior` CLI commands

## Constitution Check

- **Safety First**: Automation suggestions go through existing HITL approval
- **Isolation**: Analysis scripts run in gVisor sandbox
- **Observability**: All agent interactions traced via MLflow
- **State**: LangGraph for workflow state, PostgreSQL for persistence
