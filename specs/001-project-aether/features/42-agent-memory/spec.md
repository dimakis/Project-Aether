# Feature: Agent Memory Layer

**Status**: Draft
**Priority**: P1
**Depends on**: 23-agent-configuration, 32-prompt-registry
**Created**: 2026-03-12

## Goal

Give Aether persistent, cross-session memory so the agent can recall user
preferences, past decisions, device usage patterns, and corrections — and
reason over the relationships between them — without relying solely on the
20-message sliding window within a single conversation.

## Problem Statement

Today the Architect agent is stateless across conversations. Every new chat
session starts from zero — the agent does not know that the user prefers lights
at 60%, rejected a particular automation last week, or has solar panels. Context
is limited to:

1. **Sliding window** — last 20 messages within the current conversation.
2. **Conversation.context** — JSONB blob, not searchable, not shared across
   sessions.
3. **LangGraph checkpoints** — workflow state, not semantic knowledge.

Additionally, the domain has rich relationships that are currently invisible to
the agent: devices belong to areas, automations reference entities, insights
span multiple devices, and proposals link conversations to automations. Many of
these are soft references (JSONB arrays, string IDs) that cannot be traversed
via SQL joins. When a user asks "what automations affect the bedroom?" the agent
has no way to answer without re-discovering everything from scratch.

## User Experience

### Scenario 1 — Preference Recall

1. User says: "I always want the hallway lights at 40% after sunset."
2. Architect stores a `preference` memory linked to the hallway light entities.
3. Two weeks later, user says: "Create an automation for the hallway lights."
4. Architect retrieves the stored preference **and** traverses the graph to find
   which entities are hallway lights, proposing an automation with 40% brightness
   after sunset — without the user repeating anything.
5. User says: "Actually, make it 30% now."
6. Architect updates the existing memory (not a duplicate).

### Scenario 2 — Cross-Domain Reasoning

1. User asks: "What did we decide about the bedroom?"
2. Agent queries the memory graph for all nodes linked to the "Bedroom" area:
   preferences about bedroom lights, a rejected automation proposal for the
   bedroom thermostat, an insight about bedroom humidity.
3. Agent synthesizes a coherent answer spanning devices, automations, and
   past analyses — something impossible with flat memory alone.

### Scenario 3 — Memory Management

1. User visits Settings → Memories and sees a list of what Aether remembers.
2. Each memory shows its type, content, linked entities, source conversation,
   and timestamps.
3. User can view, correct, or delete any memory.

## Core Capabilities

### Explicit Memory Storage via Agent Tool

Memories are created through a dedicated `store_memory` tool available to the
Architect (and other agents). The agent decides when something is worth
remembering — there is no background extraction pipeline.

This keeps memory creation observable, traceable, and deterministic:
- Every memory write is a tool call visible in the MLflow trace.
- The user sees "Aether remembered: hallway lights → 40% after sunset" in the
  chat activity panel.
- No hidden LLM calls deciding what to remember behind the scenes.

### Hybrid Retrieval: Vector Search + Graph Traversal

Memory retrieval combines two strategies:

1. **Semantic search** — embed the user's query and find the most relevant
   memory nodes via pgvector cosine similarity.
2. **Graph expansion** — from the matched nodes, traverse edges to pull in
   related context (the area a device is in, other preferences for that area,
   past decisions about linked automations).

Both run on the same PostgreSQL instance. Semantic search finds the entry
point; graph traversal enriches it with relational context.

### Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `preference` | User preference or habitual request | "Lights at 40% after sunset" |
| `decision` | A choice the user made (approved/rejected) | "Rejected motion-sensor automation for bathroom" |
| `correction` | User corrected the agent's assumption | "House has 3 bedrooms, not 2" |
| `device_pattern` | Observed device usage or configuration | "Solar panels on south roof, 6kW system" |
| `instruction` | Standing instruction for agent behaviour | "Always ask before changing thermostat" |

### Graph Relationships

Memory nodes connect to each other and to domain entities via typed edges:

| Edge Type | From | To | Example |
|-----------|------|----|---------|
| `about_entity` | Memory | HAEntity | Preference → `light.hallway` |
| `about_area` | Memory | Area | Preference → "Hallway" |
| `about_automation` | Memory | HAAutomation | Decision → rejected automation |
| `supersedes` | Memory | Memory | Updated preference → old preference |
| `related_to` | Memory | Memory | "30% lights" related to "energy saving mode" |
| `derived_from` | Memory | Insight | Device pattern → energy analysis insight |
| `from_conversation` | Memory | Conversation | Provenance link |

