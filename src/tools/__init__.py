"""Tool registry for Home Assistant interactions and agent delegation."""

from src.tools.agent_tools import (
    analyze_energy,
    diagnose_issue,
    discover_entities,
    get_agent_tools,
    get_entity_history,
)
from src.tools.approval_tools import (
    get_approval_tools,
    seek_approval,
)
from src.tools.diagnostic_tools import (
    analyze_error_log,
    check_integration_health,
    diagnose_entity,
    find_unavailable_entities_tool,
    get_diagnostic_tools,
    validate_config,
)
from src.tools.ha_tools import (
    check_ha_config,
    control_entity,
    get_domain_summary,
    get_entity_state,
    get_ha_logs,
    get_ha_tools,
    list_entities_by_domain,
    search_entities,
)


def get_all_tools() -> list:
    """Return all tools available to the Architect agent.

    Combines HA tools (entity queries, control, diagnostics) with agent
    delegation tools (energy analysis, discovery, diagnostics),
    advanced diagnostic tools (log analysis, entity/integration health),
    and approval tools (seek_approval for HITL mutations).
    """
    return get_ha_tools() + get_agent_tools() + get_diagnostic_tools() + get_approval_tools()


__all__ = [
    # HA Tools
    "get_entity_state",
    "list_entities_by_domain",
    "search_entities",
    "get_domain_summary",
    "control_entity",
    "get_ha_logs",
    "check_ha_config",
    "get_ha_tools",
    # Agent Delegation Tools
    "analyze_energy",
    "discover_entities",
    "get_entity_history",
    "diagnose_issue",
    "get_agent_tools",
    # Diagnostic Tools
    "analyze_error_log",
    "find_unavailable_entities_tool",
    "diagnose_entity",
    "check_integration_health",
    "validate_config",
    "get_diagnostic_tools",
    # Approval Tools
    "seek_approval",
    "get_approval_tools",
    # Combined
    "get_all_tools",
]
