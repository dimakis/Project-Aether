# Feature Specification: Dynamic Workflow and Agent Composition

**Feature Branch**: `029-dynamic-workflow-composition`
**Created**: 2026-02-09
**Status**: Draft
**Input**: User description: "Being able to dynamically create new workflows and agents via chat/system review. The system should compose new capabilities from existing building blocks, with human approval, and remember them for future use."
**Depends on**: Feature 30 (Domain-Agnostic Orchestration -- Phases 1-2c), Feature 23 (Agent Configuration), Feature 26-27 (YAML Validation)
**Architecture Decisions**: `.cursor/plans/jarvis_pivot_architecture_aed12d48.plan.md` (Phase 2d)

## User Scenarios & Testing

### User Story 1 - Compose a Workflow via Chat (Priority: P1)

As a user, I want to describe a task in natural language and have the system design a new workflow from available building blocks, so I can automate novel multi-step processes without writing code.

**Why this priority**: This is the core value proposition -- the system extends its own capabilities via conversation. Without this, dynamic composition doesn't exist.

**Independent Test**: User asks "I want a workflow that checks humidity sensors, looks up energy prices, and adjusts HVAC settings." The system inspects the node manifest, designs a workflow graph, presents the proposed topology for approval, and upon approval compiles and executes it.

**Acceptance Scenarios**:

1. **Given** the node manifest contains `collect_energy_data`, `collect_behavioral_data`, `analyze_and_suggest`, and `present_recommendations` nodes, **When** the user asks the Architect to create a workflow combining energy and behavioral analysis, **Then** the system produces a valid `WorkflowDefinition` with correct nodes, edges, and routing.
2. **Given** a proposed `WorkflowDefinition` is pending approval, **When** the user approves it, **Then** the system compiles it into a LangGraph `StateGraph`, executes it, and returns results.
3. **Given** a proposed `WorkflowDefinition` is pending approval, **When** the user requests changes (e.g., "add a diagnostic check before the recommendation"), **Then** the system revises the definition and re-presents for approval.
4. **Given** the user requests a workflow requiring nodes that don't exist in the manifest, **When** the system detects the gap, **Then** it explains which capabilities are missing and suggests alternatives or asks for clarification.

---

### User Story 2 - Dynamic Agent Creation (Priority: P1)

As a user, I want to describe a new agent role and have the system create and register it, so I can extend the system with new specialized capabilities without editing code or config files.

**Why this priority**: Paired with workflow composition, agent creation completes the "self-extending system" vision. Users define both the workers (agents) and the processes (workflows).

**Independent Test**: User asks "Create a fitness coach agent that can access my health sensors and provide daily recommendations." The system composes an agent definition (system prompt, tool assignments, model config), presents it for approval, and upon approval registers it via the Feature 23 infrastructure.

**Acceptance Scenarios**:

1. **Given** the user describes a new agent role, **When** the system receives the request, **Then** it generates an agent definition with: system prompt, domain, tool assignments (selected from available tools), model config, intent patterns, and capabilities list.
2. **Given** a proposed agent definition is pending, **When** the user approves it, **Then** the agent is created in the DB with `status=draft` and `is_dynamic=true`, ready for promotion.
3. **Given** a dynamic agent has been promoted to `enabled`, **When** the Orchestrator receives a matching intent, **Then** it routes to the dynamic agent just like any built-in agent.
4. **Given** the user requests an agent that needs tools not available in the system, **When** the system detects this, **Then** it explains the limitation and suggests available tools that could approximate the need.

---

### User Story 3 - Workflow Persistence and Auto-Routing (Priority: P2)

As a user, I want workflows I've created to be saved and automatically triggered when I make similar requests in the future, so the system learns and improves over time.

**Why this priority**: Without persistence, every novel request requires re-composition. This transforms one-off compositions into lasting capabilities, but is an enhancement over the core P1 compose-and-execute flow.

**Independent Test**: User creates a "morning routine analysis" workflow via chat. The next day, the user says "run my morning routine analysis." The Orchestrator matches the intent pattern and runs the saved workflow without re-composition.

**Acceptance Scenarios**:

1. **Given** a workflow has been approved and executed, **When** the system saves it, **Then** it is stored in the `workflow_definitions` table with a name, description, intent patterns, and the full declarative config.
2. **Given** a saved workflow exists with intent pattern "morning routine", **When** the user says "run my morning analysis", **Then** the Orchestrator matches the intent and runs the saved workflow directly.
3. **Given** a user wants to see their custom workflows, **When** they access the workflows API or UI, **Then** they see a list of all saved workflows with status, last run, and creation date.
4. **Given** a user wants to modify a saved workflow, **When** they ask to update it (via chat or API), **Then** a new version is created, preserving the previous version for rollback.

---

### User Story 4 - Workflow Management API (Priority: P2)

As a developer or power user, I want CRUD API endpoints for workflow definitions, so I can manage custom workflows programmatically.

**Why this priority**: Enables both the UI and external integrations to manage workflows. Secondary to the core chat-based creation flow.

**Independent Test**: A developer can create, read, update, and delete workflow definitions via REST API calls, and the system validates the workflow schema on create/update.

**Acceptance Scenarios**:

1. **Given** a valid `WorkflowDefinition` JSON payload, **When** `POST /api/v1/workflows/definitions` is called, **Then** the workflow is validated, saved, and returned with an ID.
2. **Given** an invalid workflow config (e.g., orphan node, missing edge), **When** the API receives it, **Then** it returns a 422 with specific validation errors describing the topology problem.
3. **Given** a saved workflow exists, **When** `GET /api/v1/workflows/definitions/{id}` is called, **Then** the full definition including nodes, edges, and metadata is returned.
4. **Given** a saved workflow exists, **When** `DELETE /api/v1/workflows/definitions/{id}` is called, **Then** the workflow is soft-deleted and no longer appears in listings or routing.

