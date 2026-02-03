# Research: Project Aether

**Feature Branch**: `001-project-aether`  
**Date**: 2026-02-03

## Overview

This document captures research findings for Project Aether's technical decisions. Each section documents a decision, its rationale, and alternatives considered.

---

## 1. Agent Orchestration: LangGraph

**Decision**: Use LangGraph for multi-agent orchestration and state management.

**Rationale**:
- Native support for stateful, cyclical agent workflows (vs. linear chains)
- Built-in checkpointing to PostgreSQL for state persistence
- First-class support for human-in-the-loop interrupts (critical for HITL approval)
- Graph-based visualization of agent workflows for debugging
- Streaming support for real-time conversation with Architect agent

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| LangChain Agents | Linear execution model doesn't support cyclical R&D loop; no native checkpointing |
| AutoGen | More suited for code generation; less control over state transitions |
| CrewAI | Task-based model less suitable for conversational Architect agent |
| Custom orchestration | Significant engineering overhead for state management and checkpointing |

**Implementation Notes**:
- Use `StateGraph` for defining agent workflow topology
- Implement custom `Checkpointer` backed by PostgreSQL
- Use `interrupt_before` for HITL approval gates
- Define typed state with Pydantic models for validation

---

## 2. Home Assistant Integration: hass-mcp

**Decision**: Use hass-mcp (Model Context Protocol) for Home Assistant integration.

**Rationale**:
- MCP provides structured, typed access to HA entities and services
- Already validated working in development environment
- Supports entity discovery, state queries, and service calls
- Abstracts WebSocket/REST complexity

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Direct HA REST API | More boilerplate; no structured entity discovery |
| HA WebSocket API | Complex connection management; MCP handles this |
| PyHomeAssistant | Outdated; MCP is the modern standard |

**Implementation Notes**:
- Librarian agent wraps hass-mcp for entity discovery
- Cache discovered entities in PostgreSQL for offline queries
- Subscribe to HA events for real-time entity change detection
- Environment variables: `HA_TOKEN`, `HA_URL`

---

## 3. Script Sandboxing: gVisor (runsc)

**Decision**: Execute Data Scientist generated scripts in gVisor sandboxes via Podman.

**Rationale**:
- Constitution requires isolation for generated scripts (Principle II)
- gVisor provides user-space kernel that intercepts syscalls
- Lighter than full VMs; compatible with OCI containers
- Podman's rootless mode + gVisor provides defense-in-depth

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Docker + seccomp | Weaker isolation; shared kernel attack surface |
| Firecracker microVMs | Overkill for script execution; slower startup |
| nsjail | Less maintained; gVisor has broader adoption |
| WASM sandbox | Python support immature; complex FFI for data science libs |

**Implementation Notes**:
- Configure Podman with `--runtime=runsc`
- Pre-built sandbox container with pandas, numpy, matplotlib
- Mount read-only data volumes; no network access
- Timeout execution at 5 minutes
- Capture stdout/stderr for insight extraction

---

## 4. Observability: MLflow

**Decision**: Use MLflow for agent tracing and experiment tracking.

**Rationale**:
- Constitution requires tracing for all agent negotiations (Principle III)
- MLflow Tracking provides structured logging of parameters, metrics, artifacts
- Experiment comparison for A/B testing automation strategies
- Model registry for versioning agent prompts/configurations
- Self-hosted; no data leaves the network

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| LangSmith | SaaS only; data privacy concerns for home automation |
| OpenTelemetry | Lower-level; requires more custom instrumentation |
| Weights & Biases | SaaS-first; MLflow better for local deployment |
| Custom logging | No experiment comparison; significant overhead |

**Implementation Notes**:
- Deploy MLflow server alongside main application
- Create experiment per agent type (Librarian, Architect, etc.)
- Log: agent inputs, outputs, latency, token usage, decisions
- Use MLflow artifacts for storing generated scripts and insights
- Integrate with LangGraph callbacks for automatic tracing

---

## 5. State Persistence: PostgreSQL

**Decision**: Use PostgreSQL for all persistent state.

**Rationale**:
- Constitution requires durable checkpointing (Principle IV)
- LangGraph has native PostgreSQL checkpointer
- JSONB columns for flexible entity/insight storage
- ACID compliance for conversation history integrity
- Mature, well-understood technology

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| SQLite | Concurrent access issues with multiple agents |
| Redis | Not durable by default; checkpoint data could be lost |
| MongoDB | Overkill; PostgreSQL JSONB sufficient for schema flexibility |
| DuckDB | Optimized for analytics, not transactional workloads |

**Implementation Notes**:
- Use SQLAlchemy for ORM with async support
- Tables: `entities`, `conversations`, `checkpoints`, `insights`, `automations`
- LangGraph checkpoint table managed by framework
- Connection pooling via asyncpg

---

## 6. LLM Integration: OpenAI Responses API

**Decision**: Use OpenAI Responses API for agent intelligence.

**Rationale**:
- User-specified technology choice
- Streaming responses for real-time Architect conversation
- Function calling for structured agent actions
- Conversation continuity via message history

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Anthropic Claude | User specified OpenAI |
| Local LLM (Ollama) | Performance/quality tradeoffs for complex reasoning |
| Azure OpenAI | Additional cloud dependency |

