"""DS team execution strategies: parallel, teamwork, discussion round."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from src.agents.execution_context import emit_delegation, emit_progress

if TYPE_CHECKING:
    from src.graph.state import TeamAnalysis

logger = logging.getLogger(__name__)


async def _run_parallel(
    selected: list[str],
    runners: dict[str, Any],
    query: str,
    hours: int,
    entity_ids: list[str] | None,
    depth: str,
) -> list[str]:
    """Run specialists in parallel (current behavior).

    All selected specialists start simultaneously via asyncio.gather.
    """
    tasks: list[tuple[str, asyncio.Task[str]]] = []
    for name in selected:
        runner = runners.get(name)
        if runner:
            task = asyncio.create_task(runner(query, hours, entity_ids, depth=depth))
            tasks.append((name, task))

    raw_results = await asyncio.gather(*(t for _, t in tasks), return_exceptions=True)

    results: list[str] = []
    for (name, _task), raw in zip(tasks, raw_results, strict=False):
        if isinstance(raw, BaseException):
            logger.error("Specialist %s failed: %s", name, raw, exc_info=raw)
            result = f"{name.title()} analysis failed: {raw}"
        else:
            result = raw
        results.append(f"**{name.title()} Analyst:** {result}")
        analyst_agent = f"{name}_analyst"
        summary = result[:200] + ("..." if len(result) > 200 else "")
        emit_delegation(analyst_agent, "data_science_team", summary)

    return results


async def _run_teamwork(
    selected: list[str],
    runners: dict[str, Any],
    query: str,
    hours: int,
    entity_ids: list[str] | None,
    depth: str,
) -> list[str]:
    """Run specialists sequentially with cross-consultation (teamwork mode).

    Each specialist completes before the next starts.  Shared TeamAnalysis
    is updated between runs so later specialists can see earlier findings.
    After all specialists complete, a discussion round is run if there are
    findings to discuss.

    Feature 33: DS Deep Analysis — teamwork execution strategy.
    """
    results: list[str] = []

    # Priority order for sequential execution
    priority_order = ["energy", "behavioral", "diagnostic"]
    ordered = [name for name in priority_order if name in selected]
    # Add any remaining specialists not in priority list
    ordered.extend(name for name in selected if name not in ordered)

    for name in ordered:
        runner = runners.get(name)
        if not runner:
            continue

        emit_progress(
            "status",
            "data_science_team",
            f"Teamwork: running {name} analyst (sequential)",
        )

        try:
            result = await runner(query, hours, entity_ids, depth=depth)
        except Exception as e:
            logger.error("Specialist %s failed: %s", name, e, exc_info=e)
            result = f"{name.title()} analysis failed: {e}"

        results.append(f"**{name.title()} Analyst:** {result}")

        # Emit delegation after each specialist completes
        analyst_agent = f"{name}_analyst"
        summary = result[:200] + ("..." if len(result) > 200 else "")
        emit_delegation(analyst_agent, "data_science_team", summary)

    # Discussion round: let specialists review each other's findings
    from src.agents.execution_context import get_execution_context as _get_ctx

    _ctx = _get_ctx()
    ta = _ctx.team_analysis if _ctx else None
    if ta and ta.findings:
        discussion_entries = await _run_discussion_round(selected, ta)
        if discussion_entries:
            results.append(
                f"\n**Discussion Round:** {len(discussion_entries)} discussion message(s) exchanged"
            )

    return results


async def _run_discussion_round(
    selected: list[str],
    ta: TeamAnalysis,
) -> list[Any]:
    """Run a single discussion round after all specialists have completed.

    Each specialist reviews the combined findings and provides cross-references,
    agreements, and disagreements.  Capped at 1 round to bound cost.

    Feature 33: DS Deep Analysis — B1 discussion round.

    Args:
        selected: List of specialist names that participated.
        ta: TeamAnalysis with accumulated findings.

    Returns:
        List of CommunicationEntry objects from the discussion.
    """
    # Build a textual summary of all findings
    findings_parts = []
    for finding in ta.findings:
        findings_parts.append(
            f"[{finding.specialist}] ({finding.finding_type}) "
            f"{finding.title}: {finding.description}"
        )
    findings_summary = "\n".join(findings_parts)

    if not findings_summary.strip():
        return []

    emit_progress(
        "status",
        "data_science_team",
        f"Discussion round: {len(selected)} specialist(s) reviewing findings",
    )

    # Instantiate analysts for discussion
    analyst_classes: dict[str, type] = {}
    try:
        from src.agents.energy_analyst import EnergyAnalyst

        analyst_classes["energy"] = EnergyAnalyst
    except ImportError:
        pass
    try:
        from src.agents.behavioral_analyst import BehavioralAnalyst

        analyst_classes["behavioral"] = BehavioralAnalyst
    except ImportError:
        pass
    try:
        from src.agents.diagnostic_analyst import DiagnosticAnalyst

        analyst_classes["diagnostic"] = DiagnosticAnalyst
    except ImportError:
        pass

    all_entries: list[Any] = []
    for name in selected:
        cls = analyst_classes.get(name)
        if cls is None:
            continue

        try:
            analyst = cls()
            entries = await analyst.discuss(findings_summary)
            all_entries.extend(entries)
        except Exception as e:
            logger.warning("Discussion round failed for %s: %s", name, e)

    return all_entries
