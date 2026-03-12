# Feature: Agent Memory Layer

**Status**: Draft
**Priority**: P1
**Depends on**: 23-agent-configuration, 32-prompt-registry
**Created**: 2026-03-12

## Goal

Give Aether persistent, cross-session memory so the agent can recall user
preferences, past decisions, device usage patterns, and corrections without
relying solely on the 20-message sliding window within a single conversation.

## Problem Statement

Today the Architect agent is stateless across conversations. Every new chat
session starts from zero — the agent does not know that the user prefers lights
at 60%, rejected a particular automation last week, or has solar panels. Context
is limited to:

1. **Sliding window** — last 20 messages within the current conversation.
2. **Conversation.context** — JSONB blob, not searchable, not shared across
   sessions.
3. **LangGraph checkpoints** — workflow state, not semantic knowledge.

This means users must repeat themselves, the agent cannot learn from past
interactions, and personalization is impossible.

## User Experience

1. User says: "I always want the hallway lights at 40% after sunset."
2. Architect stores a `preference` memory: `hallway lights → 40% after sunset`.
3. Two weeks later, user says: "Create an automation for the hallway lights."
4. Architect retrieves the stored preference and proposes an automation with
   40% brightness after sunset — without the user having to repeat it.
5. User says: "Actually, make it 30% now."
6. Architect updates the existing memory (not a duplicate).
7. User visits Settings → Memories and sees a list of what Aether remembers,
   with the ability to view, correct, or delete any memory.

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

### Semantic Retrieval via pgvector

Before generating a response, the agent retrieves relevant memories using
vector similarity search against the current query. Retrieved memories are
injected into the system prompt alongside the conversation history.

- Uses pgvector on the existing PostgreSQL instance (no new infrastructure).
- Embedding model is configurable via agent settings.
- Retrieval is bounded: top-k results with a similarity threshold to avoid
  injecting irrelevant context.

### Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `preference` | User preference or habitual request | "Lights at 40% after sunset" |
| `decision` | A choice the user made (approved/rejected) | "Rejected motion-sensor automation for bathroom" |
| `correction` | User corrected the agent's assumption | "House has 3 bedrooms, not 2" |
| `device_pattern` | Observed device usage or configuration | "Solar panels on south roof, 6kW system" |
| `instruction` | Standing instruction for agent behaviour | "Always ask before changing thermostat" |

### Deterministic Conflict Resolution

When storing a memory that overlaps with an existing one (same user, same
type, high vector similarity), the agent explicitly updates rather than
duplicates. The update is a tool call, not a background LLM decision:

1. Agent calls `store_memory` with content.
2. System finds existing memory above similarity threshold.
3. System returns the match to the agent with a prompt to confirm update.
4. Agent calls `update_memory` with the revised content.
5. Old content is preserved in a `previous_content` field for audit.

### User Memory Management

Users can view and manage their memories through the UI and API:

- **View**: List all memories with type, content, source conversation, and
  timestamps.
