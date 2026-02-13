# Tasks: Prompt Registry

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1: Core Registry

- [ ] T3201 Create `prompts` and `prompt_versions` DB models in src/storage/entities/prompt.py
- [ ] T3202 Create Alembic migration for prompt tables
- [ ] T3203 Create `PromptRepository` with CRUD + version management in src/dal/prompt_repository.py
- [ ] T3204 Create `load_prompt()` resolver with DB > file fallback in src/agents/prompt_registry.py
- [ ] T3205 Create API routes for prompt CRUD and version history in src/api/routes/prompts.py
- [ ] T3206 Create seed command to import existing src/agents/prompts/*.md files
- [ ] T3207 Wire `load_prompt()` into BaseAnalyst, Architect, DataScientist (backward-compatible)

## Phase 2: A/B Experimentation

- [ ] T3208 Create `prompt_experiments` DB model and migration
- [ ] T3209 Add experiment-aware variant selection to `load_prompt()` (deterministic hash split)
- [ ] T3210 Log prompt_id, prompt_version, experiment_variant as MLflow params
- [ ] T3211 Add API routes for experiment CRUD

## Phase 3: UI

- [ ] T3212 Create Prompts list page with agent/tag filters
- [ ] T3213 Create Prompt detail page with version history and diff viewer
- [ ] T3214 Create Prompt editor with preview
- [ ] T3215 Create Experiment management UI

## Phase 4: Evaluation

- [ ] T3216 Scheduled scorer comparing prompt variants by insight quality metrics
- [ ] T3217 Auto-complete experiments on statistical significance
- [ ] T3218 Dashboard widgets for prompt performance comparison
