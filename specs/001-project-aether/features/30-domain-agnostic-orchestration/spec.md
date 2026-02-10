# Feature Specification: Domain-Agnostic Orchestration

**Feature Branch**: `030-domain-agnostic-orchestration`
**Created**: 2026-02-09
**Status**: Draft
**Input**: User description: "Evolve Project Aether from an HA-focused automation assistant into a general-purpose 'Jarvis' home AI with intent routing, domain agents, voice support, and personality."
**Depends on**: Feature 23 (Agent Configuration)
**Extended by**: Feature 29 (Dynamic Workflow Composition)
**Architecture Decisions**: `.cursor/plans/jarvis_pivot_architecture_aed12d48.plan.md` (Go/Rust rewrite, message bus, agent registry decisions)

## User Scenarios & Testing

### User Story 1 - Intent-Based Routing via Orchestrator (Priority: P1)

As a user, I want my messages automatically routed to the right specialist agent based on intent, so I don't need to know which agent handles what -- I just ask and the system figures it out.

**Why this priority**: This is the foundational capability that transforms Aether from a single-agent HA tool into a multi-domain AI assistant. Everything else builds on this.

**Independent Test**: User sends "turn off the kitchen lights" and it routes to the Home Agent. User sends "what's the capital of France?" and it routes to the Knowledge Agent. User sends "find me a pasta recipe" and it routes to the Food Agent. All without explicit agent selection.

**Acceptance Scenarios**:

1. **Given** the Orchestrator is the default agent, **When** a user sends a home automation request (e.g., "turn off the kitchen lights"), **Then** the Orchestrator classifies the intent as "home" and delegates to the Home Agent (existing Architect), which processes it normally.
2. **Given** the Orchestrator receives an ambiguous request, **When** intent classification confidence is below threshold, **Then** the Orchestrator asks the user for clarification rather than guessing.
3. **Given** the user sends a general knowledge question, **When** the Orchestrator classifies the intent, **Then** it routes to the Knowledge Agent and returns the response in the same conversation thread.
4. **Given** no domain agents match the intent, **When** the Orchestrator cannot classify, **Then** it falls back to the Knowledge Agent as a default handler.

---

### User Story 2 - Manual Agent Selection in Chat UI (Priority: P1)

As a power user, I want to select a specific agent from the chat interface, so I can bypass the Orchestrator and talk directly to the agent I want.

**Why this priority**: Paired with Story 1, this ensures both automatic and manual routing work. Power users and developers need direct access; it also provides a fallback if routing misclassifies.

**Independent Test**: User selects "Home Agent" from the agent picker dropdown, sends a message, and it goes directly to the Architect without Orchestrator routing. User switches to "Auto" and the Orchestrator resumes routing.

**Acceptance Scenarios**:

1. **Given** the chat UI is loaded, **When** I see the chat header, **Then** there is an AgentPicker dropdown alongside the existing ModelPicker, defaulting to "Auto (Jarvis)".
2. **Given** I select "Home Agent" from the picker, **When** I send a message, **Then** it goes directly to the Architect agent, bypassing the Orchestrator.
3. **Given** I select "Auto (Jarvis)", **When** I send a message, **Then** it goes through the Orchestrator for intent classification and routing.
4. **Given** I have selected an agent, **When** I close and reopen the browser, **Then** my agent selection is persisted (localStorage).
5. **Given** the model and agent pickers are both visible, **When** I select a model and an agent independently, **Then** the selected model powers whichever agent is active.

---

### User Story 3 - Backward-Compatible HA Experience (Priority: P1)

As an existing Aether user, I want all my current HA functionality to work exactly as before, so the Jarvis pivot doesn't break anything I depend on.

**Why this priority**: Non-negotiable. The pivot must be additive, not disruptive. Existing users selecting "Home Agent" (or the Orchestrator correctly routing HA intents) must get the identical experience.

**Independent Test**: Run the existing test suite with the Orchestrator enabled. All HA-related tests pass. All existing API endpoints return the same responses. The OpenAI-compatible endpoint still works for HA voice pipelines.

**Acceptance Scenarios**:

1. **Given** the Orchestrator is enabled, **When** a user sends an HA automation request, **Then** the response is identical to what the Architect would produce without the Orchestrator.
2. **Given** the `/api/v1/chat/completions` endpoint receives a request without an `agent` field, **Then** it defaults to `"auto"` (Orchestrator routing), and HA intents still work.
3. **Given** the existing HA Voice Pipeline is configured, **When** it sends requests to the OpenAI-compatible endpoint, **Then** it works without modification (the Orchestrator routes HA intents to the Home Agent).

---

### User Story 4 - Knowledge Agent (Priority: P2)

As a user, I want to ask general questions and get informative answers, so Aether is useful beyond just home automation.

