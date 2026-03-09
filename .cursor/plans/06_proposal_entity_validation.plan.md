---
name: "Mandatory Entity Validation at Proposal Creation"
overview: |
  Enforce semantic validation (entity existence, domain compatibility, service support) at
  automation proposal creation time — not just when the optional validate_automation_draft
  tool is called. This closes the gap between "valid YAML" and "will actually work when
  deployed", using the Librarian's entity catalog via HARegistryCache.
status: draft
priority: high
estimated_effort: "S (1 sprint)"
risk: "Low — validation infrastructure already exists; this wires it into the proposal path"
---

# 1. Problem

The schema validation system (`src/schema/`) is thorough — Pydantic models for every HA
trigger, condition, and action type, plus `SemanticValidator` with `HARegistryCache` for
entity existence checks. But:

- **Proposal creation** (`_create_automation_proposal()` in `approval_tools.py`) only checks
  that `trigger` and `actions` fields are present — no structural or semantic validation.
- **Semantic validation** only runs if the agent explicitly calls `validate_automation_draft`.
- **Deploy path** can receive proposals with invalid entity IDs, wrong entity domains for
  trigger types, or unsupported service calls.

For the business/industrial pitch, deploying a broken automation to a factory floor is
unacceptable. Validation must be mandatory at proposal creation, not optional.

# 2. Target Behavior

```
Agent builds YAML → _create_automation_proposal()
                        │
                        ├─ 1. Structural validation (existing validate_yaml)
                        ├─ 2. Semantic validation (existing validate_yaml_semantic)
                        │     • Entity existence against HARegistryCache
                        │     • Domain compatibility (sensor vs binary_sensor for trigger type)
                        │     • Service call validity (entity supports the service + attributes)
                        │     • Area existence
                        ├─ 3. If validation fails:
                        │     • Return validation errors to agent (not user)
                        │     • Agent can fix and retry
                        │     • Proposal is NOT created
                        └─ 4. If validation passes:
                              • Create proposal with validation_status = "passed"
                              • Proceed to HITL approval
```

# 3. Plan

## Phase 1 — Wire validation into proposal creation

- [ ] In `_create_automation_proposal()` (approval_tools.py):
  - Call `validate_yaml(yaml_content)` for structural validation
  - Call `validate_yaml_semantic(yaml_content, ha_client)` for semantic validation
  - If either fails: return structured error response to the agent (not an exception)
  - If both pass: create proposal as normal
- [ ] Add `validation_status: Literal["passed", "skipped", "failed"]` field to `AutomationProposal` entity
- [ ] Add `validation_errors: list[str] | None` field to `AutomationProposal` entity

## Phase 2 — Enhance semantic validation coverage

- [ ] **Domain compatibility checks** (semantic.py):
  - Trigger `platform: state` → entity must be a state-reporting entity
  - Trigger `platform: device` → device_id must exist
  - `binary_sensor` vs `sensor` distinction for trigger conditions
- [ ] **Service attribute validation**:
  - Service call `light.turn_on` with `brightness` → entity must support `brightness` attribute
  - Use HA service descriptions (already available via `list_services()`) to validate fields
- [ ] **Template variable validation**:
  - If template uses `trigger.to_state.attributes.X`, verify the entity has attribute X
  - This is best-effort (runtime values can't be statically checked)

## Phase 3 — Agent feedback loop

- [ ] When validation fails, return a structured response the agent can act on:
  ```python
  {
      "status": "validation_failed",
      "structural_errors": [...],
      "semantic_errors": [
          {"entity_id": "sensor.foo", "error": "entity not found in registry"},
          {"service": "light.turn_on", "field": "brightness",
           "error": "entity light.bar does not support brightness attribute"}
      ],
      "suggestion": "Check entity IDs against the catalog. Use list_entities to verify."
  }
  ```
- [ ] Agent prompt update: instruct agents to use the Librarian's catalog lookup before
      building automations, and to handle validation feedback by fixing and retrying

## Phase 4 — Validation bypass for advanced users

- [ ] Add `skip_validation: bool = False` parameter to proposal creation
- [ ] Only available via explicit API call (not from agent flow)
- [ ] When skipped: `validation_status = "skipped"`, warning in HITL approval UI
- [ ] HITL approval UI shows validation status badge (passed/skipped/failed)

## Phase 5 — HARegistryCache reliability

- [ ] Ensure `HARegistryCache` is populated before first validation attempt
  - On startup: pre-warm cache from last discovery results in DB
  - Fallback: if cache is empty and HA is reachable, fetch live
  - If HA is unreachable: skip semantic validation with `validation_status = "skipped"`
    and a warning, rather than blocking proposal creation entirely
- [ ] Add TTL refresh: cache refreshes every N minutes (configurable)
- [ ] Add cache stats to `/status` health check

## Phase 6 — Tests

- [ ] Unit test: proposal creation with valid YAML → passes, proposal created
- [ ] Unit test: proposal creation with invalid entity → fails, structured error returned
- [ ] Unit test: proposal creation with wrong domain → fails with domain mismatch error
- [ ] Unit test: proposal creation with invalid service attribute → fails
- [ ] Unit test: validation bypass (`skip_validation=True`) → proposal created with warning
- [ ] Unit test: HA unreachable → semantic validation skipped, structural still runs
- [ ] Integration test: full flow — agent builds YAML, validation catches error, agent fixes, proposal created

# 4. Migration

- Existing proposals in the DB won't have `validation_status` — default to `null` / "legacy"
- The `validate_automation_draft` tool remains available for explicit pre-checks but is no
  longer the only path to validation
- No breaking API changes

# 5. Success Criteria

- No automation proposal can be created with a nonexistent entity ID (unless explicitly bypassed)
- Validation errors are structured and actionable for the agent
- HITL approval UI shows validation status
- System degrades gracefully when HA is unreachable (structural validation still runs)
- Zero broken automations deployed due to entity reference errors
