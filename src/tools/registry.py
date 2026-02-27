"""Tool registry for assembling tool sets per agent role.

Canonical location for get_all_tools(), get_architect_tools(), and
get_tools_for_agent().  Re-exported from src.tools.__init__ for
backward compatibility.
"""

from __future__ import annotations

import logging
from typing import Any

from src.tools.agent_tools import (
    get_agent_tools,
)
from src.tools.analysis_tools import (
    get_analysis_tools,
)
from src.tools.approval_tools import (
    get_approval_tools,
)
from src.tools.diagnostic_tools import (
    get_diagnostic_tools,
)
from src.tools.ha_automation_tools import list_automations
from src.tools.ha_tools import get_ha_tools
from src.tools.ha_utility_tools import render_template
from src.tools.insight_schedule_tools import (
    get_insight_schedule_tools,
)
from src.tools.specialist_tools import (
    get_specialist_tools,
)

logger = logging.getLogger(__name__)


def get_all_tools() -> list[Any]:
    """Return every registered tool (superset for backward compat / testing).

    Combines HA tools (entity queries, control, diagnostics) with agent
    delegation tools (energy analysis, discovery, diagnostics),
    advanced diagnostic tools (log analysis, entity/integration health),
    approval tools (seek_approval for HITL mutations),
    insight schedule tools (create/manage recurring analysis),
    custom analysis tools (free-form DS Team queries),
    and specialist tools (individual + team delegation).
    """
    from src.tools.review_tools import review_config as _review_config
    from src.tools.web_search import get_web_search_tools

    return (
        get_ha_tools()
        + get_agent_tools()
        + get_diagnostic_tools()
        + get_approval_tools()
        + get_insight_schedule_tools()
        + get_analysis_tools()
        + get_specialist_tools()
        + get_web_search_tools()
        + [_review_config]
    )


_cached_architect_tools: list[Any] | None = None


def get_architect_tools() -> list[Any]:
    """Curated tool set for the Architect agent (lean router, 16 tools).

    The Architect is a conversationalist and router.  It does NOT directly
    execute analysis, diagnostics, or mutations.  Instead:

    - Analysis/insights -> ``consult_data_science_team`` (smart routing)
    - Dashboards -> ``consult_dashboard_designer`` (Lovelace design)
    - Mutations -> ``seek_approval`` -> Developer agent executes on approval
    - Diagnostics -> routed through the DS team's Diagnostic Analyst
    - Config reading -> ``get_automation_config`` / ``get_script_config``
      for full YAML from the discovery DB

    This keeps the LLM tool surface small and focused.

    The result is cached at module level -- the tool list is static and
    identical across requests, so building it once avoids repeated import
    and list construction overhead.
    """
    global _cached_architect_tools
    if _cached_architect_tools is not None:
        return _cached_architect_tools

    from src.tools.agent_tools import discover_entities as _discover_entities
    from src.tools.approval_tools import seek_approval as _seek_approval
    from src.tools.ds_team_tool import (
        consult_data_science_team as _consult_ds_team,
    )
    from src.tools.ha_automation_tools import (
        get_automation_config as _get_automation_config,
    )
    from src.tools.ha_entity_tools import (
        get_domain_summary as _get_domain_summary,
    )
    from src.tools.ha_entity_tools import (
        get_entity_state as _get_entity_state,
    )
    from src.tools.ha_entity_tools import (
        list_entities_by_domain as _list_entities_by_domain,
    )
    from src.tools.ha_entity_tools import (
        search_entities as _search_entities,
    )
    from src.tools.ha_script_scene_tools import get_script_config as _get_script_config
    from src.tools.ha_utility_tools import (
        check_ha_config as _check_ha_config,
    )
    from src.tools.ha_utility_tools import (
        get_ha_logs as _get_ha_logs,
    )
    from src.tools.insight_schedule_tools import (
        create_insight_schedule as _create_insight_schedule,
    )
    from src.tools.review_tools import review_config as _review_config
    from src.tools.specialist_consult_tools import (
        consult_dashboard_designer as _consult_dashboard,
    )

    _cached_architect_tools = [
        # HA query -- DB-backed (7)
        _get_entity_state,
        _list_entities_by_domain,
        _search_entities,
        _get_domain_summary,
        list_automations,
        _get_automation_config,
        _get_script_config,
        # HA query -- live (3)
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
        # Config review (1)
        _review_config,
    ]
    return _cached_architect_tools


def _build_tool_name_map() -> dict[str, Any]:
    """Build a name -> tool object mapping from the full tool set.

    Lazily imports and caches the mapping.  Used by
    ``get_tools_for_agent`` to resolve ``tools_enabled`` lists.
    """
    return {getattr(t, "name", ""): t for t in get_all_tools() if getattr(t, "name", "")}


_cached_tool_name_map: dict[str, Any] | None = None


def get_tools_for_agent(
    agent_name: str,
    tools_enabled: list[str] | None = None,
) -> list[Any]:
    """Resolve the tool set for an agent using its ``tools_enabled`` config.

    Resolution order:
        1. If ``tools_enabled`` is provided and non-empty, filter the
           full tool catalogue to exactly those tools.
        2. If agent_name == ``"architect"``, use the curated Architect set.
        3. Otherwise return an empty list (pure-LLM agent).

    Args:
        agent_name: Agent identifier (e.g. ``"architect"``, ``"research"``).
        tools_enabled: Explicit list of tool names from AgentConfigVersion.

    Returns:
        List of tool objects the agent should be bound to.
    """
    global _cached_tool_name_map

    if tools_enabled:
        if _cached_tool_name_map is None:
            _cached_tool_name_map = _build_tool_name_map()

        resolved = [
            _cached_tool_name_map[name] for name in tools_enabled if name in _cached_tool_name_map
        ]
        missing = set(tools_enabled) - set(_cached_tool_name_map.keys())
        if missing:
            logger.warning("tools_enabled references unknown tools for %s: %s", agent_name, missing)
        return resolved

    if agent_name == "architect":
        return get_architect_tools()

    return []
