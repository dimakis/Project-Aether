# Feature Specification: Natural Language Automation Builder

**Feature Branch**: `feat/36-nl-automation-builder`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "Conversational automation creation -- describe behavior in plain English, system generates, validates, tests, and deploys with HITL approval."

## User Scenarios & Testing

### User Story 1 - Conversational Automation Creation (Priority: P1)

As a user, I want to describe an automation in natural language (e.g., "turn off all lights at 10pm") and have the system generate valid HA automation YAML through a guided conversation.

**Why this priority**: Core value proposition -- the primary user journey.

**Independent Test**: Send a natural language automation request through chat, verify the system asks clarifying questions if needed, generates valid YAML, and presents it for approval.

**Acceptance Scenarios**:

1. **Given** I say "turn off the living room lights at 10pm every night", **When** the automation builder workflow runs, **Then** it generates a time-triggered automation targeting the correct entity with turn_off action.
2. **Given** I say "turn off the lights when nobody is home", **When** the system needs clarification on which lights, **Then** it asks me to specify and suggests matching entities from the registry.
3. **Given** the generated YAML passes validation, **When** I see the preview, **Then** I can approve or reject the automation via the standard HITL flow.

---

### User Story 2 - Live Entity Validation (Priority: P1)

As a user, I want the system to validate that all entity IDs in my automation exist in HA and suggest corrections for typos or ambiguous references.

**Why this priority**: Prevents deployment failures from invalid entity references.

**Independent Test**: Request an automation referencing a misspelled entity, verify the system catches it and suggests the closest match.

**Acceptance Scenarios**:

1. **Given** I reference "light.livng_room" (typo), **When** validation runs, **Then** the system suggests "light.living_room" as a correction.
2. **Given** I reference "the kitchen light" (ambiguous), **When** validation runs, **Then** the system lists matching entities and asks me to confirm which one.
3. **Given** all entities are valid, **When** validation runs, **Then** the workflow proceeds to duplicate detection without interruption.

---

### User Story 3 - Duplicate Detection (Priority: P2)

As a user, I want the system to warn me if a similar automation already exists so I don't create duplicates or conflicts.

**Why this priority**: Prevents automation conflicts and redundancy.

**Independent Test**: Create an automation for "turn off lights at 10pm", then try to create another one. Verify the system warns about the existing one.

**Acceptance Scenarios**:

1. **Given** an automation already exists for the same entity and trigger, **When** I try to create a similar one, **Then** the system warns me and offers to modify the existing one instead.
2. **Given** no similar automation exists, **When** duplicate detection runs, **Then** the workflow proceeds silently.

---

### User Story 4 - YAML Validation and Deployment (Priority: P1)

As a user, I want the generated automation YAML to be structurally and semantically validated before deployment, using the existing HITL approval and Developer agent deployment pipeline.

**Why this priority**: Safety -- invalid YAML must never reach HA.

**Independent Test**: Generate an automation with an invalid service call, verify schema validation catches it before the preview step.

**Acceptance Scenarios**:

1. **Given** generated YAML has a structural error, **When** validation runs, **Then** the system regenerates with corrections.
2. **Given** generated YAML references a non-existent service, **When** semantic validation runs, **Then** the system flags the error and asks for correction.
3. **Given** I approve the automation, **When** deployment succeeds, **Then** I receive a push notification confirming deployment.

---

### Edge Cases

- User describes an automation that requires an entity type not present in HA: inform the user which entities/integrations are needed.
- User requests a blueprint-style automation (e.g., "motion-activated light"): generate the standard automation, not a blueprint.
- Generated YAML fails HA config check after deployment: surface the error and offer rollback.
- User abandons the conversation mid-flow: state is preserved in the LangGraph checkpoint for resumption.

## Requirements

### Functional Requirements

- **FR-001**: System MUST support natural language automation description as input.
- **FR-002**: System MUST validate all entity references against the live HA entity registry.
- **FR-003**: System MUST detect and warn about similar existing automations.
- **FR-004**: System MUST validate generated YAML structurally (Feature 26) and semantically (Feature 27).
- **FR-005**: System MUST present a preview of the automation before HITL approval.
- **FR-006**: Deployment MUST reuse the existing Developer agent and proposal pipeline.
- **FR-007**: System MUST send push notification on successful deployment (Feature 37).
- **FR-008**: Workflow MUST be registered as a chat workflow preset.

### Key Entities

- **AutomationBuilderState**: LangGraph typed dict with intent, entities, yaml_draft, validation_results, similar_automations.
- Reuses existing: AutomationProposal, HAEntity, HAAutomation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Simple automations (single trigger, single action) generated correctly 90%+ of the time.
- **SC-002**: Entity validation catches 100% of invalid entity references before deployment.
- **SC-003**: Duplicate detection identifies existing automations with matching trigger+entity combinations.
- **SC-004**: End-to-end flow (describe -> validate -> approve -> deploy) completes in under 30 seconds for simple automations.
