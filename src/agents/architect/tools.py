"""Tool loading and mutation classification for the Architect agent.

Mutation classification delegates to the centralized
``src.tools.mutation_registry`` module so that HITL enforcement is
consistent across all agents (Constitution Principle I: Safety).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.tools.mutation_registry import READ_ONLY_TOOLS, is_mutating_tool

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

__all__ = ["READ_ONLY_TOOLS", "get_ha_tools", "is_mutating_tool"]


def get_ha_tools() -> list[BaseTool]:
    """Get the curated Architect tool set (16 tools).

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
