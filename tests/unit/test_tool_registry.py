"""Tests for the Architect tool registry.

Verifies:
- get_architect_tools() returns exactly 15 curated tools
- All expected tool names are present (including get_automation_config/get_script_config)
- No duplicate tool names
- Old delegation/mutation tools are NOT in the Architect set
- get_all_tools() still returns the full superset (backward compat)
- consult_data_science_team is the only DS delegation tool on the Architect
- consult_dashboard_designer is available for dashboard requests
"""

from __future__ import annotations

import pytest


EXPECTED_ARCHITECT_TOOLS = {
    # HA query — DB-backed (7)
    "get_entity_state",
    "list_entities_by_domain",
    "search_entities",
    "get_domain_summary",
    "list_automations",
    "get_automation_config",
    "get_script_config",
    # HA query — live (3)
    "render_template",
    "get_ha_logs",
    "check_ha_config",
    # Approval (1)
    "seek_approval",
    # Scheduling (1)
    "create_insight_schedule",
    # Discovery (1)
    "discover_entities",
    # DS Team (1)
    "consult_data_science_team",
    # Dashboard (1)
    "consult_dashboard_designer",
}

# Tools that should NOT be on the Architect (old delegation, mutation, etc.)
EXCLUDED_FROM_ARCHITECT = {
    # Old DS delegation
    "analyze_energy",
    "analyze_behavior",
    "diagnose_issue",
    "propose_automation_from_insight",
    "get_entity_history",
    # Individual specialist tools (absorbed by team tool)
    "consult_energy_analyst",
    "consult_behavioral_analyst",
    "consult_diagnostic_analyst",
    "request_synthesis_review",
    # Custom analysis (absorbed by team tool)
    "run_custom_analysis",
    # Mutation tools (Developer handles via seek_approval)
    "control_entity",
    "deploy_automation",
    "delete_automation",
    "create_script",
    "create_scene",
    "create_input_boolean",
    "create_input_number",
    "fire_event",
    # Diagnostic tools (DiagnosticAnalyst owns)
    "analyze_error_log",
    "find_unavailable_entities",
    "diagnose_entity",
    "check_integration_health",
    "validate_config",
}


class TestGetArchitectTools:
    """Verify the curated Architect tool set."""

    def test_exact_count(self):
        from src.tools import get_architect_tools

        tools = get_architect_tools()
        assert len(tools) == 15, (
            f"Expected 15 tools, got {len(tools)}: "
            f"{[t.name for t in tools]}"
        )

    def test_expected_names(self):
        from src.tools import get_architect_tools

        names = {t.name for t in get_architect_tools()}
        assert names == EXPECTED_ARCHITECT_TOOLS

    def test_no_duplicates(self):
        from src.tools import get_architect_tools

        names = [t.name for t in get_architect_tools()]
        assert len(names) == len(set(names)), (
            f"Duplicate tools: {[n for n in names if names.count(n) > 1]}"
        )

    def test_excluded_tools_absent(self):
        from src.tools import get_architect_tools

        names = {t.name for t in get_architect_tools()}
        overlap = names & EXCLUDED_FROM_ARCHITECT
        assert not overlap, f"Excluded tools found on Architect: {overlap}"

    def test_delegation_tools_are_correct(self):
        """Only consult_data_science_team and consult_dashboard_designer should be delegation tools."""
        from src.tools import get_architect_tools

        names = {t.name for t in get_architect_tools()}
        delegation_tools = {n for n in names if "consult" in n or "analyst" in n}
        assert delegation_tools == {"consult_data_science_team", "consult_dashboard_designer"}


class TestGetAllToolsBackwardCompat:
    """get_all_tools() must still return the full superset."""

    def test_includes_old_tools(self):
        from src.tools import get_all_tools

        names = {t.name for t in get_all_tools()}
        # It should include the team tool AND the individual specialist tools
        assert "consult_data_science_team" in names
        assert "consult_energy_analyst" in names
        assert "analyze_energy" in names

    def test_superset_of_architect(self):
        from src.tools import get_all_tools, get_architect_tools

        all_names = {t.name for t in get_all_tools()}
        architect_names = {t.name for t in get_architect_tools()}
        assert architect_names.issubset(all_names)
