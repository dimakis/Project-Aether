# Implementation Plan: YAML Schema Validator — Semantic Validation

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-02-09  
**Prerequisite**: [Feature 26: Structural Validation](../26-yaml-schema-validator/plan.md)

## Summary

Add a semantic validation layer on top of Feature 26's structural schema validator. Uses cached HA registry data to verify entity existence, service validity, and data field compatibility at validation time.

## Technical Approach

### Module Structure (additions to Feature 26)

```
src/schema/
    semantic.py          # SemanticValidator, SemanticValidationRule
    ha/
        registry_cache.py   # HARegistryCache — caches entities, services, areas, devices
        semantic_rules.py   # HA-specific semantic rules (entity exists, service valid, etc.)
```

### Components

1. **`SemanticValidator`** — accepts a `ValidationResult` from structural validation, runs semantic rules against parsed YAML data, returns enriched `ValidationResult` with semantic errors/warnings
2. **`HARegistryCache`** — fetches and caches entity registry, service registry, areas, devices from HA. Configurable TTL. Async-friendly.
3. **Semantic rules** — pluggable rule functions:
   - `entity_exists` — check entity_id against registry
   - `service_valid` — check domain.service against service registry
   - `service_data_valid` — check data fields against service field schema
   - `domain_consistent` — check entity domain matches service domain
   - `area_exists` / `device_exists` — check targets

### Integration

- `validate_yaml()` gains an optional `semantic=True` parameter
- Agent generation uses `semantic=True` for rich feedback
- Pre-deploy uses `semantic=True` as final safety net
- CLI gains `--semantic` flag

## Constitution Check

- **Safety**: Semantic validation prevents deploying automations referencing non-existent entities
- **Isolation**: N/A
- **Observability**: Semantic errors traced via MLflow
- **Reliability**: Tests use mock HA registry (no live HA dependency in tests)
- **Security**: Registry cache stores only entity/service metadata, no credentials
