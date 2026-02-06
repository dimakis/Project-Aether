# Tasks: Diagnostic Collaboration

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## State Changes

- [ ] T301 Add `DIAGNOSTIC = "diagnostic"` to AnalysisType enum in src/graph/state.py
- [ ] T302 Add `diagnostic_context: str | None = None` field to AnalysisState in src/graph/state.py

## New HA Diagnostic Tools

- [ ] T303 [P] Add `get_ha_logs` tool to src/tools/ha_tools.py wrapping MCPClient.get_error_log()
- [ ] T304 [P] Add `check_ha_config` tool to src/tools/ha_tools.py wrapping MCPClient.check_config()
- [ ] T305 Add tests for get_ha_logs and check_ha_config in tests/unit/test_ha_tools.py

## Enhanced Entity History

- [ ] T306 Enhance `get_entity_history` in src/tools/agent_tools.py with detailed mode (gap detection, stats, 20 recent changes)
- [ ] T307 Add tests for enhanced get_entity_history in tests/unit/test_ha_tools.py or test_agent_tools.py

## Diagnostic Delegation Tool

- [ ] T308 Add `diagnose_issue` delegation tool to src/tools/agent_tools.py
- [ ] T309 Add tests for diagnose_issue in tests/unit/test_data_scientist.py

## Data Scientist Diagnostic Mode

- [ ] T310 Add DIAGNOSTIC branch to _build_analysis_prompt() in src/agents/data_scientist.py
- [ ] T311 Update _collect_energy_data() to handle diagnostic mode in src/agents/data_scientist.py
- [ ] T312 Update DATA_SCIENTIST_SYSTEM_PROMPT with diagnostic capabilities
- [ ] T313 Add tests for diagnostic mode in tests/unit/test_data_scientist.py

## Architect Prompt Update

- [ ] T314 Update ARCHITECT_SYSTEM_PROMPT in src/agents/architect.py with diagnostic workflow guidance

## Wire Exports

- [ ] T315 Register get_ha_logs, check_ha_config in get_ha_tools() in src/tools/__init__.py
- [ ] T316 Register diagnose_issue in get_agent_tools() in src/tools/__init__.py

## Documentation

- [ ] T317 Update docs/architecture.md with diagnostic collaboration flow
- [ ] T318 Update specs/001-project-aether/plan.md agent capabilities section
