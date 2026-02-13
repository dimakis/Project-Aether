# Feature: Prompt Registry

**Status**: Planned  
**Priority**: P2  
**Depends on**: 25-ds-team-architecture, 08-model-routing-multi-agent

## Goal

Provide a versioned, DB-backed prompt registry that replaces static markdown files in `src/agents/prompts/`, enabling prompt versioning, A/B experimentation, and observability-linked evaluation.

## Problem Statement

As the agent system grows, the number of prompt files is increasing (system prompts, depth-specific EDA fragments, strategy fragments, per-specialist prompts). Static files in `src/agents/prompts/` have no version history, no way to compare variants, and no link between a prompt version and the quality of the insights it produced. Changing a prompt requires a code deploy.

## User Experience

1. **Browse & Edit**: User navigates to a Prompts page in the UI, sees all registered prompts grouped by agent/purpose, views version history.
2. **Version & Rollback**: Editing a prompt creates a new version. User can diff versions and rollback to any prior version with one click.
3. **Experiment**: User creates an A/B experiment — two prompt variants are assigned a traffic split. Analysis runs are tagged with the variant used.
4. **Evaluate**: MLflow traces link to prompt version. A scheduled evaluation job compares insight quality metrics (confidence, user-actioned rate, Architect satisfaction) across variants.
5. **Tag & Organise**: Prompts are tagged by agent role, analysis depth, execution strategy, and domain (energy, behavioral, diagnostic).

## Core Capabilities

- **Prompt CRUD**: Create, read, update prompts via API and UI. Each update creates an immutable version.
- **Version History**: Full history per prompt with diffs, timestamps, author.
- **A/B Experiments**: Define experiments with two variants and a traffic split percentage. Tag each analysis run with the variant used.
- **MLflow Integration**: Each prompt invocation logs the prompt ID + version as an MLflow param. Evaluation scorers can compare metrics by prompt version.
- **Agent Resolution**: `load_prompt(name)` resolves: active experiment variant (if any) > latest version > file fallback. Backward-compatible with existing file-based prompts during migration.
- **Seed from Files**: Migration command that imports all existing `src/agents/prompts/*.md` files as v1 entries in the registry.

## Data Model

- `prompts` table: id, name (unique), description, agent_role, tags (JSON), created_at, updated_at
- `prompt_versions` table: id, prompt_id (FK), version (int, auto-increment per prompt), content (TEXT), author, created_at
- `prompt_experiments` table: id, prompt_id, variant_a_version, variant_b_version, traffic_split_pct, status (active/completed), start_at, end_at, metrics (JSON)

## API Endpoints

- `GET /prompts` -- list with filters (agent_role, tag)
- `GET /prompts/{id}` -- prompt with latest version
- `GET /prompts/{id}/versions` -- version history
- `GET /prompts/{id}/versions/{version}` -- specific version content
- `POST /prompts` -- create new prompt
- `PUT /prompts/{id}` -- update (creates new version)
- `POST /prompts/{id}/experiments` -- create A/B experiment
- `PUT /prompts/{id}/experiments/{exp_id}` -- update/complete experiment
- `POST /prompts/seed` -- import from file system

## Constitution Check

- **Safety First**: Prompts shape agent behavior. Version history provides audit trail. Rollback enables rapid response if a prompt causes undesirable agent actions.
- **Isolation**: No impact on sandbox isolation.
- **Observability**: MLflow integration ensures every agent action is linked to the exact prompt version that produced it.
- **State**: PostgreSQL for prompt storage (Constitution: State).
- **Security**: Prompt editing requires authentication. No user-supplied content is executed (prompts are LLM instructions, not code).