- **Edit**: Correct a memory's content (triggers re-embedding).
- **Delete**: Remove a memory permanently.
- **Search**: Semantic search across memories ("what does Aether know about
  my lights?").

## Components

### Database Entity

**`AgentMemory`** — new table in `src/storage/entities/`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | PK |
| `user_id` | String(100) | FK-like reference to user, indexed |
| `agent_id` | UUID | Agent that created this memory, FK to `agent` |
| `memory_type` | Enum | `preference`, `decision`, `correction`, `device_pattern`, `instruction` |
| `content` | Text | Human-readable memory content |
| `embedding` | Vector(dim) | pgvector embedding for semantic search |
| `source_conversation_id` | UUID | Conversation where memory was created, FK to `conversation` |
| `source_message_id` | UUID | Message that triggered the memory, FK to `message` |
| `previous_content` | Text | Prior content before last update (audit trail) |
| `metadata` | JSONB | Structured data (entity IDs, room, etc.) |
| `is_active` | Boolean | Soft-delete flag, default true |
| `created_at` | Timestamp | Creation time |
| `updated_at` | Timestamp | Last update time |

### Data Access Layer

**`MemoryRepository`** in `src/dal/memory.py`

- `store(user_id, content, memory_type, embedding, ...)` — insert new memory
- `search(user_id, query_embedding, top_k, threshold)` — pgvector similarity search
- `find_similar(user_id, embedding, threshold)` — find potential duplicates
- `update(memory_id, content, new_embedding)` — update with audit trail
- `delete(memory_id)` — soft-delete (set `is_active = false`)
- `list_by_user(user_id, memory_type?, limit, offset)` — paginated listing
- `hard_delete(memory_id)` — permanent removal (user-initiated)

### Agent Tools

| Tool | Agent | Description |
|------|-------|-------------|
| `store_memory` | Architect, Analysts | Store a new memory for the current user |
| `update_memory` | Architect, Analysts | Update an existing memory (with audit trail) |
| `recall_memories` | Architect, Analysts | Retrieve relevant memories for a query |
| `list_memories` | Architect | List user's memories (for chat-based management) |
| `delete_memory` | Architect | Soft-delete a memory |

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
| `GET /api/v1/memories/{id}` | GET | Get single memory |
| `PUT /api/v1/memories/{id}` | PUT | Update memory content |
| `DELETE /api/v1/memories/{id}` | DELETE | Delete memory |
| `POST /api/v1/memories/search` | POST | Semantic search across memories |

### UI

- **Settings → Memories** page: list, search, edit, delete memories.
- **Chat activity panel**: "Aether remembered: ..." when a memory is stored.
- **Memory indicator**: subtle badge when the agent uses recalled memories in
  a response.

### Context Injection

The memory retrieval is wired into `_build_messages` on the Architect (and
other agents). Before generating a response:

1. Embed the latest user message.
2. Query `MemoryRepository.search()` with top-k (default 5) and threshold.
3. Format retrieved memories as a `SystemMessage` block injected after the
   main system prompt and before conversation history.
4. Track which memories were used in the response metadata for observability.

## Constitution Check

- **Safety First**: Memory storage is an explicit agent tool call — no
  autonomous background extraction. Users can view, edit, and delete all
  memories. No memory influences mutating actions without HITL approval.
- **Isolation**: No new external services. pgvector runs within existing
  PostgreSQL. Embedding calls go through the same LLM provider pipeline.
- **Observability**: Every memory write/read is a traced tool call in MLflow.
  Retrieved memories are logged in response metadata.
- **State**: Memories are durable in PostgreSQL. No in-memory-only state.
  Aligns with "Postgres for durable checkpointing."
- **Security**: Memories are scoped per `user_id` — no cross-user leakage.
  API endpoints require authentication. Memory content is validated via
  Pydantic. Embedding vectors are not sensitive (derived from content
  already stored in plaintext messages).

## Acceptance Criteria

- **Given** the user states a preference in chat, **when** the Architect
  decides to remember it, **then** a `store_memory` tool call appears in the
  trace and the memory is persisted in PostgreSQL with a valid embedding.
- **Given** stored memories exist, **when** the user starts a new conversation
  on a related topic, **then** the agent's response reflects recalled
  memories without the user repeating themselves.
- **Given** a memory already exists for "hallway lights at 40%", **when** the
  user says "make it 30%", **then** the agent updates the existing memory
  (not a duplicate) and the `previous_content` field preserves "40%".
- **Given** the user visits Settings → Memories, **then** they see all active
  memories with type, content, source, and timestamps.
- **Given** the user deletes a memory via UI, **then** it no longer appears
  in retrieval results for any future conversation.
- **Given** a conversation with no relevant memories, **then** the agent
  behaves identically to today (no performance regression).
- **Given** the embedding service is unavailable, **then** the agent falls
  back to operating without memory retrieval (graceful degradation, not a
  hard failure).

## Out of Scope

- Automatic background memory extraction (no hidden LLM calls).
- Graph-based memory (entity relationships, multi-hop reasoning).
- Memory sharing across users / multi-tenant memory isolation.
- Memory-based proactive suggestions (e.g. "you usually turn on lights now").
- Embedding model fine-tuning or custom training.
- Memory import/export.
