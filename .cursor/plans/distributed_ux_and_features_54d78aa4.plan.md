---
name: Distributed UX and Features
overview: "Three workstreams: (1) fix distributed streaming handler to use proper A2A streaming proxy, (2) update Architecture UI page for the distributed topology, (3) build UI for dynamic workflow/agent creation (Features 29/30 frontend)."
todos:
  - id: ws1-stream-client
    content: Add async stream() method to A2ARemoteClient using httpx-sse + translate_a2a_event
    status: pending
  - id: ws1-stream-executor
    content: Update AetherAgentExecutor to support SendStreamingMessage (yield events during agent execution)
    status: pending
  - id: ws1-handler-fix
    content: Replace distributed handler hack with proper streaming proxy using client.stream()
    status: pending
  - id: ws1-stream-test
    content: "Integration test: verify token-by-token streaming through distributed chain"
    status: pending
  - id: ws2-arch-config
    content: Update architecture page config.ts with Orchestrator, Knowledge, A2A edges
    status: pending
  - id: ws2-dynamic-topology
    content: Fetch routable agents from /agents/available for dynamic architecture view
    status: pending
  - id: ws2-deployment-mode
    content: Add deployment mode indicator (monolith/distributed) to Architecture page
    status: pending
  - id: ws3-agent-picker
    content: Add agent picker dropdown to ChatHeader (fetches /agents/available, sends agent field)
    status: pending
  - id: ws3-workflow-page
    content: Create Workflow Definitions page (list, create, delete via /workflows/definitions API)
    status: pending
  - id: ws3-agent-registry
    content: Enhance Agents page with domain, routing metadata, Agent Card links
    status: pending
isProject: false
---

# Distributed UX and Feature Frontend

## Workstream 1: Fix Distributed Streaming Handler

### Problem

The distributed handler calls `A2ARemoteClient.invoke()` which returns a single dict result. The response is either discarded (original bug) or returned as a single SSE chunk (current hack). No token-by-token streaming, no tool events, no thinking indicators.

### Proper Fix

Use `SendStreamingMessage` via the A2A SDK client, consume the A2A SSE stream, and translate events using `src/agents/a2a_streaming.py` (already built in Phase 4).

### Tasks

**1.1: Add streaming to A2ARemoteClient**

Extend [src/agents/a2a_client.py](src/agents/a2a_client.py) with an `async stream()` method that uses `httpx-sse` to consume A2A SSE events:

```python
async def stream(self, state) -> AsyncGenerator[StreamEvent, None]:
    data = pack_state_to_data(state)
    # POST to / with streaming=True, consume SSE response
    # Translate each A2A event via translate_a2a_event()
    # Yield StreamEvent dicts
```

**1.2: Update AetherAgentExecutor for streaming**

The executor currently only supports `SendMessage` (request/response). Add support for `SendStreamingMessage` — yield events to the A2A event queue as they happen (token by token from the LLM, tool events, etc.).

This means the Architect service needs to stream its `ArchitectWorkflow.stream_conversation()` output into A2A events in real-time.

**1.3: Replace hack in handler**

Replace the current single-chunk distributed path in [handlers.py](src/api/routes/openai_compat/handlers.py) with:

```python
if _should_use_distributed():
    client = _create_distributed_client()
    async for event in client.stream(state):
        # translate_a2a_event already handles the mapping
        # yield as OpenAI SSE format (same as monolith path)
```

**1.4: Test with real streaming**

Integration test that verifies token-by-token streaming works through the distributed chain.

---

## Workstream 2: Architecture UI Update

### Problem

The Architecture page shows a static hardcoded topology from `ui/src/pages/architecture/config.ts`. It doesn't show the Orchestrator agent, the A2A communication pattern, or the distributed container topology.

### Tasks

**2.1: Update agent node config**

Update [ui/src/pages/architecture/config.ts](ui/src/pages/architecture/config.ts):

- Add Orchestrator agent node
- Add Knowledge agent node
- Update edges to show A2A communication pattern
- Add "distributed mode" visual (container boundaries)

**2.2: Dynamic topology from Agent Cards**

Add an API call to `GET /api/v1/agents/available` to fetch routable agents dynamically. Show their domain, capabilities, and routing status. Fall back to static config if API is unavailable.

**2.3: Show deployment mode indicator**

Add a badge or toggle showing whether the system is running in monolith or distributed mode. Could query a new endpoint or use the existing health endpoint response.

---

## Workstream 3: Dynamic Workflow/Agent Creation UI

### Problem

Features 29 (Workflow Definitions) and 30 (Agent Routing) have backend APIs but no frontend UI. Users can't create new workflows or agents through the chat or settings pages.

### What exists (backend)

- `POST /api/v1/workflows/definitions` — create workflow
- `GET /api/v1/workflows/definitions` — list workflows
- `GET /api/v1/agents/available` — list routable agents
- Agent Card at `/.well-known/agent-card.json`
- `ChatCompletionRequest.agent` field — select specific agent

### Tasks

**3.1: Agent Picker in Chat Header**

Add an agent picker dropdown to [ui/src/pages/chat/ChatHeader.tsx](ui/src/pages/chat/ChatHeader.tsx):

- Fetches from `GET /api/v1/agents/available`
- Options: "Auto (Jarvis)" + each routable agent
- Persists selection in localStorage
- Sends selected agent in the `agent` field of chat requests

This is FR-005 from the Feature 30 spec.

**3.2: Workflow Definitions Page**

Create a new page at `/workflows` (or under `/agents`):

- Lists existing workflow definitions from `GET /api/v1/workflows/definitions`
- Shows name, status (draft/active/archived), state type, node count
- "Create Workflow" button opens a form
- Form fields: name, description, state type, nodes (JSON editor), edges
- Validates via the backend's compilation check before saving
- Delete (soft-delete) button

**3.3: Agent Registry Enhancement**

Enhance the existing Agents page to show:

- Domain and routing metadata for each agent
- "Routable" badge for agents the Orchestrator can route to
- Intent patterns and capabilities
- Link to the agent's Agent Card JSON

---

## Recommended Execution Order

1. **Workstream 1** first (streaming fix) — makes the distributed setup actually usable
2. **Workstream 3.1** (agent picker) — quick win, high visibility
3. **Workstream 2** (architecture page) — visual update
4. **Workstream 3.2** (workflow definitions page) — new feature
5. **Workstream 3.3** (agent registry enhancement) — polish

Each workstream is independent and can be a separate PR.