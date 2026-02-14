"""Specialist routing: keyword-based selection and team analysis state."""

from __future__ import annotations

import re
from typing import Any

from src.graph.state import TeamAnalysis

SPECIALIST_TRIGGERS: dict[str, frozenset[str]] = {
    "energy": frozenset(
        {
            "energy",
            "power",
            "consumption",
            "solar",
            "battery",
            "batteries",
            "kwh",
            "cost",
            "costs",
            "watt",
            "watts",
            "grid",
            "peak",
            "tariff",
            "electricity",
        }
    ),
    "behavioral": frozenset(
        {
            "pattern",
            "patterns",
            "behavior",
            "behaviour",
            "routine",
            "routines",
            "habit",
            "habits",
            "automation",
            "automations",
            "scene",
            "scenes",
            "script",
            "scripts",
            "usage",
            "schedule",
            "schedules",
            "occupancy",
            "manual",
            "trigger",
            "triggers",
            "frequency",
            "gap",
            "gaps",
        }
    ),
    "diagnostic": frozenset(
        {
            "error",
            "errors",
            "unavailable",
            "broken",
            "offline",
            "health",
            "diagnose",
            "diagnosis",
            "troubleshoot",
            "fix",
            "issue",
            "issues",
            "problem",
            "problems",
            "integration",
            "integrations",
            "sensor",
            "sensors",
            "unreliable",
        }
    ),
}

_ALL_SPECIALISTS = ["energy", "behavioral", "diagnostic"]


def _select_specialists(
    query: str,
    specialists: list[str] | None = None,
) -> list[str]:
    """Choose which specialists to invoke.

    Resolution order:
    1. If *specialists* is provided, use exactly those (explicit override).
    2. Else tokenise *query* and match against ``SPECIALIST_TRIGGERS``.
    3. If nothing matches (ambiguous / empty), fall back to all three.

    Returns a sorted list of specialist keys (``"energy"``, ``"behavioral"``,
    ``"diagnostic"``).
    """
    if specialists:
        # Honour explicit override, filtering to valid keys
        valid = [s for s in specialists if s in SPECIALIST_TRIGGERS]
        return sorted(valid) if valid else sorted(_ALL_SPECIALISTS)

    tokens = set(re.findall(r"[a-z]+", query.lower()))
    matched: list[str] = []
    for domain, keywords in SPECIALIST_TRIGGERS.items():
        if tokens & keywords:
            matched.append(domain)

    return sorted(matched) if matched else sorted(_ALL_SPECIALISTS)


def _get_or_create_team_analysis(query: str) -> TeamAnalysis:
    """Get the current team analysis from the ExecutionContext, or create a new one.

    Uses the per-request ExecutionContext (contextvars) instead of a module-level
    global to ensure concurrent requests don't stomp on each other.
    """
    from src.agents.execution_context import get_execution_context

    ctx = get_execution_context()
    if ctx is not None and ctx.team_analysis is not None:
        return ctx.team_analysis  # type: ignore[no-any-return]

    from uuid import uuid4

    ta = TeamAnalysis(
        request_id=str(uuid4()),
        request_summary=query,
    )
    if ctx is not None:
        ctx.team_analysis = ta
    return ta


def _set_team_analysis(ta: TeamAnalysis | None) -> None:
    """Store the team analysis in the ExecutionContext."""
    from src.agents.execution_context import get_execution_context

    ctx = get_execution_context()
    if ctx is not None:
        ctx.team_analysis = ta


def reset_team_analysis() -> None:
    """Reset the team analysis for a new session."""
    _set_team_analysis(None)


def _format_findings(result: dict[str, Any]) -> str:
    """Format analysis results into a conversational summary."""
    insights = result.get("insights", [])
    if not insights:
        return "No significant findings from this analysis."

    parts = [f"Found {len(insights)} insight(s):"]
    for i, insight in enumerate(insights, 1):
        title = insight.get("title", "Untitled")
        desc = insight.get("description", "")
        parts.append(f"\n{i}. **{title}**: {desc}")

    return "\n".join(parts)
