# Implementation Plan: Prompt Registry

**Feature**: [spec.md](./spec.md)  
**Status**: Planned  
**Date**: 2026-02-13

## Summary

Replace static file-based prompts with a versioned DB-backed registry, add A/B experimentation, and link prompt versions to MLflow traces for evaluation.

## Architecture

```
load_prompt(name)
    │
    ├── Check active experiment → variant selection (A/B split)
    │
    ├── Resolve version → latest or experiment variant
    │
    ├── DB lookup (prompt_versions table)
    │
    └── Fallback → file system (src/agents/prompts/*.md)
```

## Implementation Details

### Phase 1: Core Registry
- DB models: `prompts`, `prompt_versions` tables
- `PromptRepository` with CRUD + version management
- `load_prompt()` resolver: DB > file fallback
- API endpoints for CRUD and version history
- Seed command to import existing files

### Phase 2: A/B Experimentation
- `prompt_experiments` table
- Traffic splitting in `load_prompt()` (deterministic hash on conversation_id)
- MLflow param logging: prompt_id, prompt_version, experiment_variant
- API endpoints for experiment management

### Phase 3: UI
- Prompts page: list, view, edit with diff viewer
- Version history timeline
- Experiment creation and monitoring dashboard
- Metrics comparison view (linked to MLflow)

### Phase 4: Evaluation Integration
- Scheduled scorer that compares prompt variants by insight quality
- Auto-complete experiments when statistical significance reached
- Dashboard widgets for prompt performance

## Files to Create

- `src/storage/entities/prompt.py` -- Prompt, PromptVersion, PromptExperiment models
- `src/dal/prompt_repository.py` -- Data access layer
- `src/agents/prompt_registry.py` -- Resolution logic (replaces direct file reads)
- `src/api/routes/prompts.py` -- API endpoints
- `migrations/versions/0xx_prompt_registry.py` -- DB migration
- `ui/src/pages/prompts/` -- UI pages

## Files to Modify

- `src/agents/base_analyst.py` -- Use `load_prompt()` from registry instead of file
- `src/agents/architect.py` -- Same
- `src/agents/data_scientist.py` -- Same
- `src/tracing/` -- Log prompt version as MLflow param
