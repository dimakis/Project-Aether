# Feature Specification: Project Aether

**Feature Branch**: `001-project-aether`  
**Created**: 2026-02-02  
**Status**: In Progress  
**Input**: User description: "Build an agentic home automation system called Project Aether. Architecture: A LangGraph multi-agent system with a Librarian (HA discovery), an R&D Loop (Categorizer, Architect, Developer), and a Data Scientist. Capabilities: Abstract HA entities into a dynamic DAL. Self-heal by detecting entity changes. Suggest energy optimizations and custom dashboards. Allow me to chat with the Architect to influence design. Tech: Podman, gVisor, MLflow, HA MCP, Responses API."

**Related Documentation**:
- [Architecture Overview](../../docs/architecture.md) - System design, deployment modes, data flows
- [Quickstart Guide](quickstart.md) - Getting started
- [Implementation Tasks](tasks.md) - Detailed task breakdown

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover and Abstract Home Assistant Entities (Priority: P1)

As a homeowner, I want the system to automatically discover all entities in my Home Assistant instance and create an abstraction layer so that I can interact with my smart home through a unified interface without worrying about entity IDs or implementation details.

**Why this priority**: This is the foundational capability—without entity discovery and abstraction, no other agent can understand or interact with the home. The Librarian agent and dynamic DAL form the core infrastructure.

**Independent Test**: Can be fully tested by connecting to a Home Assistant instance and verifying that all entities are discovered, categorized, and accessible through the DAL. Delivers immediate value by providing a queryable inventory of smart home capabilities.

**Acceptance Scenarios**:

1. **Given** a running Home Assistant instance with configured entities, **When** the Librarian agent performs discovery, **Then** all entities are catalogued with their types, capabilities, and current states.
2. **Given** discovered entities, **When** accessing through the DAL, **Then** entity interactions are abstracted (e.g., "turn on living room lights" without knowing entity_id).
3. **Given** the DAL is operational, **When** an entity is added/removed/renamed in Home Assistant, **Then** the system detects the change and updates the DAL within 5 minutes.

---

### User Story 2 - Conversational Design with Architect Agent (Priority: P2)

As a homeowner, I want to have a conversation with the Architect agent to describe my preferences, constraints, and goals so that the system designs automations tailored to my lifestyle rather than generic rules.

**Why this priority**: Enables personalization and user agency. Once entities are discovered (P1), users need a way to influence how the system uses them. HITL approval is critical here per constitution.

**Independent Test**: Can be fully tested by initiating a chat session with the Architect, describing a scenario (e.g., "I work from home on Tuesdays"), and receiving a proposed automation design that requires user approval before activation.

**Acceptance Scenarios**:

1. **Given** the DAL is populated with entities, **When** I describe a lifestyle preference to the Architect, **Then** I receive a proposed automation design within 60 seconds.
2. **Given** a proposed automation, **When** I provide feedback or modifications, **Then** the Architect refines the design based on my input.
3. **Given** a finalized automation design, **When** I approve it, **Then** the automation is deployed to Home Assistant with a rollback option.
4. **Given** any automation proposal, **When** presented for execution, **Then** I must explicitly approve before it takes effect (HITL requirement).

---

### User Story 3 - Energy Optimization Suggestions (Priority: P3)

As a homeowner, I want the Data Scientist agent to analyze my energy consumption patterns and suggest optimizations so that I can reduce electricity costs without sacrificing comfort. I also want the Data Scientist to suggest useful graphs and visualisations so that I can see data about my home clearly.

**Why this priority**: Delivers tangible financial value. Requires historical data collection (enabled after P1) and benefits from Architect integration (P2) for implementing suggestions.

**Independent Test**: Can be fully tested by providing 7 days of energy data, running analysis, and receiving at least one actionable optimization suggestion with projected savings.

**Acceptance Scenarios**:

1. **Given** at least 7 days of energy consumption data, **When** the Data Scientist analyzes patterns, **Then** I receive optimization suggestions ranked by potential savings.
2. **Given** an energy optimization suggestion, **When** I review it, **Then** I see projected monthly savings, comfort impact, and implementation steps.
3. **Given** I approve an optimization, **When** the Architect implements it, **Then** actual savings are tracked and reported against projections.

---

