# Feature: YAML Schema Validator — Semantic Validation

**Status**: Not Started  
**Priority**: P3  
**Phase**: 2 of 2  
**Prerequisite**: [Feature 26: YAML Schema Compiler/Validator (Structural)](../26-yaml-schema-validator/spec.md)

## Goal

Extend the structural YAML schema validator (Feature 26) with semantic validation that verifies YAML content against live Home Assistant state — entity existence, service validity, domain compatibility, and service data field schemas.

## Description

Feature 26 delivers structural validation: required keys, types, enum values, trigger platform discrimination. But structural validity alone does not guarantee a working automation. Common failure modes include:

- Referencing an `entity_id` that does not exist in HA
- Calling a `service` that is not registered in HA
- Passing `data` fields that the service does not accept (e.g., `brightness` for a switch)
- Using a `device_id` or `area_id` that does not exist
- Trigger platform referencing a non-existent entity domain

This feature adds a semantic validation layer that enriches the static Pydantic schemas with live HA data at runtime.

### Capabilities

1. **Entity existence** — Validate that referenced `entity_id` values exist in the HA entity registry
2. **Service validation** — Validate that `domain.service` calls reference registered HA services
3. **Service data fields** — Validate that `data` payloads match the service's field schema (selectors, required fields)
4. **Domain consistency** — Validate that entity domains match expected types (e.g., `light.*` for `light.turn_on`)
5. **Area/device existence** — Validate `area_id` and `device_id` targets exist
6. **Introspection caching** — Cache HA registry data to avoid repeated API calls during validation

### Architecture Extension

The semantic validator sits on top of Feature 26's `SchemaRegistry`:

```
SchemaRegistry.validate()          ← structural (Feature 26)
    ↓
SemanticValidator.validate()       ← semantic (this feature)
    ↓ queries
HARegistryCache                    ← cached HA entity/service/area/device data
    ↓ fetches
HAClient                           ← live HA API
```

## Independent Test

1. Create automation YAML referencing `light.nonexistent_light`
2. Structural validation passes (valid structure)
3. Semantic validation returns warning: "entity_id 'light.nonexistent_light' not found in HA registry"

## Dependencies

- Feature 26 (structural validation framework) — must be complete
- `src/ha/client.py` — HAClient for entity/service introspection
- HA MCP tools — `list_entities`, `search_entities_tool`, `domain_summary_tool`

## MCP Tools Used

- `list_entities` — enumerate all entities for existence checks
- `search_entities_tool` — entity lookup
- `domain_summary_tool` — domain enumeration
- `call_service_tool` — (indirectly) service registry queries