Edges are lightweight rows in a `memory_edges` table — not a separate graph
database. Traversal uses recursive CTEs, bounded by depth (default 2 hops)
to keep queries fast.

### Deterministic Conflict Resolution

When storing a memory that overlaps with an existing one (same user, same
type, high vector similarity), the agent explicitly updates rather than
duplicates. The update is a tool call, not a background LLM decision:

1. Agent calls `store_memory` with content and entity links.
2. System finds existing memory above similarity threshold.
3. System returns the match to the agent with a prompt to confirm update.
4. Agent calls `update_memory` with the revised content.
5. Old content is preserved in a `previous_content` field for audit.
6. A `supersedes` edge is created from the new version to the old.

### User Memory Management

Users can view and manage their memories through the UI and API:

- **View**: List all memories with type, content, linked entities, source
  conversation, and timestamps.
- **Edit**: Correct a memory's content (triggers re-embedding).
- **Delete**: Remove a memory permanently.
- **Search**: Semantic search across memories ("what does Aether know about
  my lights?").

## Components

### Database Entities

**`MemoryNode`** — core memory table with embeddings

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | PK |
| `user_id` | String(100) | User scope, indexed |
| `agent_id` | UUID | Agent that created this memory, FK to `agent` |
| `memory_type` | Enum | `preference`, `decision`, `correction`, `device_pattern`, `instruction` |
| `content` | Text | Human-readable memory content |
| `embedding` | Vector(dim) | pgvector embedding for semantic search |
| `source_conversation_id` | UUID | FK to `conversation` (nullable) |
| `source_message_id` | UUID | FK to `message` (nullable) |
| `previous_content` | Text | Prior content before last update (audit trail) |
| `metadata` | JSONB | Structured data (extracted entities, confidence, etc.) |
| `is_active` | Boolean | Soft-delete flag, default true |
| `created_at` | Timestamp | Creation time |
| `updated_at` | Timestamp | Last update time |

**`MemoryEdge`** — typed relationships between memory nodes and domain entities

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | PK |
| `edge_type` | String | Relationship type (see table above) |
| `from_node_id` | UUID | FK to `memory_nodes`, indexed |
| `to_node_id` | UUID | FK to `memory_nodes` (nullable, for memory↔memory edges) |
| `to_entity_id` | UUID | Target domain entity ID (nullable, for memory↔domain edges) |
| `to_entity_type` | String | Target entity table name (e.g. `ha_entity`, `area`, `conversation`) |
| `properties` | JSONB | Edge metadata (e.g. relationship strength, context) |
| `created_at` | Timestamp | Creation time |

Constraint: exactly one of `to_node_id` or `to_entity_id` must be non-null
(CHECK constraint). This allows edges to point either to other memory nodes or
to existing domain entities without requiring FKs to every table.

Unique constraint on `(from_node_id, to_node_id, edge_type)` and
`(from_node_id, to_entity_id, to_entity_type, edge_type)` to prevent
duplicate edges.

### Data Access Layer

**`MemoryRepository`** in `src/dal/memory.py`

- `store(user_id, content, memory_type, embedding, edges, ...)` — insert node + edges
- `search(user_id, query_embedding, top_k, threshold)` — pgvector cosine similarity
- `search_with_graph(user_id, query_embedding, top_k, threshold, depth)` — vector
  search + recursive CTE expansion of edges up to `depth` hops
- `find_similar(user_id, embedding, threshold)` — find potential duplicates
- `update(memory_id, content, new_embedding)` — update with audit trail
- `delete(memory_id)` — soft-delete node (edges preserved for audit)
- `hard_delete(memory_id)` — permanent removal of node + edges
- `list_by_user(user_id, memory_type?, limit, offset)` — paginated listing
- `get_related(node_id, edge_types?, depth)` — graph traversal from a node
- `get_by_entity(entity_id, entity_type)` — all memories linked to a domain entity

### Agent Tools

| Tool | Agent | Description |
|------|-------|-------------|
| `store_memory` | Architect, Analysts | Store a memory with optional entity links |
| `update_memory` | Architect, Analysts | Update an existing memory (with audit trail + supersedes edge) |
| `recall_memories` | Architect, Analysts | Hybrid retrieval: vector search + graph expansion |
| `list_memories` | Architect | List user's memories (for chat-based management) |
| `delete_memory` | Architect | Soft-delete a memory |

The `store_memory` tool accepts optional `entity_ids` (HA entity IDs) and
`area_ids` which are automatically resolved to `about_entity` and `about_area`
edges. The agent provides these when the memory is about specific devices or
rooms.

### Embedding Service

**`EmbeddingService`** in `src/services/embedding.py`

- Wraps the configured embedding model (e.g. `text-embedding-3-small`).
- Configurable via `AppSettings` (model name, dimension, batch size).
- Async interface with retry logic.
- Shared across memory storage, retrieval, and re-embedding on edit.

### Backend API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/memories` | GET | List memories for authenticated user |
| `GET /api/v1/memories/{id}` | GET | Get single memory with edges |
| `PUT /api/v1/memories/{id}` | PUT | Update memory content |
| `DELETE /api/v1/memories/{id}` | DELETE | Delete memory |
| `POST /api/v1/memories/search` | POST | Semantic search across memories |
| `GET /api/v1/memories/entity/{entity_id}` | GET | Memories linked to a domain entity |

### UI

- **Settings → Memories** page: list, search, edit, delete memories. Each
  memory shows linked entities as clickable chips.
- **Chat activity panel**: "Aether remembered: ..." when a memory is stored.
- **Memory indicator**: subtle badge when the agent uses recalled memories in
  a response.
- **Entity detail**: "Memories about this entity" section on device/area pages
  (future enhancement).

### Context Injection

The memory retrieval is wired into `_build_messages` on the Architect (and
other agents). Before generating a response:

1. Embed the latest user message.
2. Call `MemoryRepository.search_with_graph()` — vector search for top-k
   memories, then expand 1-2 hops via graph edges to pull in related context.
3. Format retrieved memories as a `SystemMessage` block injected after the
   main system prompt and before conversation history. Includes relationship
   context (e.g. "This preference is about light.hallway in the Hallway area").
4. Track which memories were used in the response metadata for observability.

## Constitution Check

- **Safety First**: Memory storage is an explicit agent tool call — no
  autonomous background extraction. Users can view, edit, and delete all
  memories. No memory influences mutating actions without HITL approval.
- **Isolation**: No new external services. pgvector and graph tables run
  within existing PostgreSQL. Embedding calls go through the same LLM
  provider pipeline.
- **Observability**: Every memory write/read is a traced tool call in MLflow.
  Retrieved memories and graph expansions are logged in response metadata.
- **State**: Memories and edges are durable in PostgreSQL. No in-memory-only
  state. Aligns with "Postgres for durable checkpointing."
- **Security**: Memories are scoped per `user_id` — no cross-user leakage.
  Graph traversal is user-scoped (edges can only reach the user's own memory
  nodes; domain entity edges are read-only references). API endpoints require
  authentication. Memory content is validated via Pydantic.

## Acceptance Criteria

- **Given** the user states a preference in chat, **when** the Architect
  decides to remember it, **then** a `store_memory` tool call appears in the
  trace and the memory is persisted with a valid embedding and entity edges.
- **Given** stored memories exist, **when** the user starts a new conversation
  on a related topic, **then** the agent's response reflects recalled
  memories without the user repeating themselves.
- **Given** a memory already exists for "hallway lights at 40%", **when** the
  user says "make it 30%", **then** the agent updates the existing memory
  (not a duplicate), the `previous_content` field preserves "40%", and a
  `supersedes` edge links the versions.
- **Given** the user asks "what do you know about the bedroom?", **then** the
  agent traverses graph edges to find all memories linked to the Bedroom area
  and its child entities, returning a coherent summary.
- **Given** the user visits Settings → Memories, **then** they see all active
  memories with type, content, linked entities, and timestamps.
- **Given** the user deletes a memory via UI, **then** it no longer appears
  in retrieval results for any future conversation.
- **Given** a conversation with no relevant memories, **then** the agent
  behaves identically to today (no performance regression).
- **Given** the embedding service is unavailable, **then** the agent falls
  back to operating without memory retrieval (graceful degradation, not a
  hard failure).
- **Given** a graph traversal query, **then** it completes within 100ms for
  graphs with up to 10,000 nodes and 2-hop depth.

## Out of Scope

- Automatic background memory extraction (no hidden LLM calls).
- External graph database (Neo4j, Memgraph, etc.).
- Memory sharing across users / multi-tenant memory isolation.
- Memory-based proactive suggestions (e.g. "you usually turn on lights now").
- Embedding model fine-tuning or custom training.
- Memory import/export.
- Apache AGE or SQL/PGQ (may adopt in future if PostgreSQL adds native graph
  query support).
