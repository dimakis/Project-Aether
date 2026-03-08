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
    "validate_automation_draft",
    "validate_config",
    "web_search",
]
