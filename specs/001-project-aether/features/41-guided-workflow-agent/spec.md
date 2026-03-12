# Feature Specification: Guided Workflow Agent

**Feature Branch**: `feat/41-guided-workflow-agent`
**Created**: 2026-03-12
**Status**: Draft
**Depends on**: Feature 36 (NL Automation Builder — state, nodes, tools exist but are not exposed)
**Input**: User request: "I want the workflows to be guided with a dedicated agent."

## Problem Statement

Feature 36 implemented the automation builder workflow (LangGraph graph, nodes, tools, state) but it was never wired to an API endpoint, chat preset, or UI. Users currently create automations through free-form chat with the Architect agent, which requires them to know HA automation structure. There is no guided, step-by-step experience and no way to invoke the automation builder at all.

Two gaps need filling:

1. **Guided mode** — a dedicated agent that walks users through automation creation step by step (trigger, entities, conditions, actions), with live validation and previews at each stage.
2. **Manual instruction** — users who prefer free-form chat should be able to say "create an automation that..." to the Architect, which routes the intent to the automation builder workflow automatically.

## User Scenarios & Testing

### User Story 1 — Guided Automation Creation via Dedicated Agent (Priority: P1)

As a user, I want to select "Create Automation" from the chat preset picker and be guided through each step (describe intent, confirm entities, review conditions, preview YAML, approve/deploy) interactively.

**Acceptance Scenarios**:

1. **Given** I select the "Create Automation" preset, **When** I type "turn off lights at 10pm", **Then** the agent extracts intent, validates entities, and presents a step-by-step summary before generating YAML.
2. **Given** the agent asks me to confirm entities, **When** I correct an entity name, **Then** it re-validates and proceeds with the corrected entity.
3. **Given** the agent generates YAML, **When** I see the preview, **Then** I can approve (creating a proposal), request modifications, or cancel.
4. **Given** I approve, **Then** a proposal is created via the existing proposal pipeline and I'm directed to the proposals page.

### User Story 2 — Architect Routes to Automation Builder (Priority: P1)

As a user, I want to tell the Architect "create an automation that turns off lights when nobody is home" in general chat and have it automatically route to the automation builder workflow.

**Acceptance Scenarios**:

1. **Given** I send an automation-creation intent in general chat, **When** the orchestrator classifies the intent, **Then** it routes to the automation builder workflow (not free-form Architect).
2. **Given** the automation builder handles my request, **When** it needs clarification, **Then** it asks within the same chat session.
3. **Given** the builder generates valid YAML, **Then** it creates a proposal via `seek_approval` and informs me.

### User Story 3 — Step Progress UI (Priority: P2)

As a user, I want to see which step I'm on during guided automation creation (intent, entities, duplicates, YAML, preview) so I know the progress.

**Acceptance Scenarios**:

1. **Given** the automation builder is running, **When** each node completes, **Then** the activity panel shows the current step name and progress.
2. **Given** validation errors occur, **When** the agent loops back, **Then** the step indicator shows the regression clearly.

### Edge Cases

- User starts guided flow then switches to a different chat session: state is checkpointed and can be resumed.
- User describes something that isn't an automation (e.g. "tell me the weather"): agent recognizes this and redirects to Architect.
- User requests a complex automation (multiple triggers, parallel actions): agent handles multi-step intent extraction.
- The automation builder generates invalid YAML 3 times: agent gives up, presents best attempt, and suggests manual editing.

## Requirements

### Functional Requirements

- **FR-001**: Automation builder workflow MUST be invocable via a chat workflow preset ("Create Automation").
- **FR-002**: Orchestrator MUST route automation-creation intents to the automation builder (not Architect).
- **FR-003**: Automation builder MUST create proposals via `seek_approval` (reusing existing proposal pipeline).
- **FR-004**: Each step of the builder MUST stream status updates to the activity panel.
- **FR-005**: Builder MUST support multi-turn clarification within a single chat session.
- **FR-006**: Builder MUST checkpoint state to PostgreSQL for resumability.

### Non-Functional Requirements

- **NFR-001**: Step transitions should complete within 5 seconds for simple automations.
- **NFR-002**: All nodes traced via MLflow (existing `traced_node` wrapper).

### Key Entities

- **AutomationBuilderState** (exists): Extended if needed for streaming step updates.
- Reuses: AutomationProposal, HAEntity, workflow presets.

## Success Criteria

- **SC-001**: "Create Automation" preset appears in the chat workflow picker.
- **SC-002**: Simple automations complete end-to-end (NL -> preview -> proposal) within 30 seconds.
- **SC-003**: Orchestrator correctly routes 90%+ of automation-creation intents to the builder.
- **SC-004**: Activity panel shows step progress during guided flow.
