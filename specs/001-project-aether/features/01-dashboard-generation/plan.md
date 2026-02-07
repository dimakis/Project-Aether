# Implementation Plan: Custom Dashboard Generation

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-02-06 (migrated from project tasks.md)

## Summary

Add a dashboard generation capability to Aether. The system uses entity context from the DAL and user preferences to generate Lovelace YAML configurations. A Dashboard agent handles generation and validation, while deployment supports both direct HA integration (when WebSocket API is available) and export mode.

## Technical Approach

### Models

- `Dashboard` model in `src/storage/models.py` — id, conversation_id, name, description, theme, layout, entities, status, ha_dashboard_id, deployed_at
- Alembic migration for the Dashboard table

### Agent

- `src/agents/dashboard.py` — Lovelace YAML generation using entity context from DAL
- Uses LLM to translate user preferences (theme, layout, specific entities) into valid Lovelace card configurations

### DAL

- `src/dal/dashboards.py` — Dashboard CRUD and Lovelace schema validation

### Deployment

- `src/mcp/dashboard_deploy.py` — Deployment strategy selection
- Export mode: generate downloadable YAML for user import
- Direct mode: requires HA Lovelace WebSocket API (not currently available via MCP)

### API

- `src/api/schemas/dashboards.py` — Dashboard, DashboardList, DashboardExport schemas
- `src/api/routes/dashboards.py` — CRUD + export + deploy endpoints

### CLI

- `aether dashboards list/show/export` — list and export dashboards
- `aether dashboards generate` — generate with theme/area options

## Constitution Check

- **Safety First**: N/A — dashboards don't control home state
- **Isolation**: N/A — no script generation
- **Observability**: Dashboard generation should be traced via MLflow
- **State**: Dashboard state managed via PostgreSQL
