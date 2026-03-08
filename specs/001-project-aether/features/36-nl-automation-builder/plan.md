# Implementation Plan: Natural Language Automation Builder

**Feature**: [spec.md](./spec.md)
**Status**: Planned
**Date**: 2026-02-27

## Summary

A dedicated LangGraph workflow that guides users through automation creation conversationally. Validates entities against the live registry (kept fresh by Feature 35), detects duplicate automations, validates YAML (Features 26-27), and deploys via the existing proposal/Developer pipeline with push notification (Feature 37).

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: LangGraph, LangChain, FastAPI, SQLAlchemy (async)
**Storage**: PostgreSQL (existing entities: HAEntity, HAAutomation, AutomationProposal)
**Testing**: pytest with async fixtures, mock LLM responses
**Target Platform**: Linux server (Docker/K8s)

## Constitution Check

- **Safety First**: All automations go through HITL approval gate before deployment. Existing proposal lifecycle enforced.
- **Isolation**: No sandbox execution needed (YAML generation, not script execution).
- **Observability**: Workflow traced via MLflow. Each node creates a span.
- **State**: LangGraph state with PostgreSQL checkpointing for resumable conversations.

## Architecture

```
User: "Turn off lights at 10pm"
    |
    v
gather_intent_node (Architect LLM)
    |-- Extract: trigger, entities, actions
    |-- Clarify if ambiguous (loop back to user)
    v
validate_entities_node
    |-- Check each entity_id against ha_entities table
    |-- Fuzzy match for typos (Levenshtein distance)
    |-- Suggest corrections or confirm
    v
check_duplicates_node
    |-- Query ha_automations for similar trigger+entity combos
    |-- Warn user if match found, offer to modify existing
    v
generate_yaml_node (Architect LLM)
    |-- Generate HA automation YAML from validated intent
    v
validate_yaml_node
    |-- Structural validation (Feature 26: schema validator)
    |-- Semantic validation (Feature 27: entity/service checks)
    |-- Loop back to generate if errors
    v
preview_node
    |-- Present formatted YAML to user
    |-- Create AutomationProposal (PROPOSED)
    v
approval_gate (HITL interrupt)
    |-- Approved -> developer_deploy_node (existing)
    |-- Rejected -> gather_intent_node (refine)
    v
deploy + push notification (Feature 37)
```

## Key Design Decisions

- **Reuses existing infrastructure**: proposal system, Developer agent deployment, YAML validators, HITL approval gate.
- **Separate workflow**: Not shoehorned into conversation workflow. Registered as a workflow preset.
- **Entity validation from DB**: Uses `EntityRepository` against fresh data (Feature 35 event stream).
- **Fuzzy matching**: Simple Levenshtein distance for entity name suggestions. No external dependency needed.
- **New tool group**: `automation_builder` registered via Feature 34 tool registry.

## Files to Create

- `src/graph/workflows/automation_builder.py` -- Workflow graph definition
- `src/graph/state/automation_builder.py` -- `AutomationBuilderState` typed dict
- `src/graph/nodes/automation_builder.py` -- Node implementations
- `src/tools/automation_builder_tools.py` -- Validation and detection tools
- `tests/unit/graph/test_automation_builder_nodes.py` -- Node tests
- `tests/unit/tools/test_automation_builder_tools.py` -- Tool tests

## Files to Modify

- `src/graph/workflows/__init__.py` -- Register new workflow
- `src/tools/registry.py` -- Add `automation_builder` tool group
- `src/agents/architect/agent.py` -- Add routing hint for automation builder intent
