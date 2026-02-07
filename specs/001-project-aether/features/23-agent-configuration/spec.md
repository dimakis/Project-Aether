**Completed**: 2026-02-07

# Feature Specification: Agent Configuration Page

**Feature Branch**: `023-agent-configuration`  
**Created**: 2026-02-07  
**Status**: Complete  
**Input**: User description: "Agent configuration page where we can configure and lifecycle our agents -- separate LLMs for each, promotion, etc."

## User Scenarios & Testing

### User Story 1 - View & Configure Agent LLM Settings (Priority: P1)

As an admin, I want to view all agents in the system and configure each one with its own LLM model, temperature, and fallback model, so I can optimise cost and quality per agent role.

**Why this priority**: This is the core value of the feature -- moving per-agent configuration out of environment variables and into a UI where it can be changed without restarting the server.

**Independent Test**: Can be fully tested by navigating to `/agents`, selecting an agent, editing its model/temperature, saving as draft, and verifying the draft appears in version history. After promoting, the agent should use the new model on its next invocation.

**Acceptance Scenarios**:

1. **Given** the system has seeded agents, **When** I navigate to `/agents`, **Then** I see cards for Architect, Data Scientist, Librarian, Developer, and Orchestrator with their current status and active model.
2. **Given** I am viewing the Architect agent detail, **When** I click "New Config Version" and set model to `anthropic/claude-sonnet-4` with temperature `0.5`, **Then** a draft config version is created and shown in the version history.
3. **Given** a draft config version exists, **When** I click "Promote", **Then** the draft becomes active, the previous active version is archived, and subsequent Architect invocations use the new model.

---

### User Story 2 - Version & Promote Prompt Templates (Priority: P1)

As an admin, I want to edit agent system prompts in a UI editor, version them independently from model config, and promote/rollback prompt versions so I can iterate on agent behaviour safely.

**Why this priority**: Prompt engineering is the primary tuning lever for agent behaviour. Versioning with rollback lets admins experiment without risk.

**Independent Test**: Can be fully tested by creating a new prompt version for the Data Scientist, promoting it, verifying the agent uses the new prompt, then rolling back and verifying it reverts.

**Acceptance Scenarios**:

1. **Given** the Data Scientist has an active prompt (v1), **When** I create a new prompt version with modified text, **Then** a draft prompt version (v2) is created.
2. **Given** a draft prompt exists, **When** I promote it, **Then** the previous prompt is archived and the new one becomes active.
3. **Given** the active prompt is v2, **When** I click "Rollback", **Then** v1 is restored as a new draft (v3 with v1's content) ready for promotion, preserving full history.

---

### User Story 3 - Agent Status Lifecycle (Priority: P2)

As an admin, I want to enable, disable, or promote agents through status transitions so I can control which agents are active in the system.

**Why this priority**: Operational control is important but secondary to configuration -- most users will want all agents enabled by default.

**Independent Test**: Can be tested by disabling the Data Scientist agent and verifying that delegation to it is skipped, then re-enabling and verifying it works again.

**Acceptance Scenarios**:

1. **Given** the Data Scientist is `enabled`, **When** I click "Disable", **Then** its status changes to `disabled` and the Architect no longer delegates analysis tasks to it.
2. **Given** an agent is `disabled`, **When** I click "Enable", **Then** it becomes `enabled` and is available for delegation again.
3. **Given** an agent is `enabled`, **When** I click "Promote to Primary", **Then** it becomes `primary` for its role.

---

### User Story 4 - Tool Assignment per Agent (Priority: P2)

As an admin, I want to control which tools each agent has access to, so I can restrict agent capabilities for safety or experimentation.

**Why this priority**: Enhances security and experimentation but has a sensible default (all tools enabled).

**Independent Test**: Can be tested by removing the `control_entity` tool from the Architect's config and verifying it can no longer control entities.

**Acceptance Scenarios**:

1. **Given** I am viewing the Architect's config, **When** I see the tools section, **Then** I see checkboxes for all available tools with their current assignment.
2. **Given** I uncheck `control_entity` and promote the config, **Then** the Architect no longer has the `control_entity` tool available.

---

### User Story 5 - Version History & Audit Trail (Priority: P3)

As an admin, I want to see a combined timeline of config and prompt changes for each agent, so I can understand what was active at any point in time and audit changes.

**Why this priority**: Valuable for debugging and compliance but not needed for day-to-day operation.

**Independent Test**: Can be tested by making several config and prompt changes, then viewing the history tab and verifying all changes appear with correct timestamps and linked versions.

**Acceptance Scenarios**:

1. **Given** I have made multiple config and prompt changes to the Architect, **When** I view the History tab, **Then** I see a timeline showing which config version and prompt version were active at each point.
2. **Given** I am viewing history, **When** I click on an archived version, **Then** I can see its full details (model, temperature, tools, or prompt text).

---

### Edge Cases

- What happens when the last enabled agent is disabled? System should warn but allow it.
- What happens if a promoted config references a model that becomes unavailable? Agent falls back to env var defaults, then global default.
- What happens when two admins edit the same agent's draft simultaneously? Last-write-wins with updated_at conflict detection.
- What happens on rollback when there is no previous version? Rollback button is disabled / returns 409.
- What happens when an agent has no active config version? Falls back to env var settings (backward compatible).

## Requirements

### Functional Requirements

- **FR-001**: System MUST store per-agent LLM configuration (model name, temperature, fallback model) in the database with version history.
- **FR-002**: System MUST store per-agent prompt templates in the database with independent version history.
- **FR-003**: Each version (config or prompt) MUST have a status of `draft`, `active`, or `archived`.
- **FR-004**: System MUST enforce single-draft policy: only one draft per agent per version type at a time.
- **FR-005**: System MUST enforce single-active policy: only one active version per agent per type at a time.
- **FR-006**: Promoting a draft MUST atomically set it to `active` and archive the previous active version.
- **FR-007**: Rollback MUST create a new draft with the content of the most recent archived version (preserving history).
- **FR-008**: Agent status MUST support transitions: disabled <-> enabled <-> primary.
- **FR-009**: Disabled agents MUST be skipped during delegation in graph workflows.
- **FR-010**: Runtime model resolution MUST check DB config before env var defaults: user UI selection > DB active config > env var > global default.
- **FR-011**: System MUST provide a seed mechanism to populate default agents with initial config/prompt versions from env vars and file-based prompts.
- **FR-012**: Per-agent tool assignment MUST be stored in the config version as a list of tool names.
- **FR-013**: System MUST provide REST API endpoints for all agent configuration CRUD operations.
- **FR-014**: System MUST provide a UI page at `/agents` for viewing and managing agent configurations.

### Key Entities

- **AgentConfigVersion**: Snapshot of an agent's model settings and tool assignments. Versioned with auto-incrementing version number per agent.
- **AgentPromptVersion**: Snapshot of an agent's system prompt template. Versioned independently from config.
- **Agent** (extended): Adds `status` (disabled/enabled/primary), `active_config_version_id`, and `active_prompt_version_id` fields.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 5 agents (Architect, Data Scientist, Librarian, Developer, Orchestrator) are configurable via the UI without server restart.
- **SC-002**: Config and prompt versions maintain full history with promote/rollback capability.
- **SC-003**: Agent status changes (enable/disable) take effect on the next delegation attempt (no restart required).
- **SC-004**: Env var configuration continues to work as fallback for deployments without UI-based config.
- **SC-005**: Version promotion completes atomically in under 500ms.
