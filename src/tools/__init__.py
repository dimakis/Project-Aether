"""Tool registry for Home Assistant interactions and agent delegation.

All tool functions and registry accessors are re-exported here.
Canonical registry logic lives in tools/registry.py.

Uses lazy imports to avoid pulling in the full agent/HA/DB dependency
graph when only a subset of tools is needed.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    # agent_tools
    "analyze_energy": "src.tools.agent_tools",
    "diagnose_issue": "src.tools.agent_tools",
    "discover_entities": "src.tools.agent_tools",
    "get_agent_tools": "src.tools.agent_tools",
    "get_entity_history": "src.tools.agent_tools",
    # analysis_tools
    "get_analysis_tools": "src.tools.analysis_tools",
    "run_custom_analysis": "src.tools.analysis_tools",
    # approval_tools
    "get_approval_tools": "src.tools.approval_tools",
    "seek_approval": "src.tools.approval_tools",
    # automation_builder_tools
    "check_entity_exists": "src.tools.automation_builder_tools",
    "find_similar_automations": "src.tools.automation_builder_tools",
    "get_automation_builder_tools": "src.tools.automation_builder_tools",
    "validate_automation_draft": "src.tools.automation_builder_tools",
    # diagnostic_tools
    "analyze_error_log": "src.tools.diagnostic_tools",
    "check_integration_health": "src.tools.diagnostic_tools",
    "diagnose_entity": "src.tools.diagnostic_tools",
    "find_unavailable_entities_tool": "src.tools.diagnostic_tools",
    "get_diagnostic_tools": "src.tools.diagnostic_tools",
    "validate_config": "src.tools.diagnostic_tools",
    # ha_automation_tools
    "get_automation_config": "src.tools.ha_automation_tools",
    "list_automations": "src.tools.ha_automation_tools",
    # ha_entity_tools
    "control_entity": "src.tools.ha_entity_tools",
    "get_domain_summary": "src.tools.ha_entity_tools",
    "get_entity_state": "src.tools.ha_entity_tools",
    "list_entities_by_domain": "src.tools.ha_entity_tools",
    "search_entities": "src.tools.ha_entity_tools",
    # ha_script_scene_tools
    "get_script_config": "src.tools.ha_script_scene_tools",
    # ha_tools
    "get_ha_tools": "src.tools.ha_tools",
    # ha_utility_tools
    "check_ha_config": "src.tools.ha_utility_tools",
    "get_ha_logs": "src.tools.ha_utility_tools",
    "render_template": "src.tools.ha_utility_tools",
    # insight_schedule_tools
    "create_insight_schedule": "src.tools.insight_schedule_tools",
    "get_insight_schedule_tools": "src.tools.insight_schedule_tools",
    # mutation_registry
    "READ_ONLY_TOOLS": "src.tools.mutation_registry",
    "is_mutating_tool": "src.tools.mutation_registry",
    "register_read_only_tool": "src.tools.mutation_registry",
    # registry
    "get_all_tools": "src.tools.registry",
    "get_architect_tools": "src.tools.registry",
    "get_tools_for_agent": "src.tools.registry",
    # tariff_tools
    "get_tariff_rates": "src.tools.tariff_tools",
    "setup_electricity_tariffs": "src.tools.tariff_tools",
    "update_electricity_tariffs": "src.tools.tariff_tools",
    # specialist_tools
    "consult_behavioral_analyst": "src.tools.specialist_tools",
    "consult_dashboard_designer": "src.tools.specialist_tools",
    "consult_data_science_team": "src.tools.specialist_tools",
    "consult_diagnostic_analyst": "src.tools.specialist_tools",
    "consult_energy_analyst": "src.tools.specialist_tools",
    "get_specialist_tools": "src.tools.specialist_tools",
    "request_synthesis_review": "src.tools.specialist_tools",
    # web_search
    "get_web_search_tools": "src.tools.web_search",
    "web_search": "src.tools.web_search",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]

    if name in _EXPORTS:
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr

    raise AttributeError(f"module 'src.tools' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
    from src.tools.agent_tools import (
        analyze_energy,
        diagnose_issue,
        discover_entities,
        get_agent_tools,
        get_entity_history,
    )
    from src.tools.analysis_tools import (
        get_analysis_tools,
        run_custom_analysis,
    )
    from src.tools.approval_tools import (
        get_approval_tools,
        seek_approval,
    )
    from src.tools.automation_builder_tools import (
        check_entity_exists,
        find_similar_automations,
        get_automation_builder_tools,
        validate_automation_draft,
    )
    from src.tools.diagnostic_tools import (
        analyze_error_log,
        check_integration_health,
        diagnose_entity,
        find_unavailable_entities_tool,
        get_diagnostic_tools,
        validate_config,
    )
    from src.tools.ha_automation_tools import get_automation_config, list_automations
    from src.tools.ha_entity_tools import (
        control_entity,
        get_domain_summary,
        get_entity_state,
        list_entities_by_domain,
        search_entities,
    )
    from src.tools.ha_script_scene_tools import get_script_config
    from src.tools.ha_tools import get_ha_tools
    from src.tools.ha_utility_tools import check_ha_config, get_ha_logs, render_template
    from src.tools.insight_schedule_tools import (
        create_insight_schedule,
        get_insight_schedule_tools,
    )
    from src.tools.mutation_registry import (
        READ_ONLY_TOOLS,
        is_mutating_tool,
        register_read_only_tool,
    )
    from src.tools.registry import get_all_tools, get_architect_tools, get_tools_for_agent
    from src.tools.specialist_tools import (
        consult_behavioral_analyst,
        consult_dashboard_designer,
        consult_data_science_team,
        consult_diagnostic_analyst,
        consult_energy_analyst,
        get_specialist_tools,
        request_synthesis_review,
    )
    from src.tools.tariff_tools import (
        get_tariff_rates,
        setup_electricity_tariffs,
        update_electricity_tariffs,
    )
    from src.tools.web_search import get_web_search_tools, web_search

__all__ = [
    "READ_ONLY_TOOLS",
    "analyze_energy",
    "analyze_error_log",
    "check_entity_exists",
    "check_ha_config",
    "check_integration_health",
    "consult_behavioral_analyst",
    "consult_dashboard_designer",
    "consult_data_science_team",
    "consult_diagnostic_analyst",
    "consult_energy_analyst",
    "control_entity",
    "create_insight_schedule",
    "diagnose_entity",
    "diagnose_issue",
    "discover_entities",
    "find_similar_automations",
    "find_unavailable_entities_tool",
    "get_agent_tools",
    "get_all_tools",
    "get_analysis_tools",
    "get_approval_tools",
    "get_architect_tools",
    "get_automation_builder_tools",
    "get_automation_config",
    "get_diagnostic_tools",
    "get_domain_summary",
    "get_entity_history",
    "get_entity_state",
    "get_ha_logs",
    "get_ha_tools",
    "get_insight_schedule_tools",
    "get_script_config",
    "get_specialist_tools",
    "get_tariff_rates",
    "get_tools_for_agent",
    "get_web_search_tools",
    "is_mutating_tool",
    "list_automations",
    "list_entities_by_domain",
    "register_read_only_tool",
    "render_template",
    "request_synthesis_review",
    "run_custom_analysis",
    "search_entities",
    "seek_approval",
    "setup_electricity_tariffs",
    "update_electricity_tariffs",
    "validate_automation_draft",
    "validate_config",
    "web_search",
]
