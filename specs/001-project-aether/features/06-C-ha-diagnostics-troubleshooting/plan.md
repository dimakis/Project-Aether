**Completed**: 2026-02-07

# Plan: Home Assistant Diagnostics & Troubleshooting

**Feature**: [spec.md](./spec.md) | **Tasks**: [tasks.md](./tasks.md)

## Implementation Phases

### Phase 1: MCP Client Extensions
Add REST API methods for logs, config check, integration diagnostics.

**Deliverable**: MCPClient can fetch logs, check config, query integration status

### Phase 2: Log Analysis
Build log parser and error pattern matching.

**Deliverable**: Structured error analysis with known-issue detection

### Phase 3: Entity & Integration Diagnostics
Create health check utilities for entities and integrations.

**Deliverable**: Comprehensive entity/integration health reports

### Phase 4: Agent Tools
Create LangChain tools for diagnostic queries.

**Deliverable**: Agents can diagnose issues via tool calls

### Phase 5: Troubleshooting Intelligence
Build fix suggestion database and guided troubleshooting.

**Deliverable**: Agent can suggest fixes for common issues

### Phase 6: API & CLI
Expose diagnostic features via API and CLI.

**Deliverable**: Full programmatic access to diagnostics

## Dependencies

- US1 (Entity Discovery): Need entity data for health checks
- MCPClient base: `get_error_log()` and `check_config()` already implemented

## Risks

| Risk | Mitigation |
|------|------------|
| HA version differences in diagnostic APIs | Feature detection, graceful fallback |
| Large log files | Pagination, time-based filtering |
| Incorrect fix suggestions | Conservative suggestions, always verify |
| Privacy in logs | Sanitize before display, don't expose tokens |

## Success Metrics

- Agent correctly identifies root cause 80% of the time
- Fix suggestions resolve issue 60% of the time without escalation
- Users report diagnostic features save significant troubleshooting time

## Estimated Effort

- MCP Client: 2-3 hours
- Log Analysis: 3-4 hours
- Entity/Integration Diagnostics: 3-4 hours
- Agent Tools: 2-3 hours
- Troubleshooting Intelligence: 4-5 hours
- API/CLI: 2-3 hours
- Tests: 3-4 hours

**Total**: ~20-26 hours
