---
name: "Selective Remote Agents — Granular Deployment"
overview: |
  Replace the binary monolith/distributed toggle with per-agent remote configuration.
  Allow specific compute-heavy agents to be pushed out to separate services while keeping
  lightweight agents in-process. The infrastructure (dual_mode.py, A2A client/service) already
  exists — this is primarily a config-surface change.
status: draft
priority: medium
estimated_effort: "S (1-2 sprints)"
risk: "Low — additive change to existing infrastructure"
---

# 1. Problem

`DEPLOYMENT_MODE` is all-or-nothing: either every agent runs in-process (monolith) or every
agent runs as a separate A2A service (distributed). The jump from monolith to distributed
requires container orchestration for 8+ services. In practice, only compute-heavy agents
(data_scientist, energy_analyst, behavioral_analyst, diagnostic_analyst) benefit from being
remote — the Orchestrator, Architect, Knowledge, and Developer are lightweight and better
kept in-process.

`dual_mode.py` already resolves per-agent via `_AGENT_CLASS_MAP` and `_AGENT_URL_MAP`, but
the config is gated by a single global `deployment_mode` check.

# 2. Target Configuration

```yaml
# .env or settings
DEPLOYMENT_MODE=selective                    # new mode alongside monolith/distributed
REMOTE_AGENTS=data_scientist,energy_analyst  # only these agents are remote

# Per-agent service URLs (existing settings, only needed for remote agents)
DS_ORCHESTRATOR_URL=http://ds-service:8001
ENERGY_ANALYST_URL=http://analyst-service:8002
```

# 3. Plan

## Phase 1 — Extend settings

- [ ] Add `remote_agents: list[str] = []` to `Settings`
- [ ] Add `"selective"` to `deployment_mode: Literal["monolith", "distributed", "selective"]`
- [ ] Validation: if `deployment_mode == "selective"`, `remote_agents` must be non-empty
- [ ] Validation: each agent in `remote_agents` must have a corresponding `*_service_url` set
- [ ] Document in `.env.example`

## Phase 2 — Update dual_mode.py

- [ ] Modify `resolve_agent_invoker(agent_name)`:
  ```python
  if settings.deployment_mode == "monolith":
      return local_invoker(agent_name)
  elif settings.deployment_mode == "distributed":
      return remote_invoker(agent_name)  # existing behavior
  elif settings.deployment_mode == "selective":
      if agent_name in settings.remote_agents:
          return remote_invoker(agent_name)
      else:
          return local_invoker(agent_name)
  ```
- [ ] Add startup validation: log which agents are local vs remote
- [ ] Add `/status` endpoint info: show per-agent deployment mode

## Phase 3 — Health checking for selective mode

- [ ] On startup (selective mode): verify remote agent URLs are reachable
- [ ] Add per-agent health status to `/status` response
- [ ] Fallback behavior: if a remote agent is unreachable, option to fall back to local
  - [ ] New setting: `remote_agent_fallback: bool = False`
  - [ ] If enabled and remote fails: log warning, resolve locally
  - [ ] If disabled and remote fails: raise clear error

## Phase 4 — Compose template for selective mode

- [ ] Create `infrastructure/podman/compose.selective.yaml`
- [ ] Only define services for agents listed in `REMOTE_AGENTS`
- [ ] Document how to add/remove agents from the remote set

## Phase 5 — Tests

- [ ] Unit test: `resolve_agent_invoker` in selective mode routes correctly
- [ ] Unit test: validation rejects selective mode without `remote_agents`
- [ ] Unit test: validation rejects remote agents without service URLs
- [ ] Unit test: fallback behavior when `remote_agent_fallback=True`
- [ ] Integration test: mixed local/remote agent invocation

# 4. Migration

- Default `deployment_mode` remains `"monolith"` — no breaking change
- `"distributed"` continues to work as-is
- `"selective"` is opt-in

# 5. Success Criteria

- Can run `DEPLOYMENT_MODE=selective REMOTE_AGENTS=data_scientist` and have only
  the DS agent call out via A2A while everything else runs in-process
- `/status` shows per-agent mode (local/remote) and health
- Clear error messages when remote agents are misconfigured
