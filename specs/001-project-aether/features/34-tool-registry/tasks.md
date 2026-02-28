# Tasks: Dynamic Tool Registry

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1 -- Entity & Migration

- [ ] T3401 Create `ToolGroup` entity in `src/storage/entities/tool_group.py` -- UUID PK, `name` (unique), `display_name`, `description`, `tool_names` (JSONB list[str]), `is_read_only` (bool), timestamps
- [ ] T3402 Export `ToolGroup` from `src/storage/entities/__init__.py`
- [ ] T3403 Create migration `031_tool_groups.py` -- create `tool_group` table with unique constraint on `name`, seed with 12 groups
- [ ] T3404 Create migration `032_agent_config_tool_groups.py` -- add `tool_groups_enabled` JSONB column to `agent_config_version`
- [ ] T3405 Add `tool_groups_enabled` mapped column to `AgentConfigVersion` entity and `create()` factory method

**Checkpoint**: Schema ready, migrations apply cleanly

---

## Phase 2 -- Repository (US1)

- [ ] T3406 [P] Create `ToolGroupRepository` in `src/dal/tool_groups.py` extending `BaseRepository[ToolGroup]` -- `get_by_name(name)`, `get_by_names(names: list[str])`, `list_all()`, `upsert()`
- [ ] T3407 [P] Unit tests in `tests/unit/dal/test_tool_group_repository.py` -- CRUD operations, `get_by_names` returns correct subset, unknown names ignored
- [ ] T3408 Export `ToolGroupRepository` from `src/dal/__init__.py`

**Checkpoint**: Repository tested, data layer complete

---

## Phase 3 -- Tool Resolution (US1, US2)

- [ ] T3409 Refactor `get_tools_for_agent` in `src/tools/registry.py` to async, accept `tool_groups_enabled` param, expand groups via `ToolGroupRepository`, merge with `tools_enabled`, preserve fallback chain
- [ ] T3410 [P] Unit tests in `tests/unit/tools/test_tool_group_resolution.py` -- groups-only, tools-only, groups+tools merge, unknown group warning, empty both falls back to hardcoded, architect fallback preserved
- [ ] T3411 Update `create_agent_from_config` in `src/agents/registry.py` -- extract `tool_groups_enabled` from config, pass to `get_tools_for_agent`, await the now-async call
- [ ] T3412 Add `build_read_only_set_from_db()` to `src/tools/mutation_registry.py` -- async function, TTL-cached (60s), falls back to hardcoded `READ_ONLY_TOOLS` on DB error
- [ ] T3413 [P] Unit tests in `tests/unit/tools/test_mutation_registry_db.py` -- DB-backed classification, fallback on error, TTL cache expiry

**Checkpoint**: Resolution logic works end-to-end, mutation safety verified

---

## Phase 4 -- API (US3)

- [ ] T3414 [P] Create Pydantic schemas in `src/api/schemas/tool_groups.py` -- `ToolGroupResponse`, `ToolGroupListResponse`, `ToolGroupUpdate`, `ToolGroupCreate` with validation
- [ ] T3415 [P] Create API routes in `src/api/routes/tool_groups.py` -- `GET /api/tool-groups` (list), `GET /api/tool-groups/{name}` (detail), `POST /api/tool-groups` (create), `PUT /api/tool-groups/{name}` (update)
- [ ] T3416 Register router in `src/api/routes/__init__.py`
- [ ] T3417 [P] Unit tests in `tests/unit/api/test_tool_groups_api.py`

**Checkpoint**: Full CRUD API tested

---

## Phase 5 -- Polish & Integration

- [ ] T3418 Verify all existing agent tests pass (no regressions from async `get_tools_for_agent`)
- [ ] T3419 Verify existing streaming/tool dispatch tests pass
- [ ] T3420 Add integration test: seed groups, create agent config with `tool_groups_enabled`, resolve tools, verify correct set

**Checkpoint**: Feature complete, all tests green

---

`[P]` = Can run in parallel (different files, no dependencies)
