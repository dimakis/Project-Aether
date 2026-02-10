# Tasks: YAML Schema Validator — Semantic Validation

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Prerequisite**: [Feature 26](../26-yaml-schema-validator/tasks.md) must be complete

---

## Registry Cache (test-first)

- [ ] T220 [P] Create tests/unit/test_ha_registry_cache.py + src/schema/ha/registry_cache.py — HARegistryCache with TTL, entity/service/area/device caching

## Semantic Validator Core (test-first)

- [ ] T221 [P] Create tests/unit/test_semantic_validator.py + src/schema/semantic.py — SemanticValidator, SemanticValidationRule base

## Semantic Rules (test-first)

- [ ] T222 Create tests/unit/test_semantic_rules.py + src/schema/ha/semantic_rules.py — entity_exists, service_valid, service_data_valid, domain_consistent, area_exists, device_exists

## Integration

- [ ] T223 Extend validate_yaml() with optional semantic=True parameter
- [ ] T224 Add semantic validation to agent YAML generation paths
- [ ] T225 Add --semantic flag to CLI validation command

## Integration Tests

- [ ] T226 Create tests/integration/test_semantic_validation.py — validate against mock HA registry