**Why this priority**: Simplest possible domain agent (no tools, pure LLM). Validates the routing pattern works end-to-end and provides immediate value.

**Independent Test**: User asks "explain quantum computing in simple terms" and receives a clear, informative response without any HA tool invocations.

**Acceptance Scenarios**:

1. **Given** the Knowledge Agent is registered and enabled, **When** the Orchestrator receives a general question, **Then** it routes to the Knowledge Agent.
2. **Given** the Knowledge Agent receives a question, **When** it processes the request, **Then** it returns a response using only the LLM (no tools), traced via MLflow.
3. **Given** the Knowledge Agent is disabled via Feature 23 agent config, **When** the Orchestrator would route to it, **Then** it falls back to the next best match or asks for clarification.

---

### User Story 5 - Web Research Agent (Priority: P2)

As a user, I want to ask questions that require current information (weather, news, flights, products), so Aether can help me with real-time queries.

**Why this priority**: Demonstrates tool-using domain agents beyond HA. Validates that the routing pattern works with agents that have external tool dependencies.

**Independent Test**: User asks "what's the weather in Sydney?" and receives current weather information sourced from a web search.

**Acceptance Scenarios**:

1. **Given** the Research Agent is registered with web search tools, **When** the Orchestrator receives a search-oriented query, **Then** it routes to the Research Agent.
2. **Given** the Research Agent receives a query, **When** it processes the request, **Then** it uses Tavily or equivalent web search tools to find current information and returns a summarized response.
3. **Given** the Research Agent encounters a rate limit or API failure, **When** the search tool fails, **Then** it gracefully falls back to the LLM's training knowledge with a disclaimer.

---

### User Story 6 - Food/Cooking Agent with Cross-Domain Delegation (Priority: P2)

As a user, I want to ask for cooking help and have the system coordinate with my smart kitchen appliances, so I get a seamless "Jarvis" experience.

**Why this priority**: The canonical Jarvis interaction -- demonstrates cross-domain delegation where one agent coordinates with another. This is the first multi-agent collaboration beyond the existing HA specialist team.

**Independent Test**: User says "I want to make lasagna." The Food Agent provides the recipe and asks if the user wants to preheat the oven. On confirmation, it delegates to the Home Agent to preheat via HA.

**Acceptance Scenarios**:

1. **Given** the Food Agent is registered with recipe knowledge and HA delegation capability, **When** the user asks for cooking help, **Then** the Orchestrator routes to the Food Agent.
2. **Given** the Food Agent determines an HA action is needed (e.g., preheat oven), **When** it needs to control a device, **Then** it delegates to the Home Agent via tool call, not by directly using HA tools.
3. **Given** the user confirms an HA action from the Food Agent, **When** the action involves a mutation, **Then** HITL approval is required (consistent with Constitution Principle I: Safety).

---

### User Story 7 - HA Voice Pipeline Integration (Priority: P3)

As a user, I want to interact with Aether via voice using smart speakers in my home, triggered by a "Jarvis" wake word.

**Why this priority**: Voice is a major UX leap but depends on Phase 1 (routing) and Phase 2 (domain agents) being stable. The HA voice pipeline requires no code changes on Aether's side -- it's a configuration/documentation effort.

**Independent Test**: Say "Jarvis, turn off the living room lights" to a Wyoming satellite. The wake word triggers, Whisper transcribes, HA sends the text to Aether's OpenAI-compatible endpoint, Aether processes and responds, Piper speaks the response.

**Acceptance Scenarios**:

1. **Given** a Wyoming satellite is configured with openWakeWord ("Jarvis"), **When** the user says the wake word followed by a command, **Then** the audio is captured and sent to the HA Assist pipeline.
2. **Given** the Assist pipeline uses Aether's `/api/v1/chat/completions` endpoint, **When** it sends the transcribed text, **Then** the Orchestrator processes it and returns a text response.
3. **Given** the response is returned to HA, **When** Piper TTS synthesizes the audio, **Then** the response is played back on the satellite speaker.

---

### User Story 8 - Jarvis Personality and Channel-Aware Responses (Priority: P3)

As a user, I want Aether to feel like a cohesive AI assistant with a consistent personality that adapts its communication style to the channel (voice vs text).

**Why this priority**: Polish and UX refinement that makes the system feel like "Jarvis" rather than a collection of disconnected agents. Depends on all prior stories being functional.

**Independent Test**: Same question asked via text and voice produces different response lengths and formatting -- voice gets a concise spoken response, text gets a detailed formatted response.

**Acceptance Scenarios**:

