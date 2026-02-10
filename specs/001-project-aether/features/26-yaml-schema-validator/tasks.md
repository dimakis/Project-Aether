# Tasks: YAML Schema Compiler/Validator (Structural)

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Dependencies

- [ ] T200 Add `jsonschema>=4.20.0` to pyproject.toml dependencies

## Core Framework (test-first)

- [ ] T201 [P] Create tests/unit/test_schema_core.py + src/schema/core.py — ValidationResult, ValidationError, SchemaRegistry, validate_yaml()
- [ ] T202 Create src/schema/__init__.py — public API re-exports

## HA Common Types (test-first)

- [ ] T203 [P] Create tests/unit/test_schema_ha_common.py + src/schema/ha/common.py — Mode enum, EntityId, ServiceName, Duration

## HA Automation Schema (test-first)

- [ ] T204 [P] Create tests/unit/test_schema_ha_automation.py + src/schema/ha/automation.py — HAAutomation with trigger/action/condition discriminated unions

## HA Dashboard Schema (test-first)

- [ ] T205 [P] Create tests/unit/test_schema_ha_dashboard.py + src/schema/ha/dashboard.py — LovelaceDashboard, View, Card

## HA Script & Scene Schemas (test-first)

- [ ] T206 Create tests/unit/test_schema_ha_script_scene.py + src/schema/ha/script.py + scene.py

## Schema Registry Integration

- [ ] T207 Create src/schema/ha/__init__.py — auto-register all HA schemas

## Codebase Integration

- [ ] T208 Replace validation in src/ha/automation_deploy.py with schema validator
- [ ] T209 Replace validation in src/diagnostics/config_validator.py with schema validator
- [ ] T210 Replace validation in src/tools/dashboard_tools.py with schema validator
- [ ] T211 Add schema validation in agent YAML generation (architect.py, developer.py)
