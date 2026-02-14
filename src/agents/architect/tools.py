"""Tool loading and mutation classification for the Architect agent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


def get_ha_tools() -> list[BaseTool]:
    """Get the curated Architect tool set (12 tools).

    The Architect is a lean router -- it delegates analysis to the
    DS team via ``consult_data_science_team`` and mutations via
    ``seek_approval``.  Mutation tools and individual specialist
    tools are NOT bound here.
    """
    try:
        from src.tools import get_architect_tools

        return get_architect_tools()
    except Exception:
        logger.error(
            "Failed to load tools -- agent will operate without tools. "
            "This may affect HITL enforcement.",
            exc_info=True,
        )
        return []


# Read-only tools that can execute without HITL approval.
# Every tool in get_architect_tools() is read-only except seek_approval,
# which is the approval mechanism itself (creating proposals, not mutations).
READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        # HA query tools (10)
        "get_entity_state",
        "list_entities_by_domain",
        "search_entities",
        "get_domain_summary",
        "list_automations",
        "get_automation_config",
        "get_script_config",
        "render_template",
        "get_ha_logs",
        "check_ha_config",
        # Discovery (1)
        "discover_entities",
        # Specialist delegation (2) — read-only analysis
        "consult_data_science_team",
        "consult_dashboard_designer",
        # Scheduling (1) — creates config, no HA mutation
        "create_insight_schedule",
        # Approval (1) — creating proposals IS the approval mechanism
        "seek_approval",
        # Review (1) — creates review proposals for HITL approval
        "review_config",
    }
)


def is_mutating_tool(tool_name: str) -> bool:
    """Check if a tool call can mutate Home Assistant state.

    Uses a whitelist of known read-only tools. Any tool not in the
    whitelist is treated as mutating and requires HITL approval.
    This fail-safe approach ensures newly registered tools default
    to requiring approval rather than silently bypassing it.
    """
    return tool_name not in READ_ONLY_TOOLS