1. **Given** the Orchestrator has a "Jarvis" personality system prompt, **When** it handles any request, **Then** the personality is consistent across domain switches.
2. **Given** a request comes via voice channel, **When** the response is generated, **Then** it is short, conversational, and avoids markdown formatting.
3. **Given** a request comes via text channel, **When** the response is generated, **Then** it can use full markdown formatting, code blocks, and detailed explanations.
4. **Given** a multi-turn conversation crosses domains (e.g., from cooking to lights), **When** the domain switches, **Then** the conversation remains coherent and the personality stays consistent.

---

### Edge Cases

- What happens when the Orchestrator is down or misconfigured? Direct agent selection must still work. The `agent` field in the API provides the bypass.
- What happens when a domain agent is disabled mid-conversation? The Orchestrator should detect the unavailable agent and re-route or inform the user.
- What happens when two agents could handle the same intent (e.g., "set a timer" -- Home Agent or Food Agent)? Confidence scoring with user disambiguation if scores are close.
- What happens when the voice channel receives a request that requires visual output (e.g., a dashboard)? The agent should detect the channel and suggest the user check the text UI for visual content.
- What happens when agent selection is set to a specific agent but the user's message is clearly for a different domain? The selected agent handles it (respects explicit selection) but may suggest switching.

## Requirements

### Functional Requirements

- **FR-001**: System MUST implement an OrchestratorAgent that classifies user intent and routes to the appropriate domain agent.
- **FR-002**: The `/api/v1/chat/completions` endpoint MUST accept an `agent` field: `"auto"` (default, Orchestrator routes) or a specific agent name (bypasses Orchestrator).
- **FR-003**: System MUST extend the Feature 23 Agent DB entity with: `domain` (str), `intent_patterns` (list[str]), `is_routable` (bool), `capabilities` (list[str]).
- **FR-004**: System MUST provide `GET /api/v1/agents/available` returning all routable agents with their descriptions and capabilities.
- **FR-005**: The chat UI MUST include an AgentPicker component alongside ModelPicker, persisted in localStorage.
- **FR-006**: `ConversationState` MUST be extended with `channel` (voice/text/api) and `active_agent` fields.
- **FR-007**: HITL approval gates MUST work for any mutation-capable agent, not just the Architect.
- **FR-008**: The Orchestrator MUST support multi-turn conversations that span domain switches without losing context.
- **FR-009**: System MUST implement a KnowledgeAgent (no tools, pure LLM) as the simplest routable domain agent.
- **FR-010**: System MUST implement a ResearchAgent with web search tools (Tavily or equivalent).
- **FR-011**: System MUST implement a FoodAgent with cross-domain delegation to the Home Agent for HA actions.
- **FR-012**: Cross-domain delegation MUST go through the Orchestrator or explicit tool calls, not by sharing tools directly between agents.
- **FR-013**: System MUST document HA Voice Pipeline setup (Wyoming satellites, Whisper STT, Piper TTS, openWakeWord) for the "Jarvis" wake word.
- **FR-014**: The Orchestrator system prompt MUST define a consistent "Jarvis" personality.
- **FR-015**: Responses MUST be channel-aware: concise for voice, detailed for text.
- **FR-016**: All agent routing, intent classification, and domain switches MUST be traced via MLflow (Constitution Principle III: Observability).
- **FR-017**: Existing HA functionality MUST work identically when the Home Agent is selected or when the Orchestrator routes HA intents.

### Key Entities

- **Agent (extended)**: Adds `domain`, `intent_patterns`, `is_routable`, `capabilities` fields to the existing Feature 23 Agent entity.
- **OrchestratorAgent**: New agent class with intent classification, confidence scoring, and routing logic. Uses the agent registry to discover available domain agents.
- **ConversationState (extended)**: Adds `channel` (voice/text/api), `active_agent`, and `domain_history` for tracking cross-domain conversations.
- **AgentRole (extended)**: New enum values for Orchestrator, Knowledge, Research, Food roles.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The Orchestrator correctly routes HA-related intents to the Home Agent with >= 95% accuracy (measured against a test set of 100 labeled intents).
- **SC-002**: All existing HA test suites pass without modification after enabling the Orchestrator.
- **SC-003**: Agent selection via the UI picker takes effect within the same message (no page reload required).
- **SC-004**: Cross-domain conversations maintain context across at least 3 domain switches in a single thread.
- **SC-005**: The Knowledge Agent responds to general questions in under 3 seconds (excluding LLM latency).
- **SC-006**: The Research Agent returns web search results with source citations in under 10 seconds.
- **SC-007**: The Food Agent successfully delegates an HA action (preheat oven) to the Home Agent in a single conversation turn.
- **SC-008**: Voice pipeline round-trip (wake word to spoken response) completes in under 8 seconds on a local network.
- **SC-009**: All agent routing decisions are traced in MLflow with intent classification scores visible.
