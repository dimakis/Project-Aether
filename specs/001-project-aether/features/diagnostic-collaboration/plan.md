# Implementation Plan: Diagnostic Collaboration

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-02-06

## Summary

Enable Architect-DS collaborative troubleshooting by exposing existing MCPClient diagnostic methods as tools, enhancing entity history output, adding a diagnostic delegation tool, and extending the Data Scientist with a diagnostic analysis mode.

## Architecture

The collaborative flow leverages the Architect's existing tool-calling loop — no new workflow graph needed:

```
User → Architect → get_ha_logs() → reads error log
                 → get_entity_history(detailed=true) → identifies data gaps
                 → check_ha_config() → validates config
                 → diagnose_issue(entities, context, instructions) → DS analyzes
       Architect ← DS diagnostic findings + recommendations
User ← Architect presents unified diagnosis
       (Architect can loop: pull more data, refine instructions, re-delegate)
```

## Implementation Details

### New HA diagnostic tools (src/tools/ha_tools.py)
- `get_ha_logs` — wraps MCPClient.get_error_log(), truncates to ~4000 chars
- `check_ha_config` — wraps MCPClient.check_config(), returns validation result

### Enhanced entity history (src/tools/agent_tools.py)
- Add `detailed` flag to get_entity_history (default False)
- Detailed mode: state change count, first/last timestamps, gap detection, state distribution, up to 20 recent changes

### Diagnostic delegation tool (src/tools/agent_tools.py)
- `diagnose_issue(entity_ids, diagnostic_context, instructions, hours)` — creates AnalysisState with DIAGNOSTIC type, passes context to DS

### State changes (src/graph/state.py)
- Add `DIAGNOSTIC = "diagnostic"` to AnalysisType enum
- Add `diagnostic_context: str | None` field to AnalysisState

### DS diagnostic mode (src/agents/data_scientist.py)
- DIAGNOSTIC branch in _build_analysis_prompt() with Architect's context + instructions
- Update _collect_energy_data() to handle diagnostic mode
- Update DATA_SCIENTIST_SYSTEM_PROMPT

### Architect prompt (src/agents/architect.py)
- Update ARCHITECT_SYSTEM_PROMPT with diagnostic capabilities and workflow guidance

### Wire exports (src/tools/__init__.py)
- Register get_ha_logs, check_ha_config, diagnose_issue

## Files Changed

| File | Change |
|------|--------|
| src/tools/ha_tools.py | Add get_ha_logs, check_ha_config |
| src/tools/agent_tools.py | Enhance get_entity_history, add diagnose_issue |
| src/tools/__init__.py | Export new tools |
| src/graph/state.py | Add DIAGNOSTIC enum, diagnostic_context field |
| src/agents/data_scientist.py | Diagnostic prompt, context handling |
| src/agents/architect.py | Update system prompt |
| tests/unit/test_ha_tools.py | Tests for new HA tools |
| tests/unit/test_data_scientist.py | Tests for diagnostic mode |
| docs/architecture.md | Add diagnostic flow |
