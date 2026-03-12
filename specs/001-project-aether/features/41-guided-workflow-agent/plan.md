# Implementation Plan: Guided Workflow Agent

**Feature**: [spec.md](./spec.md)
**Status**: Planned
**Date**: 2026-03-12

## Summary

Wire the existing Feature 36 automation builder workflow into the system as a dedicated, guided agent. This involves three layers: (1) a backend API route and chat preset, (2) orchestrator intent routing, and (3) conversational streaming with step progress in the activity panel.

## Technical Context

**Existing infrastructure (Feature 36)**:
- `src/graph/workflows/automation_builder.py` — LangGraph workflow with 6 nodes, HITL interrupt at preview
- `src/graph/nodes/automation_builder.py` — Node implementations (gather_intent, validate_entities, check_duplicates, generate_yaml, validate_yaml, preview)
- `src/graph/state/automation_builder.py` — `AutomationBuilderState` typed dict
- `src/tools/automation_builder_tools.py` — check_entity_exists, find_similar_automations, validate_automation_draft
- Registered in `src/graph/workflows/_registry.py` as `automation_builder`

**What's missing**:
- No API endpoint invokes the workflow
- No chat preset for "Create Automation"
- Orchestrator doesn't route automation intents to the builder
- No streaming/activity integration
- `preview_node` generates a `proposal_id` but doesn't actually call `seek_approval`

## Constitution Check

- **Safety First**: Automations go through HITL approval (interrupt_before=["preview"]) and the proposal pipeline. No deployment without user consent.
- **Isolation**: YAML generation only; no script execution.
- **Observability**: All nodes wrapped in `traced_node()`, MLflow spans.
- **State**: PostgreSQL checkpointing via `PostgresCheckpointer`.

## Architecture

### Two entry points

```
Entry 1: Chat preset "Create Automation"
    |
    POST /v1/chat/completions
    |-- agent="automation_builder"
    |-- Bypasses orchestrator, goes directly to builder
    v
    AutomationBuilderWorkflow.stream()

Entry 2: General chat with automation intent
    |
    POST /v1/chat/completions
    |-- agent="auto" (default)
    |-- Orchestrator.classify_intent()
    |-- intent = "create_automation"
    |-- Routes to AutomationBuilderWorkflow
    v
    AutomationBuilderWorkflow.stream()
```

### Streaming flow

```
User message
    |
    v
gather_intent_node
    |-- emit_job_status("Extracting automation intent...")
    |-- If needs_clarification: stream question back, wait for user reply
    v
validate_entities_node
    |-- emit_job_status("Validating entities...")
    |-- If errors: stream suggestions, loop to gather_intent
    v
check_duplicates_node
    |-- emit_job_status("Checking for duplicates...")
    |-- If found: stream warning, ask user to confirm
    v
generate_yaml_node
    |-- emit_job_status("Generating automation YAML...")
    v
validate_yaml_node
    |-- emit_job_status("Validating YAML...")
    |-- If errors (< 3 attempts): loop to generate
    v
preview_node
    |-- emit_job_status("Preparing preview...")
    |-- Stream YAML preview to user
    |-- Call seek_approval() to create proposal
    |-- Stream proposal link
    v
END
```

## Key Design Decisions

1. **Wrap workflow as an agent**: Create `AutomationBuilderAgent` that wraps the compiled LangGraph graph with streaming, job events, and message formatting. This parallels how `ArchitectWorkflow` wraps the conversation graph.

2. **Conversational multi-turn**: The HITL interrupt at `preview` pauses the graph. For clarification loops (needs_clarification, entity_errors), the gather_intent node already loops. We enhance it to stream the question as an SSE message and wait for the user's next message (resume from checkpoint).

3. **Orchestrator routing**: Add `"create_automation"` as an intent in `OrchestratorAgent.classify_intent()`. When detected, set `target_agent = "automation_builder"` in the `TaskPlan`.

4. **Proposal creation**: `preview_node` currently only generates a message. Enhance it to call `seek_approval()` to create an actual `AutomationProposal` in the database.

5. **Reuse streaming infrastructure**: Use the same SSE streaming as the conversation workflow (`/v1/chat/completions` with `stream=true`).

## How Users Can Create Automations

### Method 1: Guided Agent (via preset)

1. Open chat, select "Create Automation" preset from the workflow picker
2. Describe the automation: "Turn off all lights at 11pm"
3. Agent validates entities, checks for duplicates
4. Agent shows YAML preview
5. User approves -> proposal created
6. Navigate to Proposals page to deploy

### Method 2: Natural Language in Chat

1. Open chat (general mode or any preset)
2. Say: "Create an automation that turns off the lights when nobody is home"
3. Orchestrator routes to automation builder automatically
4. Same guided flow as Method 1

### Method 3: Manual via Architect

1. Open chat, select any preset
2. Tell the Architect exactly what you want:
   - "Use seek_approval to create an automation with this YAML: ..."
   - "Create a proposal for a time-triggered automation that..."
3. Architect generates YAML inline and uses `seek_approval` to create a proposal
4. This path is free-form — no step-by-step guidance

### Method 4: Registry Page

1. Go to the Registry page, Automations tab
2. Use the "Ask Architect" inline assistant
3. Say: "Create a new automation that locks the door when I leave"
4. Architect generates and proposes via `seek_approval`
5. Navigate to Proposals page to review and deploy

## Files to Create

- `src/agents/automation_builder/agent.py` — `AutomationBuilderAgent` wrapper (stream, resume, job events)
- `src/agents/automation_builder/__init__.py` — Module init
- `tests/unit/test_automation_builder_agent.py` — Agent wrapper tests
- `tests/unit/test_orchestrator_routing.py` — Intent routing tests

## Files to Modify

- `src/graph/nodes/automation_builder.py` — Enhance `preview_node` to call `seek_approval`; add step status emissions
- `src/agents/orchestrator.py` — Add `create_automation` intent, route to builder
- `src/api/routes/openai_compat/handlers.py` — Handle `agent="automation_builder"` in stream handler
- `src/api/routes/workflows.py` — Add "Create Automation" preset
- `ui/src/api/client/conversations.ts` — No changes (uses existing stream API)
- `ui/src/pages/chat/WorkflowPresetSelector.tsx` — Picks up new preset from API automatically
