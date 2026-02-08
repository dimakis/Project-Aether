"""Tool registry for Home Assistant interactions and agent delegation."""

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
    get_automation_config,
    get_domain_summary,
    get_entity_state,
    get_ha_logs,
    get_ha_tools,
    get_script_config,
    list_entities_by_domain,
    search_entities,
)
from src.tools.insight_schedule_tools import (
    create_insight_schedule,
    get_insight_schedule_tools,
)
from src.tools.specialist_tools import (
    consult_behavioral_analyst,
    consult_dashboard_designer,
    consult_data_science_team,
    consult_diagnostic_analyst,
    consult_energy_analyst,
    get_specialist_tools,
    request_synthesis_review,
)


def get_all_tools() -> list:
    """Return every registered tool (superset for backward compat / testing).

    Combines HA tools (entity queries, control, diagnostics) with agent
    delegation tools (energy analysis, discovery, diagnostics),
    advanced diagnostic tools (log analysis, entity/integration health),
    approval tools (seek_approval for HITL mutations),
    insight schedule tools (create/manage recurring analysis),
    custom analysis tools (free-form DS Team queries),
    and specialist tools (individual + team delegation).
    """
    return (
        get_ha_tools()
        + get_agent_tools()
        + get_diagnostic_tools()
        + get_approval_tools()
        + get_insight_schedule_tools()
        + get_analysis_tools()
        + get_specialist_tools()
    )


def get_architect_tools() -> list:
    """Curated tool set for the Architect agent (lean router, 15 tools).

    The Architect is a conversationalist and router.  It does NOT directly
    execute analysis, diagnostics, or mutations.  Instead:

    - Analysis/insights → ``consult_data_science_team`` (smart routing)
    - Dashboards → ``consult_dashboard_designer`` (Lovelace design)
    - Mutations → ``seek_approval`` → Developer agent executes on approval
    - Diagnostics → routed through the DS team's Diagnostic Analyst
    - Config reading → ``get_automation_config`` / ``get_script_config``
      for full YAML from the discovery DB

    This keeps the LLM tool surface small and focused.
    """
    from src.tools.ha_tools import (
        check_ha_config as _check_ha_config,
        get_automation_config as _get_automation_config,
        get_domain_summary as _get_domain_summary,
        get_entity_state as _get_entity_state,
        get_ha_logs as _get_ha_logs,
        get_script_config as _get_script_config,
        list_automations,
        list_entities_by_domain as _list_entities_by_domain,
        render_template,
        search_entities as _search_entities,
    )
    from src.tools.approval_tools import seek_approval as _seek_approval
    from src.tools.insight_schedule_tools import (
        create_insight_schedule as _create_insight_schedule,
    )
    from src.tools.agent_tools import discover_entities as _discover_entities
    from src.tools.specialist_tools import (
        consult_dashboard_designer as _consult_dashboard,
        consult_data_science_team as _consult_ds_team,
    )

    return [
        # HA query — DB-backed (7)
        _get_entity_state,
        _list_entities_by_domain,
        _search_entities,
        _get_domain_summary,
        list_automations,
        _get_automation_config,
        _get_script_config,
        # HA query — live (3)
        render_template,
        _get_ha_logs,
        _check_ha_config,
        # Approval (1)
        _seek_approval,
        # Scheduling (1)
        _create_insight_schedule,
        # Discovery (1)
        _discover_entities,
        # DS Team (1)
        _consult_ds_team,
        # Dashboard (1)
        _consult_dashboard,
    ]


__all__ = [
    # HA Tools
    "get_entity_state",
    "list_entities_by_domain",
    "search_entities",
    "get_domain_summary",
    "get_automation_config",
    "get_script_config",
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
    # Insight Schedule Tools
    "create_insight_schedule",
    "get_insight_schedule_tools",
    # Custom Analysis Tools
    "run_custom_analysis",
    "get_analysis_tools",
    # Specialist Tools
    "consult_energy_analyst",
    "consult_behavioral_analyst",
    "consult_diagnostic_analyst",
    "consult_dashboard_designer",
    "consult_data_science_team",
    "request_synthesis_review",
    "get_specialist_tools",
    # Combined
    "get_all_tools",
    "get_architect_tools",
]