**Implementation Notes**:
- Use `openai` Python SDK with async client
- Implement retry logic with exponential backoff
- Cache common queries to reduce API costs
- Log all LLM interactions to MLflow

---

## 7. Containerization: Podman

**Decision**: Use Podman for container orchestration.

**Rationale**:
- User-specified technology choice
- Rootless containers for better security
- Daemonless architecture; systemd integration
- OCI-compliant; compatible with gVisor runtime
- Podman Compose for local development

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Docker | Requires daemon; rootless mode less mature |
| Kubernetes | Overkill for single-user home automation |

**Implementation Notes**:
- Create Containerfile for main application
- Use Podman Compose for local dev (app + postgres + mlflow)
- Configure gVisor as runtime for sandbox containers
- Systemd unit files for production deployment

---

## 8. API Framework: FastAPI

**Decision**: Use FastAPI for HTTP API endpoints.

**Rationale**:
- Native async support for agent streaming
- Automatic OpenAPI documentation
- Pydantic integration for request/response validation
- WebSocket support for real-time chat

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Flask | No native async; less modern |
| Django | Too heavyweight for API-only service |
| Starlette | FastAPI builds on it with better DX |

**Implementation Notes**:
- Use dependency injection for database sessions
- WebSocket endpoint for Architect chat streaming
- Background tasks for long-running agent workflows
- Health check endpoints for container orchestration

---

## 9. Entity Abstraction: Dynamic DAL

**Decision**: Build a custom Data Access Layer abstracting HA entities.

**Rationale**:
- FR-002 requires natural language entity queries
- Decouple agent logic from HA entity_id specifics
- Support entity categorization (room, type, capability)
- Enable semantic search ("living room lights" → entity_ids)

**Design Approach**:
- Entity model with: id, ha_entity_id, friendly_name, domain, area, capabilities, state
- Query interface supporting natural language via LLM
- Sync service detecting HA changes via MCP events
- Cache layer for fast queries without HA round-trips

**Implementation Notes**:
- Use Pydantic models for Entity schema
- Implement semantic similarity for NL queries (embedding-based)
- Background task for periodic sync (every 5 minutes per FR-003)
- Event-driven updates when HA pushes changes

---

## 10. Package Management: uv

**Decision**: Use `uv` for Python package management, virtual environments, and project tooling.

**Rationale**:
- Extremely fast (10-100x faster than pip) - written in Rust by Astral (ruff authors)
- Unified tool: replaces pip, pip-tools, virtualenv, pyenv in one
- Lock file support (`uv.lock`) for reproducible builds
- Compatible with `pyproject.toml` and PEP standards
- Active development, modern Python packaging best practices

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| pip + venv | Slow; no lock file without pip-tools |
| pip-tools | Separate tool; uv does this natively |
| Poetry | Slower; uv is faster and simpler |
| PDM | Less mature ecosystem; uv has better DX |
| conda | Overkill; uv handles pure Python deps well |

**Implementation Notes**:
- Initialize project with `uv init` or manage via `pyproject.toml`
- Create venv with `uv venv`
- Install dependencies with `uv pip install` or `uv sync`
- Lock dependencies with `uv lock`
- CI/CD: `uv sync --frozen` for reproducible installs
- Dev dependencies managed via `[project.optional-dependencies]` or `[tool.uv]`

---

## 11. HITL Approval Flow

**Decision**: Implement approval gates using LangGraph interrupts.

**Rationale**:
- Constitution Principle I requires HITL for all automations
- LangGraph's `interrupt_before` provides native support
- Approval state persisted in checkpoints for recovery

**Design Approach**:
1. Architect agent proposes automation → state saved
2. Graph interrupts at "approval" node
3. User reviews via API/CLI → approves or rejects
4. Graph resumes from checkpoint with decision
5. Developer agent implements if approved

**Implementation Notes**:
- Define `ApprovalState` with proposal, user_decision, timestamp
- API endpoint: `POST /automations/{id}/approve`
- Timeout after 24 hours; proposals expire
- Rollback endpoint: `POST /automations/{id}/rollback`

---

## Summary of Decisions

| Area | Decision | Key Rationale |
|------|----------|---------------|
| Agent Orchestration | LangGraph | Stateful workflows, HITL interrupts, checkpointing |
| HA Integration | hass-mcp | Structured MCP access, validated working |
| Script Sandbox | gVisor + Podman | Constitution compliance, user-space isolation |
| Observability | MLflow | Self-hosted tracing, experiment tracking |
| State Persistence | PostgreSQL | LangGraph native, ACID, JSONB flexibility |
| LLM API | OpenAI Responses API | User requirement, streaming, function calling |
| Containers | Podman | User requirement, rootless, gVisor runtime |
| API Framework | FastAPI | Async, OpenAPI, WebSocket support |
| Entity Abstraction | Custom DAL | NL queries, semantic search, caching |
| Package Management | uv | Fast, unified tooling, lock files, Rust-based |
| HITL Approval | LangGraph interrupts | Constitution compliance, checkpoint-based |

All NEEDS CLARIFICATION items have been resolved. Ready for Phase 1 implementation.
