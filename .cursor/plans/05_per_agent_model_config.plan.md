---
name: "Per-Agent Model Configuration — Systematic Approach"
overview: |
  Extend the model configuration system so every agent can have its own model, temperature,
  and fallback — configured via a unified YAML/env structure rather than one-off settings per
  agent. The DB-backed config with versioning becomes the primary path; env vars become the
  bootstrap/override layer.
status: draft
priority: medium
estimated_effort: "M (1-2 sprints)"
risk: "Low — additive; existing resolution chain preserved as fallback"
---

# 1. Problem

Only `data_scientist` has per-agent env vars (`data_scientist_model`, `data_scientist_temperature`).
The resolution chain (context → DB → env → global) is correct in principle, but:

- Adding a new agent-specific override requires a new Settings field, a new env var, and
  updating `resolve_model()` — it doesn't scale.
- The model tier system (`fast`/`standard`/`frontier`) classifies models but isn't used for
  automatic agent-to-tier routing.
- The DB-backed config is the right long-term path but requires manual seeding and API calls
  to configure. There's no declarative "desired state" config file.

# 2. Target Configuration

```yaml
# config/agent_models.yaml (or env var AGENT_MODELS as JSON)
agent_models:
  orchestrator:
    model: gpt-4o-mini
    temperature: 0.0
    tier: fast
  architect:
    model: claude-sonnet-4
    temperature: 0.7
    tier: frontier
    fallback_model: gpt-4o
  data_scientist:
    model: deepseek-coder
    temperature: 0.2
    tier: standard
  knowledge:
    model: gpt-4o-mini
    temperature: 0.3
    tier: fast
  # Agents not listed use the global default (llm_model / llm_temperature)
```

Resolution order (unchanged, but sources expanded):
1. **Runtime context** (user model selection via UI)
2. **DB active config** (versioned, promotable — production path)
3. **Agent models config file** (declarative desired state — bootstrap/dev path)
4. **Global default** (`llm_model` / `llm_temperature`)

# 3. Plan

## Phase 1 — Unified agent model settings

- [ ] Create `AgentModelConfig` Pydantic model: `model`, `temperature`, `tier`, `fallback_model`
- [ ] Add `agent_models: dict[str, AgentModelConfig] = {}` to `Settings`
- [ ] Support loading from:
  - Env var `AGENT_MODELS` (JSON string)
  - Config file `config/agent_models.yaml` (loaded at startup if exists)
- [ ] Deprecate `data_scientist_model` / `data_scientist_temperature` (map to new structure)

## Phase 2 — Update resolve_model()

- [ ] `src/agents/model_context.py` `resolve_model()`:
  - After DB check, before global default: check `settings.agent_models.get(agent_name)`
  - Pass `agent_name` to `resolve_model()` (currently some callers don't pass it)
- [ ] Add model tier routing: if `AgentModelConfig.tier` is set but `model` is not,
      use `resolve_model_for_tier(tier, available_models)` to pick a model
- [ ] Update all `resolve_model()` call sites to pass `agent_name`

## Phase 3 — DB seed from config file

- [ ] On startup: if `config/agent_models.yaml` exists and agent has no DB config,
      seed the DB agent config from the file (one-time bootstrap)
- [ ] Update `src/api/routes/agents/seed.py` to use the new config structure
- [ ] The DB config remains the authoritative runtime source; the file is bootstrap-only

## Phase 4 — API surface

- [ ] `GET /agents/models` — return current effective model config per agent
  (merges all resolution levels with indicators of which level each value came from)
- [ ] `PUT /agents/{agent_name}/model` — update DB config for an agent
- [ ] `POST /agents/models/sync` — re-seed DB from config file (admin action)

## Phase 5 — UI integration

- [ ] Agent Settings page: show per-agent model config with resolution source
- [ ] Allow model/temperature override from UI (writes to DB config)
- [ ] Show model tier badge (fast/standard/frontier) per agent

## Phase 6 — Tests

- [ ] Unit test: `resolve_model()` with all resolution levels
- [ ] Unit test: config file loading and parsing
- [ ] Unit test: DB seed from config file
- [ ] Unit test: deprecation mapping for `data_scientist_model`

# 4. Migration

- Existing `data_scientist_model` / `data_scientist_temperature` env vars continue to work
  (mapped to `agent_models.data_scientist.model` / `.temperature` internally)
- If neither the new config nor old env vars are set, behavior is unchanged (global default)
- DB config always wins over file config (existing behavior preserved)

# 5. Success Criteria

- Any agent's model can be configured without adding new Settings fields
- `config/agent_models.yaml` provides a declarative, version-controllable desired state
- DB config remains the runtime authority with versioning and rollback
- `resolve_model()` is the single entry point for all model resolution
- Model tier system actively routes agents to appropriate models when no explicit model is set