### User Story 4 - Custom Dashboard Generation (Priority: P4)

As a homeowner, I want the system to generate custom dashboards based on my usage patterns and stated preferences so that I have quick access to the controls and information most relevant to me.

**Why this priority**: Quality-of-life enhancement that benefits from understanding user patterns (P3) and preferences captured during Architect conversations (P2).

**Independent Test**: Can be fully tested by requesting a dashboard for a specific purpose (e.g., "morning routine dashboard") and receiving a functional dashboard configuration.

**Acceptance Scenarios**:

1. **Given** entity data and usage history, **When** I request a themed dashboard, **Then** the system generates a dashboard layout within 30 seconds.
2. **Given** a generated dashboard, **When** I provide feedback, **Then** the system refines the dashboard accordingly.
3. **Given** an approved dashboard, **When** deployed, **Then** it appears in Home Assistant and remains synchronized with entity changes.

---

### Edge Cases

- What happens when Home Assistant is temporarily unreachable during discovery or sync?
- How does the system handle entities with ambiguous or missing friendly names?
- What happens when an automation suggestion conflicts with existing automations?
- How does the system behave when energy data is incomplete or sensors are unavailable?
- What happens if a user rejects all automation suggestions repeatedly?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST discover all Home Assistant entities within 2 minutes of initial connection.
- **FR-002**: System MUST abstract entities into a unified DAL that supports natural language queries.
- **FR-003**: System MUST detect and reconcile entity changes (additions, removals, renames) within 5 minutes.
- **FR-004**: System MUST provide a conversational interface with the Architect agent for design discussions.
- **FR-005**: System MUST require explicit user approval (HITL) before executing any automation that modifies home state.
- **FR-006**: System MUST trace all agent negotiations and data science insights via MLflow, with session correlation for multi-turn conversations and hierarchical spans for tool calls.
- **FR-007**: System MUST run all generated analysis scripts in an isolated sandbox environment.
- **FR-008**: System MUST persist state checkpoints for recovery from failures.
- **FR-009**: System MUST provide energy consumption analysis with actionable optimization suggestions.
- **FR-010**: System MUST generate custom dashboards based on user preferences and usage patterns.
- **FR-011**: System MUST maintain conversation history with the Architect for context continuity.
- **FR-012**: System MUST provide rollback capability for deployed automations.

### Key Entities

- **Entity**: A single smart home device or sensor (lights, switches, sensors, climate controls) with properties (state, attributes, capabilities) and relationships to rooms/zones.
- **Agent**: An autonomous component with a specific role (Librarian, Categorizer, Architect, Developer, Data Scientist) that can negotiate with other agents and produce traceable outputs.
- **Automation**: A rule or workflow that triggers actions based on conditions, requiring user approval before activation.
- **Insight**: A data-driven observation or recommendation produced by the Data Scientist, including supporting evidence and confidence level.
- **Dashboard**: A visual configuration defining layout, widgets, and entity bindings for Home Assistant UI.
- **Conversation**: A dialogue session between user and Architect, maintaining context for design refinement.

## Assumptions

- User has an existing Home Assistant instance with the MCP (Model Context Protocol) integration enabled.
- Home Assistant instance is accessible on the local network or via a secure tunnel.
- User is willing to provide 1-2 weeks of historical data for meaningful energy analysis.
- Standard OAuth2 or long-lived access tokens are acceptable for HA authentication.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can query their smart home in natural language and receive accurate responses 90% of the time.
- **SC-002**: Entity discovery completes within 2 minutes for installations with up to 500 entities.
- **SC-003**: Entity changes are detected and reconciled within 5 minutes of occurrence.
- **SC-004**: Users receive automation proposals within 60 seconds of describing their requirements.
- **SC-005**: 100% of automations require explicit user approval before activation (HITL compliance).
- **SC-006**: Energy optimization suggestions demonstrate measurable savings within 30 days of implementation.
- **SC-007**: Users can recover from any system failure within 5 minutes using checkpoint restoration.
- **SC-008**: All agent negotiations are fully traceable with complete audit logs.
- **SC-009**: Custom dashboards are generated within 30 seconds and deploy successfully to Home Assistant.
- **SC-010**: 80% of users report satisfaction with Architect conversation quality in providing useful designs.
