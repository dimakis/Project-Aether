# Feature Specification: Model Routing & Multi-Agent Communication

**Feature Branch**: `001-project-aether`
**Created**: 2026-02-07
**Status**: Superseded by `08-C-model-routing-multi-agent/`
**Depends On**: US1 (Entity Discovery), US2 (Architect), US3 (Data Scientist)

## Problem Statement

1. **Model selection doesn't propagate**: When a user picks a model in Open WebUI, the Architect uses it, but delegated agents (Data Scientist) fall back to the default from `.env`, ignoring the user's choice.
2. **No per-agent model tiers**: All LLM-using agents share a single model config. The Architect needs strong reasoning for tool selection + conversation; the Data Scientist only generates structured Python scripts and could use a cheaper/faster model.
3. **No reverse communication**: Specialist agents cannot proactively suggest actions back to the Architect (e.g., Data Scientist discovering an optimization and suggesting an automation).

## User Stories

### US-M1: Model Propagation Through Delegation

As a user selecting a model in Open WebUI, I want all agents involved in my request to use my chosen model, so that I get consistent behavior regardless of which specialist agent handles part of the work.

**Acceptance Criteria**:
1. When I select `anthropic/claude-sonnet-4` and ask about energy, the Data Scientist uses `claude-sonnet-4` (not the `.env` default).
2. When no model context is set (CLI, direct API), agents fall back to their configured defaults.

### US-M2: Per-Agent Model Configuration

As a system operator, I want to pin specific agents to specific models via `.env`, so that I can optimize cost (cheap model for script generation) while keeping the Architect on a premium model.

**Acceptance Criteria**:
1. Setting `DATA_SCIENTIST_MODEL=gpt-4o-mini` in `.env` causes the Data Scientist to always use that model.
2. Per-agent settings override the global default but are overridden by explicit user selection from the UI.
3. Resolution order: user selection > per-agent setting > global default.

### US-M3: Insight-Driven Automation Suggestions

As a user, when the Data Scientist discovers a high-impact optimization, I want to be informed that an automation could address it, so that I can ask the Architect to design it.

**Acceptance Criteria**:
1. When the Data Scientist produces a high-confidence insight with an actionable suggestion, the Architect's response includes a prompt like "The Data Scientist suggests creating an automation for X. Shall I design one?"
2. The user can accept or ignore the suggestion naturally in conversation.

## Requirements

### Functional

- **FR-M01**: Model context MUST propagate from the OpenAI-compatible endpoint through agent delegation.
- **FR-M02**: Per-agent model settings MUST be configurable via environment variables.
- **FR-M03**: Model resolution MUST follow: explicit context > per-agent setting > global default.
- **FR-M04**: Data Scientist insights MUST be able to carry automation suggestions.
- **FR-M05**: Inter-agent MLflow trace spans MUST show parent-child relationships.

### Non-Functional

- **NFR-M01**: Model context propagation MUST add <1ms overhead per delegation.
- **NFR-M02**: Existing CLI and API behavior MUST NOT change when no model context is set.
