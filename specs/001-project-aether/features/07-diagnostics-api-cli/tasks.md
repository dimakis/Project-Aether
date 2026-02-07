# Tasks: Diagnostics API & CLI

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Carried from**: Feature 06 tasks T516-T519, T525-T529

---

## API Schemas

- [ ] T601 Create src/api/schemas/diagnostics.py:
  - ErrorLogResponse, ConfigCheckResponse
  - EntityDiagnosticResponse, IntegrationHealthResponse
  - TroubleshootingRequest, TroubleshootingResponse

## API Routes

- [ ] T602 Create src/api/routes/diagnostics.py:
  - GET /diagnostics/errors - Recent errors with analysis
  - GET /diagnostics/errors/{integration} - Errors for integration
  - POST /diagnostics/config-check - Validate configuration
  - GET /diagnostics/entities/unavailable - List unavailable
  - GET /diagnostics/entities/{id} - Entity diagnostic
  - GET /diagnostics/integrations - All integration health
  - GET /diagnostics/integrations/{domain} - Single integration
  - POST /diagnostics/troubleshoot - Run guided troubleshooting

## CLI Commands

- [ ] T603 Add `aether diagnose` commands to src/cli/main.py:
  - `aether diagnose errors` - Show recent errors
  - `aether diagnose errors --integration zigbee` - Filter by integration
  - `aether diagnose config` - Validate configuration
  - `aether diagnose entity <entity_id>` - Entity health check
  - `aether diagnose integration <domain>` - Integration health
  - `aether diagnose --full` - Complete health report

- [ ] T604 Add `aether health` commands:
  - `aether health` - Quick system health summary
  - `aether health integrations` - Integration status table
  - `aether health entities` - Entity availability summary

## Tests

**Integration Tests**:
- [ ] T605 Create tests/integration/test_error_log_analysis.py
- [ ] T606 Create tests/integration/test_entity_diagnostics.py
- [ ] T607 Create tests/integration/test_integration_health.py

**E2E Tests**:
- [ ] T608 Create tests/e2e/test_troubleshooting_flow.py
- [ ] T609 Create tests/e2e/test_health_check.py
