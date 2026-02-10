# Feature: YAML Schema Compiler/Validator (Structural)

**Status**: In Progress  
**Priority**: P2  
**Phase**: 1 of 2 (see [Phase 2: Semantic Validation](../27-yaml-semantic-validation/spec.md))

## Goal

Build a general-purpose YAML schema validation framework using Pydantic models that compile to JSON Schema, with Home Assistant config schemas as the primary use case. Replace scattered ad-hoc validation with a unified, extensible system.

## Description

YAML validation is currently scattered across 3 files with inconsistent, shallow checks:

- `src/diagnostics/config_validator.py` — checks `alias`, `trigger`, `action` keys exist
- `src/ha/automation_deploy.py` — checks trigger has `platform`/`trigger` key, valid `mode` enum
- `src/tools/dashboard_tools.py` — checks `views` key exists and is a list

Errors in trigger structure, action payloads, or condition logic are only caught when HA rejects them at deploy time. This wastes a human review cycle on structurally invalid proposals.

This feature introduces:

1. **Core framework** (`src/schema/core.py`) — `SchemaRegistry`, `YAMLValidator`, `ValidationResult` with structured error reporting (JSONPath to error location)
2. **HA schemas** (`src/schema/ha/`) — Pydantic models for automations (with discriminated union triggers/actions/conditions), scripts, scenes, and Lovelace dashboards
3. **JSON Schema compilation** — Pydantic models compile to JSON Schema via `.model_json_schema()`, validated with `jsonschema` library
4. **Integration** — Validation at both agent generation time (before proposals) and pre-deploy (before HA API calls)

### Phase 1 Scope (This Feature)

Structural validation only: required keys, types, valid enum values, trigger platform discrimination, action structure. Entity/service existence checks are Phase 2.

## Independent Test

1. Define a valid HA automation YAML string
2. Call `validate_yaml(yaml_str, "ha.automation")` → returns `ValidationResult(valid=True)`
3. Remove the `trigger` key → returns `ValidationResult(valid=False, errors=[...])` with JSONPath

## Dependencies

- `jsonschema>=4.20.0` (new)
- `pydantic>=2.10.0` (existing)
- `PyYAML` (existing, transitive)

## Successor Feature

[Feature 27: YAML Semantic Validation](../27-yaml-semantic-validation/spec.md) — adds entity existence checks, service validation, and HA introspection-based schema enrichment.
