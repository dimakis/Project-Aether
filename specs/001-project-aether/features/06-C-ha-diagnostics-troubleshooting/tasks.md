**Completed**: 2026-02-07

# Tasks: Home Assistant Diagnostics & Troubleshooting

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**User Story**: US8

---

## Scope Note

Core diagnostic intelligence (MCP extensions, diagnostics module, agent tools, tests)
implemented in Feature 06. API routes, CLI commands, integration/E2E tests, and
advanced troubleshooting workflows deferred to [Feature 07](../07-diagnostics-api-cli/).

---

## MCP Client Extensions

Note: `get_error_log()` and `check_config()` already added to MCPClient.

- [x] T501 [US8] Add integration diagnostics to src/mcp/client.py:
  - `list_config_entries()` - GET /api/config/config_entries
  - `get_config_entry_diagnostics(entry_id)` - GET diagnostics
  - `reload_config_entry(entry_id)` - POST reload (requires HITL)

- [x] T502 [US8] Add service discovery to src/mcp/client.py:
  - `list_services()` - GET /api/services (all available services)
  - `list_event_types()` - GET /api/events

- [ ] T503 [US8] Add system health methods to src/mcp/client.py — *deferred to Feature 07*

## Log Analysis

- [x] T504 [US8] Create src/diagnostics/log_parser.py:
  - ErrorLogEntry dataclass
  - parse_error_log(log_text) - Parse raw log into entries
  - categorize_by_integration(entries) - Group by logger/integration
  - find_patterns(entries) - Detect recurring errors
  - get_error_summary(entries) - Summary stats

- [x] T505 [US8] Create src/diagnostics/error_patterns.py:
  - KNOWN_ERROR_PATTERNS list (regex -> fix suggestion)
  - match_known_errors(entry) - Find matching patterns
  - analyze_errors(entries) - Batch analysis with suggestions

## Entity Diagnostics

- [x] T506 [US8] Create src/diagnostics/entity_health.py:
  - EntityDiagnostic dataclass
  - find_unavailable_entities(mcp) - List unavailable entities
  - find_stale_entities(mcp, hours) - Entities not updated recently
  - correlate_unavailability(diagnostics) - Find common cause

- [x] T507 [US8] Create src/diagnostics/integration_health.py:
  - IntegrationHealth dataclass
  - get_integration_statuses(mcp) - All integration states
  - find_unhealthy_integrations(mcp) - Filter to problem integrations
  - diagnose_integration(mcp, entry_id) - Full health report

## Config Validation

- [x] T508 [US8] Create src/diagnostics/config_validator.py:
  - ConfigCheckResult dataclass
  - run_config_check(mcp) - Call check_config API
  - parse_config_errors(raw_result) - Extract structured errors
  - validate_automation_yaml(yaml_str) - Local validation before deploy

## Agent Tools

- [x] T509 [P] [US8] Create src/tools/diagnostic_tools.py:
  - `analyze_error_log` - Fetch + analyze HA error log
  - `find_unavailable_entities` - List unavailable entities
  - `diagnose_entity(entity_id)` - Full entity health check
  - `check_integration_health` - Integration status
  - `validate_config` - Validate HA configuration

- [ ] T510 [P] [US8] Advanced troubleshooting tools — *deferred to Feature 07*

- [x] T511 [US8] Register diagnostic tools in src/tools/__init__.py

## Troubleshooting Workflows

- [ ] T512 [US8] TroubleshootingAgent — *deferred to Feature 07*
- [ ] T513 [US8] fix_suggestions.py — *deferred to Feature 07*

## System Prompt Extensions

- [ ] T514 [US8] DIAGNOSTICIAN_SYSTEM_PROMPT — *deferred to Feature 07*

- [x] T515 [US8] Extend ArchitectAgent system prompt with diagnostic tool descriptions

## API Endpoints

- [ ] T516–T517 [US8] — *deferred to Feature 07*

## CLI Commands

- [ ] T518–T519 [US8] — *deferred to Feature 07*

## Tests

**Unit Tests** (all TDD: test first, then implement):
- [x] T520 [P] [US8] tests/unit/test_log_parser.py (16 tests)
- [x] T521 [P] [US8] tests/unit/test_error_patterns.py (12 tests)
- [x] T522 [P] [US8] tests/unit/test_entity_health.py (9 tests)
- [x] T522b [P] [US8] tests/unit/test_integration_health.py (7 tests)
- [x] T523 [P] [US8] tests/unit/test_config_validator.py (12 tests)
- [x] T524 [P] [US8] tests/unit/test_diagnostic_tools.py (12 tests)
- [x] T524b [P] [US8] tests/unit/test_mcp_client_diagnostics.py (11 tests)

**Integration / E2E Tests**:
- [ ] T525–T529 [US8] — *deferred to Feature 07*
