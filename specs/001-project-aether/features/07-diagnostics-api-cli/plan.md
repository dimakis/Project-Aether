# Plan: Diagnostics API & CLI

**Feature**: [spec.md](./spec.md) | **Tasks**: [tasks.md](./tasks.md)

## Summary

Add REST API endpoints and CLI commands that wrap the `src/diagnostics/` module (built in Feature 06). Pure surface area -- no new intelligence, just HTTP/CLI adapters.

## Implementation Phases

### Phase 1: API Schemas
Create Pydantic response models for all diagnostic endpoints.

### Phase 2: API Routes
Create `src/api/routes/diagnostics.py` with FastAPI endpoints that call diagnostics module functions.

### Phase 3: CLI Commands
Add `aether diagnose` and `aether health` command groups to the CLI.

### Phase 4: Integration & E2E Tests
Test the full stack: API -> diagnostics module -> mocked MCP.

## Dependencies

- Feature 06 (HA Diagnostics Core) must be complete
- Existing FastAPI app structure in `src/api/`
- Existing CLI structure in `src/cli/`

## Estimated Effort

- API Schemas: 1-2 hours
- API Routes: 2-3 hours
- CLI Commands: 2-3 hours
- Tests: 3-4 hours

**Total**: ~8-12 hours
