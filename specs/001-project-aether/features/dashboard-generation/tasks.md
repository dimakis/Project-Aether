# Tasks: Custom Dashboard Generation

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Migrated from**: `specs/001-project-aether/tasks.md` Phase 6 (US4)

---

## Models

- [ ] T106 [P] [US4] Create Dashboard model in src/storage/models.py per data-model.md (id, conversation_id, name, description, theme, layout, entities, status, ha_dashboard_id, deployed_at)
- [ ] T107 [US4] Create Alembic migration for Dashboard table in alembic/versions/005_dashboards.py

## Dashboard Generation

- [ ] T108 [US4] Create src/agents/dashboard.py with Lovelace YAML generation using entity context
- [ ] T109 [US4] Create src/dal/dashboards.py with Dashboard CRUD and Lovelace validation
- [ ] T110 [US4] **Workaround**: Generate dashboard YAML for manual import OR use HA storage API if available

## Dashboard Deployment

- [ ] T111 [US4] Create src/mcp/dashboard_deploy.py with deployment strategy selection
- [ ] T112 [US4] Implement "export" mode: generate downloadable YAML for user import
- [ ] T113 [US4] **Note**: Direct dashboard deployment requires HA Lovelace WebSocket API (not in current MCP)

## API Endpoints

- [ ] T114 [P] [US4] Create dashboard schemas in src/api/schemas/dashboards.py (Dashboard, DashboardList, DashboardExport)
- [ ] T115 [US4] Create src/api/routes/dashboards.py with GET /dashboards, GET /dashboards/{id}, GET /dashboards/{id}/export, POST /dashboards/{id}/deploy

## CLI Commands

- [ ] T116 [US4] Add `aether dashboards list/show/export` commands in src/cli/main.py
- [ ] T117 [US4] Add `aether dashboards generate` command with theme/area options

## Tests (Constitution: Reliability & Quality)

**Unit Tests**:
- [ ] T118 [P] [US4] Create tests/unit/test_dashboard_generator.py - Lovelace YAML generation
- [ ] T119 [P] [US4] Create tests/unit/test_dal_dashboards.py - Dashboard CRUD
- [ ] T120 [P] [US4] Create tests/unit/test_lovelace_validation.py - YAML schema validation

**Integration Tests**:
- [ ] T121 [US4] Create tests/integration/test_dashboard_workflow.py - Generation pipeline
- [ ] T122 [US4] Create tests/integration/test_api_dashboards.py - Dashboard API

**E2E Tests**:
- [ ] T123 [US4] Create tests/e2e/test_dashboard_generation.py - Full generation and export