---

### User Story 5 - Visual Workflow Editor (Priority: P3)

As a power user, I want to view and edit workflow graphs visually in the UI, so I can make fine-grained adjustments to workflow topology without describing changes in chat.

**Why this priority**: Powerful UX enhancement but requires significant frontend investment (React Flow integration). The chat-based creation (P1) and API (P2) provide full functionality without this.

**Independent Test**: User navigates to a workflow detail page and sees a visual graph rendering of the workflow. They can drag to rearrange, add/remove nodes from a palette, draw edges, and save changes.

**Acceptance Scenarios**:

1. **Given** a saved workflow definition, **When** the user opens its detail page, **Then** a visual graph is rendered showing nodes, edges, and conditional routing with labels.
2. **Given** the visual editor is open, **When** the user drags a node from the palette and connects it, **Then** the underlying `WorkflowDefinition` is updated and can be saved.
3. **Given** the user has made visual edits, **When** they click "Save", **Then** the updated definition is validated and persisted, with the previous version preserved for rollback.

---

### Edge Cases

- What happens when a composed workflow references a node that gets removed from the manifest in a future update? System should detect stale references at compile time and notify the user with a migration path.
- What happens when two users create workflows with overlapping intent patterns? The Orchestrator should use confidence scoring and present ambiguous matches as options to the user.
- What happens when a dynamic workflow enters an infinite loop (e.g., circular conditional routing)? The compiler must perform cycle detection during validation, and the runtime should enforce a max-step limit.
- What happens when a workflow depends on an agent that gets disabled? The compiler should check agent availability at compile time and warn if dependencies are unavailable.
- What happens when the node manifest changes (new nodes added, old ones deprecated)? Saved workflows should be re-validated on load; invalid ones are flagged for user review rather than silently broken.

## Requirements

### Functional Requirements

- **FR-001**: System MUST define a `WorkflowDefinition` schema (Pydantic model) that declaratively describes workflow graphs including nodes, edges, conditional routing, state schema reference, and compile options.
- **FR-002**: System MUST maintain a `NodeManifest` -- a typed registry of all available node functions with their input/output state contracts, descriptions, dependency requirements, and parameter schemas.
- **FR-003**: System MUST implement a `WorkflowCompiler` that takes a `WorkflowDefinition`, resolves node references from the manifest, validates topology (no orphan nodes, no unintended cycles, all edges connect valid nodes), and produces a compiled LangGraph `StateGraph`.
- **FR-004**: System MUST persist custom workflow definitions in a `workflow_definitions` DB table with: id, name, description, config (JSON), intent_patterns, state_schema, status (draft/active/archived), created_by, version, created_at, updated_at.
- **FR-005**: System MUST extend `get_workflow()` to check both the static `WORKFLOW_REGISTRY` and the `workflow_definitions` DB table, with static workflows taking precedence on name collision.
- **FR-006**: System MUST provide REST API endpoints for workflow definition CRUD: `GET/POST /api/v1/workflows/definitions`, `GET/PUT/DELETE /api/v1/workflows/definitions/{id}`.
- **FR-007**: System MUST validate workflow definitions on create and update, rejecting invalid topologies with descriptive error messages.
- **FR-008**: System MUST require HITL approval before executing a newly composed workflow for the first time.
- **FR-009**: System MUST require HITL approval before promoting a dynamically created agent from `draft` to `enabled`.
- **FR-010**: System MUST flag dynamically created agents with `is_dynamic: true` for audit and lifecycle management.
- **FR-011**: System MUST store intent patterns on saved workflows so the Orchestrator can route future matching intents directly to the saved workflow.
- **FR-012**: System MUST support workflow versioning -- updates create new versions, previous versions are preserved for rollback.
- **FR-013**: System MUST enforce a configurable max-step limit on workflow execution to prevent runaway graphs.
- **FR-014**: System MUST trace all dynamic workflow compilations and executions via MLflow, consistent with Constitution Principle III (Observability).

### Key Entities

- **WorkflowDefinition**: A declarative description of a workflow graph. Key attributes: id, name, description, config (nodes, edges, conditional_edges, compile options), state_schema (reference to a known state class), intent_patterns, status, version, created_by, is_dynamic.
- **NodeManifestEntry**: A registry entry for an available node function. Key attributes: name, handler (function reference), description, input_state_fields, output_state_fields, required_dependencies (e.g., ha_client, session), parameter_schema.
- **Agent (extended)**: Adds `is_dynamic: bool` field to the existing Feature 23 Agent entity to distinguish system-defined agents from dynamically created ones.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can describe a novel multi-step task in chat and receive a composed workflow that executes successfully, without writing any code or config.
- **SC-002**: Dynamically created workflows persist across server restarts and are auto-routable by the Orchestrator on matching intent.
- **SC-003**: The `WorkflowCompiler` rejects 100% of invalid topologies (orphan nodes, missing edges, unresolved node references) with descriptive errors at validation time.
- **SC-004**: Dynamic agent creation produces agents that are fully functional within the existing Feature 23 lifecycle (draft -> enabled -> primary, with config/prompt versioning).
- **SC-005**: All dynamic compositions and executions are fully traced in MLflow with the same fidelity as static workflows.
- **SC-006**: Workflow CRUD API responds in under 200ms for create/update operations (excluding compilation).
- **SC-007**: The node manifest is auto-generated from decorated node functions, requiring zero manual maintenance when new nodes are added to the codebase.
