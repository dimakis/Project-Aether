# Tasks: Natural Language Automation Builder

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1 -- State & Workflow Skeleton

- [ ] T3601 Create `AutomationBuilderState` typed dict in `src/graph/state/automation_builder.py` -- messages, intent, entities, yaml_draft, validation_errors, similar_automations, proposal_id
- [ ] T3602 Create workflow graph skeleton in `src/graph/workflows/automation_builder.py` -- nodes, edges, HITL interrupt, compilation
- [ ] T3603 Register workflow in `src/graph/workflows/__init__.py`

**Checkpoint**: Workflow compiles with stub nodes

---

## Phase 2 -- Validation Tools (US2, US3)

- [ ] T3604 [P] Create `check_entity_exists` tool in `src/tools/automation_builder_tools.py` -- query `EntityRepository`, return exists/suggestions
- [ ] T3605 [P] Create `find_similar_automations` tool -- query `ha_automations` for matching trigger type + entity overlap
- [ ] T3606 [P] Create `validate_automation_draft` tool -- wrap `validate_yaml()` and `validate_yaml_semantic()` from Feature 26-27
- [ ] T3607 [P] Unit tests in `tests/unit/tools/test_automation_builder_tools.py` -- entity exists, fuzzy match, duplicate found, duplicate not found, YAML valid, YAML invalid

**Checkpoint**: All validation tools tested

---

## Phase 3 -- Node Implementations (US1, US4)

- [ ] T3608 Implement `gather_intent_node` -- Architect LLM extracts trigger, entities, actions from user message; asks clarifying questions if ambiguous
- [ ] T3609 Implement `validate_entities_node` -- iterates entities, calls `check_entity_exists`, routes to correction or proceeds
- [ ] T3610 Implement `check_duplicates_node` -- calls `find_similar_automations`, warns user or proceeds
- [ ] T3611 Implement `generate_yaml_node` -- Architect LLM generates HA automation YAML from validated intent
- [ ] T3612 Implement `validate_yaml_node` -- calls `validate_automation_draft`, loops back to generate on errors
- [ ] T3613 Implement `preview_node` -- formats YAML, creates `AutomationProposal` (PROPOSED), presents to user
- [ ] T3614 Reuse `developer_deploy_node` from conversation workflow for deployment
- [ ] T3615 [P] Unit tests for each node in `tests/unit/graph/test_automation_builder_nodes.py`

**Checkpoint**: All nodes implemented and tested

---

## Phase 4 -- Integration

- [ ] T3616 Register `automation_builder` tool group in tool registry (Feature 34) with seed migration
- [ ] T3617 Add workflow preset in chat UI for "Create Automation" (routing hint in Architect)
- [ ] T3618 Wire push notification on successful deployment (Feature 37 `InsightNotifier` pattern)
- [ ] T3619 Integration test: full flow from NL input to YAML preview to mock deployment

**Checkpoint**: Feature complete, end-to-end flow verified

---

`[P]` = Can run in parallel (different files, no dependencies)
