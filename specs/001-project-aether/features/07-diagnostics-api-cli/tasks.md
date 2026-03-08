# Tasks: Diagnostics API & CLI

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Carried from**: Feature 06 tasks T516-T519, T525-T529

---

## API Schemas

- [x] T601 Create src/api/schemas/diagnostics.py:
  - ErrorLogResponse, ConfigCheckResponse
  - EntityDiagnosticResponse, IntegrationHealthResponse
  - TroubleshootingRequest, TroubleshootingResponse

## API Routes

- [x] T602 Create src/api/routes/diagnostics.py:
  - GET /diagnostics/ha-health - HA health check
  - GET /diagnostics/error-log - Recent errors with analysis
  - GET /diagnostics/config-check - Validate configuration
  - GET /diagnostics/traces/recent - Recent trace spans

## CLI Commands

- [ ] T603 Add `aether diagnose` commands to src/cli/main.py (**Not implemented**):
  - `aether diagnose errors` - Show recent errors
  - `aether diagnose errors --integration zigbee` - Filter by integration
  - `aether diagnose config` - Validate configuration
  - `aether diagnose entity <entity_id>` - Entity health check
  - `aether diagnose integration <domain>` - Integration health
  - `aether diagnose --full` - Complete health report

- [ ] T604 Add `aether health` commands (**Not implemented**):
  - `aether health` - Quick system health summary
  - `aether health integrations` - Integration status table
  - `aether health entities` - Entity availability summary

## Tests

**Integration Tests**:
- [x] T605 Diagnostics API integration tests
- [x] T606 Entity diagnostics tests
- [x] T607 Integration health tests

**E2E Tests**:
- [ ] T608 Create tests/e2e/test_troubleshooting_flow.py
- [ ] T609 Create tests/e2e/test_health_check.py
