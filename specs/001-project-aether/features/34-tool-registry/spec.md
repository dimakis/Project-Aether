# Feature Specification: Dynamic Tool Registry

**Feature Branch**: `feat/34-tool-registry`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "Tool registry feature -- bunch tools in the database by group so HA tools etc. and dynamically load them into agents."

## User Scenarios & Testing

### User Story 1 - DB-Backed Tool Groups (Priority: P1)

As a system operator, I want tools organized into named groups in the database so that when I assign tools to an agent, I assign groups (e.g. "ha_query", "diagnostics") rather than 30+ individual tool names.

**Why this priority**: This is the core data model and resolution logic. Everything else builds on it.

**Independent Test**: Seed tool groups, assign groups to an agent config version, resolve via `get_tools_for_agent` and verify the correct union of tool objects is returned.

**Acceptance Scenarios**:

1. **Given** a `tool_group` table seeded with groups matching current Python groupings, **When** I query the groups, **Then** each group contains the same tool names as its Python counterpart (`get_ha_tools()`, etc.).
2. **Given** an `AgentConfigVersion` with `tool_groups_enabled: ["ha_entity_query", "approval"]`, **When** `get_tools_for_agent` resolves tools, **Then** it returns exactly the union of those groups' tool names mapped to tool objects.
3. **Given** an `AgentConfigVersion` with both `tool_groups_enabled` and `tools_enabled`, **When** resolved, **Then** the result is the set union (no duplicates).

---

### User Story 2 - Mutation Registry from DB (Priority: P1)

As the system, I want the read-only tool classification derived from tool group metadata so that adding a tool to a read-only group automatically classifies it correctly for HITL enforcement.

**Why this priority**: Safety-critical -- HITL enforcement must remain fail-safe through the migration.

**Independent Test**: Add a tool to a read-only group, verify `is_mutating_tool()` returns false. Add to a non-read-only group, verify it returns true.

**Acceptance Scenarios**:

1. **Given** groups with `is_read_only: true`, **When** `build_read_only_set_from_db()` is called, **Then** it returns all tool names from those groups.
2. **Given** a new tool added to a non-read-only group, **When** `is_mutating_tool()` is called, **Then** it returns `true` (fail-safe preserved).
3. **Given** the DB is unavailable at startup, **When** the mutation registry is queried, **Then** it falls back to the current hardcoded `READ_ONLY_TOOLS` frozenset.

---

### User Story 3 - CRUD API for Tool Groups (Priority: P2)

As an admin, I want API endpoints to list, view, create, and update tool groups so I can manage tool organization without code changes.

**Why this priority**: Operational flexibility but sensible defaults exist from seed data.

**Independent Test**: Call each CRUD endpoint and verify correct responses.

**Acceptance Scenarios**:

1. **Given** I call `GET /api/tool-groups`, **Then** I receive all groups with tool counts.
2. **Given** I call `PUT /api/tool-groups/{name}` with updated `tool_names`, **Then** the group is updated and subsequent agent resolution reflects the change.
3. **Given** I call `PUT /api/tool-groups/{name}` with a tool name not in the Python registry, **Then** the API returns a 422 with details on the unknown tool name.

---

### User Story 4 - Agent Config UI Integration (Priority: P3)

As an admin using the agent configuration page, I want to assign tool groups to agents (alongside individual tool overrides) so I can manage tool assignments at the right level of abstraction.

**Why this priority**: UI is a convenience layer; the API and resolution logic deliver the core value.

**Independent Test**: Edit an agent config version, select tool groups, promote, verify the agent uses exactly those tools.

**Acceptance Scenarios**:

1. **Given** I am editing an agent config version, **When** I see the tools section, **Then** I see checkboxes for tool groups and a separate section for individual tool overrides.
2. **Given** I select the "ha_entity_query" and "approval" groups, **When** I promote the config, **Then** the agent uses exactly those tools.

---

### Edge Cases

- Tool group references a tool name that no longer exists in Python registry: log warning, skip unknown tool.
- Both `tool_groups_enabled` and `tools_enabled` are empty/null: fall back to current hardcoded behavior.
- Two groups contain the same tool: set union, no duplicates.
- A tool is in a read-only group AND a mutating group: treat as mutating (fail-safe).
- DB unavailable during resolution: fall back to hardcoded behavior (backward compat).

## Requirements

### Functional Requirements

- **FR-001**: System MUST store named tool groups in the database with tool name lists and read-only classification.
- **FR-002**: System MUST support a `tool_groups_enabled` JSONB column on `AgentConfigVersion` alongside existing `tools_enabled`.
- **FR-003**: Tool resolution MUST expand groups into individual tool names, merge with `tools_enabled`, and deduplicate.
- **FR-004**: Mutation registry MUST derive read-only classification from DB tool group metadata with hardcoded fallback.
- **FR-005**: System MUST provide CRUD API endpoints for tool group management.
- **FR-006**: System MUST seed default tool groups matching current Python grouping functions on first migration.
- **FR-007**: Resolution MUST fall back to hardcoded behavior when DB is unavailable.

### Key Entities

- **ToolGroup**: Named collection of tool names with read-only classification. UUID PK, unique name, display_name, description, tool_names (JSONB), is_read_only (bool).
- **AgentConfigVersion** (extended): Adds `tool_groups_enabled` JSONB column.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 12 seed groups contain the correct tool names matching current Python functions.
- **SC-002**: Agent tool resolution with groups produces identical results to current hardcoded curator sets.
- **SC-003**: Mutation classification from DB matches current hardcoded `READ_ONLY_TOOLS` for all existing tools.
- **SC-004**: Existing agent tests pass without modification (backward compatibility).
- **SC-005**: Tool group CRUD operations complete in under 100ms.
