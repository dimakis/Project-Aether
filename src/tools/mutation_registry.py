"""Centralized mutation classification for HITL enforcement.

Provides a single source of truth for which tools can mutate Home
Assistant state and therefore require human-in-the-loop approval.

Constitution Principle I (Safety): all mutating actions require
human approval before execution.  This module ensures that ANY
agent — not just the Architect — routes mutating tool calls through
the approval gate.

The registry uses a **fail-safe whitelist** approach: only tools
explicitly listed in READ_ONLY_TOOLS are allowed to execute without
approval.  Any unlisted tool is treated as mutating.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        # HA query -- DB-backed (7)
        "get_entity_state",
        "list_entities_by_domain",
        "search_entities",
        "get_domain_summary",
        "list_automations",
        "get_automation_config",
        "get_script_config",
        # HA query -- live (3)
        "render_template",
        "get_ha_logs",
        "check_ha_config",
        # Discovery (1)
        "discover_entities",
        # Specialist delegation (2) -- read-only analysis
        "consult_data_science_team",
        "consult_dashboard_designer",
        # Scheduling (1) -- creates config, no HA mutation
        "create_insight_schedule",
        # Approval (1) -- creating proposals IS the approval mechanism
        "seek_approval",
        # Review (1) -- creates review proposals for HITL approval
        "review_config",
        # Web search (1) -- external read-only query
        "web_search",
    }
)


def is_mutating_tool(tool_name: str) -> bool:
    """Check if a tool call can mutate Home Assistant state.

    Uses a whitelist of known read-only tools.  Any tool not in the
    whitelist is treated as mutating and requires HITL approval.
    This fail-safe approach ensures newly registered tools default
    to requiring approval rather than silently bypassing it.
    """
    return tool_name not in READ_ONLY_TOOLS


def register_read_only_tool(tool_name: str) -> None:
    """Register an additional tool as read-only at runtime.

    Intended for dynamically added tools (e.g., from plugins or
    dynamic agent composition) that are provably read-only.  Must
    be called during startup or agent configuration, not per-request.
    """
    global READ_ONLY_TOOLS
    READ_ONLY_TOOLS = READ_ONLY_TOOLS | frozenset({tool_name})
    logger.info("Registered read-only tool: %s", tool_name)


# ---------------------------------------------------------------------------
# DB-backed read-only set with TTL cache (Feature 34)
# ---------------------------------------------------------------------------

_cached_db_read_only: frozenset[str] | None = None
_cached_db_read_only_at: float = 0.0
_DB_CACHE_TTL = 60.0


async def build_read_only_set_from_db() -> frozenset[str]:
    """Load the read-only tool set from DB-backed tool groups.

    Results are cached for ``_DB_CACHE_TTL`` seconds.  On any DB
    failure the hardcoded ``READ_ONLY_TOOLS`` set is returned as a
    safe fallback.
    """
    global _cached_db_read_only, _cached_db_read_only_at

    now = time.monotonic()
    if _cached_db_read_only is not None and (now - _cached_db_read_only_at) < _DB_CACHE_TTL:
        return _cached_db_read_only

    try:
        from src.dal.tool_groups import ToolGroupRepository
        from src.storage import get_session

        async with get_session() as session:
            groups = await ToolGroupRepository(session).list_all()

        read_only: set[str] = set()
        for group in groups:
            if group.is_read_only:
                read_only.update(group.tool_names or [])

        result = frozenset(read_only)
        _cached_db_read_only = result
        _cached_db_read_only_at = now
        return result
    except Exception:
        logger.warning("Failed to load read-only tools from DB, using hardcoded fallback")
        return READ_ONLY_TOOLS


async def is_mutating_tool_async(tool_name: str) -> bool:
    """Async mutation check using the DB-backed read-only set.

    Falls back to the hardcoded ``READ_ONLY_TOOLS`` if the DB is
    unavailable (handled inside ``build_read_only_set_from_db``).
    """
    read_only = await build_read_only_set_from_db()
    return tool_name not in read_only
