# Implementation Plan: YAML Schema Compiler/Validator (Structural)

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-02-09

## Summary

Replace ad-hoc YAML validation with a schema-driven framework. Pydantic models define HA config schemas, compile to JSON Schema, and validate parsed YAML at both generation and deployment time.

## Technical Approach

### Module Structure

```
src/schema/
    __init__.py          # Public API: validate_yaml(), get_schema(), registry
    core.py              # YAMLValidator, SchemaRegistry, ValidationResult
    ha/
        __init__.py      # Registers all HA schemas with registry
        automation.py    # HAAutomation + discriminated union triggers/actions/conditions
        dashboard.py     # LovelaceDashboard, View, Card schemas
        script.py        # HAScript schema
        scene.py         # HAScene schema
        common.py        # Shared types: Mode, EntityId, ServiceName, Duration
```

### Core Framework (`src/schema/core.py`)

- `ValidationError(BaseModel)` — path (JSONPath), message, schema_path
- `ValidationResult(BaseModel)` — valid, errors, warnings, schema_name
- `SchemaRegistry` — register Pydantic models by name, compile to JSON Schema, validate
- `validate_yaml(content: str, schema_name: str) -> ValidationResult` — top-level convenience

Uses `jsonschema` library for JSON Schema validation engine.

### HA Schemas (`src/schema/ha/`)

- **common.py** — `Mode` enum, `EntityId`/`ServiceName` annotated strings
- **automation.py** — `HAAutomation` with discriminated union `Trigger` (state, time, sun, numeric_state, event, template, webhook, zone, tag, device, calendar, mqtt), `Action` (service call, delay, wait, choose, if/then, repeat, event, stop), `Condition` (state, time, sun, numeric_state, template, zone, trigger, and/or/not)
- **dashboard.py** — `LovelaceDashboard`, `View`, base `Card` type
- **script.py** — `HAScript` (alias, sequence, mode, fields)
- **scene.py** — `HAScene` (name, entities map)

### Integration

1. `src/ha/automation_deploy.py` `validate_automation_yaml()` → delegates to `validate_yaml(content, "ha.automation")`
2. `src/diagnostics/config_validator.py` `validate_automation_yaml()` → same
3. `src/tools/dashboard_tools.py` `validate_dashboard_yaml()` → delegates to `validate_yaml(content, "ha.dashboard")`
4. Agent generation (architect, developer) → call `validate_yaml()` after YAML generation

### New Dependency

- `jsonschema>=4.20.0` added to `pyproject.toml` dependencies

## Constitution Check

- **Safety**: Validation catches bad configs before they reach HA — improves safety
- **Isolation**: N/A — no sandbox involvement
- **Observability**: Validation errors included in MLflow traces (via existing tracing)
- **Reliability**: Comprehensive test coverage for all schema models (valid + invalid fixtures)
- **Security**: No credential handling; Pydantic input validation throughout
