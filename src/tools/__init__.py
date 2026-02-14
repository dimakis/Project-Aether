"""Tool registry for Home Assistant interactions and agent delegation.

All tool functions and registry accessors are re-exported here.
Canonical registry logic lives in tools/registry.py.
"""

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
from src.tools.registry import get_all_tools, get_architect_tools
from src.tools.specialist_tools import (
    consult_behavioral_analyst,
    consult_dashboard_designer,
    consult_data_science_team,
    consult_diagnostic_analyst,
    consult_energy_analyst,
    get_specialist_tools,
    request_synthesis_review,
)

__all__ = [
    # Agent Delegation Tools
    "analyze_energy",
    # Diagnostic Tools
    "analyze_error_log",
    "check_ha_config",
    "check_integration_health",
    "consult_behavioral_analyst",
    "consult_dashboard_designer",
    "consult_data_science_team",
    "consult_diagnostic_analyst",
    # Specialist Tools
    "consult_energy_analyst",
    "control_entity",
    # Insight Schedule Tools
    "create_insight_schedule",
    "diagnose_entity",
    "diagnose_issue",
    "discover_entities",
    "find_unavailable_entities_tool",
    "get_agent_tools",
    # Combined
    "get_all_tools",
    "get_analysis_tools",
    "get_approval_tools",
    "get_architect_tools",
    "get_automation_config",
    "get_diagnostic_tools",
    "get_domain_summary",
    "get_entity_history",
    # HA Tools
    "get_entity_state",
    "get_ha_logs",
    "get_ha_tools",
    "get_insight_schedule_tools",
    "get_script_config",
    "get_specialist_tools",
    "list_automations",
    "list_entities_by_domain",
    "render_template",
    "request_synthesis_review",
    # Custom Analysis Tools
    "run_custom_analysis",
    "search_entities",
    # Approval Tools
    "seek_approval",
    "validate_config",
]
