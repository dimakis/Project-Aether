# Implementation Plan: Dynamic Tool Registry

**Feature**: [spec.md](./spec.md)
**Status**: Planned
**Date**: 2026-02-27

## Summary

Replace hardcoded Python tool-grouping functions with a DB-backed `tool_group` table. Agents reference groups in their config version (`tool_groups_enabled` JSONB column) alongside the existing individual `tools_enabled`. The registry resolves groups into tool objects at agent build time, and the mutation registry derives its read-only classification from group metadata with a hardcoded fallback for safety.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, SQLAlchemy (async), Alembic, LangChain
**Storage**: PostgreSQL (JSONB for tool_names)
**Testing**: pytest with async fixtures, DB guard enforced
**Target Platform**: Linux server (Docker/K8s)

## Constitution Check

- **Safety First**: No new HA mutations. Tool assignment changes go through existing config version promotion lifecycle (draft -> active). Mutation registry fail-safe preserved.
- **Isolation**: No script execution involved.
- **Observability**: Tool group resolution logged at INFO level. No new MLflow traces needed.
- **State**: DB-backed (Postgres). No LangGraph state changes.

## Architecture

```
AgentConfigVersion
    |-- tool_groups_enabled: ["ha_entity_query", "diagnostics"]  (NEW)
    |-- tools_enabled: ["web_search"]                            (EXISTING)
    v
get_tools_for_agent(agent_name, tools_enabled, tool_groups_enabled)
    |-- Expand groups: ToolGroupRepository.get_by_names(group_names)
    |       -> flatten tool_names from each group
    |-- Merge individual: tools_enabled UNION expanded_group_names
    |-- Resolve: _tool_name_map[name] for each name
    +-- Fallback: hardcoded curator (architect) or [] (others)
```

## Seed Data (12 groups)

| Group Name | Display Name | is_read_only |
|---|---|---|
| `ha_entity_query` | HA Entity Queries | true |
| `ha_automation_query` | HA Automation Queries | true |
| `ha_live_query` | HA Live Queries | true |
| `ha_mutation` | HA Mutations | false |
| `diagnostics` | Diagnostic Tools | true |
| `specialists` | Specialist Delegation | true |
| `approval` | HITL Approval | true |
| `discovery` | Entity Discovery | true |
| `analysis` | Custom Analysis | false |
| `scheduling` | Insight Scheduling | true |
| `web` | Web Search | true |
| `review` | Config Review | true |

## Key Design Decisions

- **JSONB over join table**: `tool_names` as `list[str]` matches established pattern.
- **Additive column**: `tool_groups_enabled` alongside existing `tools_enabled`. Zero migration risk.
- **Async resolution**: `get_tools_for_agent` becomes async. Single caller is already async.
- **TTL-cached mutation set**: 60s cache. Hardcoded fallback for safety.
- **Seed in migration**: 12 groups seeded via `op.bulk_insert`.

## Files to Create

- `src/storage/entities/tool_group.py` -- ToolGroup entity
- `src/dal/tool_groups.py` -- ToolGroupRepository
- `src/api/schemas/tool_groups.py` -- Pydantic schemas
- `src/api/routes/tool_groups.py` -- CRUD endpoints
- `alembic/versions/031_tool_groups.py` -- Table + seed
- `alembic/versions/032_agent_config_tool_groups.py` -- Add column

## Files to Modify

- `src/storage/entities/agent_config_version.py` -- Add `tool_groups_enabled`
- `src/tools/registry.py` -- Async `get_tools_for_agent` with group expansion
- `src/tools/mutation_registry.py` -- DB-backed classification with fallback
- `src/agents/registry.py` -- Pass `tool_groups_enabled`, await async resolution
- `src/storage/entities/__init__.py`, `src/dal/__init__.py`, `src/api/routes/__init__.py` -- Exports
