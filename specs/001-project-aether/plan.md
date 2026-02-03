# Implementation Plan: Project Aether

**Branch**: `001-project-aether` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-project-aether/spec.md`

## Summary

Project Aether is a LangGraph-based multi-agent system for intelligent home automation. It features a Librarian agent for Home Assistant entity discovery, an R&D Loop (Categorizer, Architect, Developer) for automation design with human-in-the-loop approval, and a Data Scientist for energy optimization insights. The system abstracts HA entities into a dynamic Data Access Layer (DAL), supports conversational design via the Architect agent, and generates custom dashboards—all while maintaining full observability through MLflow and running generated scripts in gVisor sandboxes.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: LangGraph, FastAPI, hass-mcp, MLflow, Pydantic, OpenAI Responses API  
**Storage**: PostgreSQL 15+ (state checkpoints, conversation history, entity cache)  
**Testing**: pytest, pytest-asyncio, testcontainers  
**Target Platform**: Linux server (containerized via Podman)  
**Project Type**: Single project with CLI + API interfaces  
**Performance Goals**: Entity discovery <2min for 500 entities, automation proposals <60s, dashboard generation <30s  
**Constraints**: All scripts sandboxed via gVisor (runsc), HITL approval for all automations  
**Scale/Scope**: Single-user home automation, 500+ entities, weeks of historical data

### Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Agent Orchestration | LangGraph | State machine for multi-agent workflows, built-in checkpointing |
| LLM API | OpenAI Responses API | Streaming, function calling, conversation continuity |
| HA Integration | hass-mcp (MCP) | Model Context Protocol for Home Assistant access |
| Containerization | Podman | Rootless containers, systemd integration |
| Script Sandbox | gVisor (runsc) | User-space kernel isolation for generated scripts |
| Observability | MLflow | Experiment tracking, agent tracing, model registry |
| Database | PostgreSQL | ACID compliance, JSON support, LangGraph checkpoint storage |
| API Framework | FastAPI | Async, OpenAPI generation, Pydantic validation |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with Aether Home Architect Constitution principles:

- **Safety First**: ✅ COMPLIANT — FR-005 requires HITL approval for all automations. The Architect agent presents proposals requiring explicit user approval before HA state changes.
- **Isolation**: ✅ COMPLIANT — FR-007 requires gVisor sandbox. Data Scientist generated scripts execute in runsc containers via Podman.
- **Observability**: ✅ COMPLIANT — FR-006 requires MLflow tracing. All agent negotiations, insights, and decisions are logged to MLflow.
- **State**: ✅ COMPLIANT — FR-008 requires checkpointing. LangGraph manages workflow state; PostgreSQL stores durable checkpoints.

**Gate Status**: ✅ PASSED — All constitution principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-aether/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI specs)
│   ├── api.yaml         # Main API contract
│   └── events.yaml      # Event schemas
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── agents/
│   ├── __init__.py
│   ├── librarian.py      # HA entity discovery agent
│   ├── categorizer.py    # Entity categorization agent
│   ├── architect.py      # Automation design agent (conversational)
│   ├── developer.py      # Automation implementation agent
│   └── data_scientist.py # Energy analysis agent
├── dal/
│   ├── __init__.py
│   ├── entities.py       # Entity abstraction layer
│   ├── queries.py        # Natural language query interface
│   └── sync.py           # HA entity sync/reconciliation
├── graph/
│   ├── __init__.py
│   ├── state.py          # LangGraph state definitions
│   ├── nodes.py          # Graph node implementations
│   └── workflows.py      # Agent workflow definitions
├── sandbox/
│   ├── __init__.py
│   ├── runner.py         # gVisor script execution
│   └── policies.py       # Sandbox security policies
├── storage/
│   ├── __init__.py
│   ├── checkpoints.py    # LangGraph checkpoint persistence
│   ├── conversations.py  # Chat history storage
│   └── models.py         # SQLAlchemy models
├── tracing/
│   ├── __init__.py
│   └── mlflow.py         # MLflow integration
├── api/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── routes/
│   │   ├── entities.py   # Entity endpoints
│   │   ├── chat.py       # Architect chat endpoints
│   │   ├── insights.py   # Data Scientist endpoints
│   │   └── dashboards.py # Dashboard endpoints
│   └── schemas/          # Pydantic request/response models
└── cli/
    ├── __init__.py
    └── main.py           # CLI entry point

tests/
├── conftest.py
├── contract/             # API contract tests
├── integration/          # End-to-end agent tests
└── unit/                 # Unit tests per module

infrastructure/
├── podman/
│   ├── Containerfile     # Main application container
│   └── compose.yaml      # Podman compose for local dev
├── gvisor/
│   └── config.toml       # runsc configuration
└── postgres/
    └── init.sql          # Database schema
```

**Structure Decision**: Single project structure chosen. The system is a unified agent platform with CLI and API interfaces, not a web application with separate frontend/backend. All agents share the same codebase and communicate through LangGraph workflows.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
