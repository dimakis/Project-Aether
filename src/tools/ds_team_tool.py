"""Main DS team orchestrator tool: consult_data_science_team."""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.agents.execution_context import emit_delegation, emit_progress
from src.agents.synthesis import ProgrammaticSynthesizer
from src.tools.ds_team_runners import (
    _run_behavioral,
    _run_diagnostic,
    _run_energy,
)
from src.tools.ds_team_strategies import (
    _run_discussion_round,
    _run_parallel,
    _run_teamwork,
)
from src.tools.report_lifecycle import (
    complete_analysis_report,
    create_analysis_report,
    fail_analysis_report,
)
from src.tools.specialist_routing import (
    _select_specialists,
    _set_team_analysis,
    reset_team_analysis,
)
from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)


@tool("consult_data_science_team")
@trace_with_uri(name="agent.consult_data_science_team", span_type="TOOL")
async def consult_data_science_team(
    query: str,
    hours: int = 24,
    entity_ids: list[str] | None = None,
    specialists: list[str] | None = None,
    custom_query: str | None = None,
    depth: str = "standard",
    strategy: str = "parallel",
) -> str:
    """Consult the DS team for analysis, diagnostics, or optimization.

    Args:
        query: What to analyze
        hours: Hours of history (default 24, max 168)
        entity_ids: Entity IDs to focus on (optional)
        specialists: Override routing: "energy", "behavioral", "diagnostic"
        custom_query: Free-form analysis prompt for ad-hoc investigations
        depth: "quick", "standard", or "deep"
        strategy: "parallel" (fast) or "teamwork" (sequential cross-consult)
    """
    hours = min(max(hours, 1), 168)
    effective_query = custom_query or query

    # Emit delegation: architect -> DS team
    emit_delegation("architect", "data_science_team", effective_query)
    emit_progress(
        "agent_start",
        "data_science_team",
        f"Data Science Team started (depth={depth}, strategy={strategy})",
    )

    # 1. Smart routing
    selected = _select_specialists(effective_query, specialists)
    logger.info(
        "DS team routing: query=%r  selected=%s  explicit=%s  depth=%s  strategy=%s",
        effective_query[:80],
        selected,
        specialists is not None,
        depth,
        strategy,
    )

    # 2. Reset shared state for a fresh analysis session
    reset_team_analysis()

    # --- Report lifecycle: create a RUNNING report if DB session available ---
    from src.agents.execution_context import get_execution_context as _get_ctx

    _ctx = _get_ctx()
    report_obj = None
    session_factory = _ctx.session_factory if _ctx else None
    if session_factory:
        try:
            async with session_factory() as _session:
                report_obj = await create_analysis_report(
                    session=_session,
                    title=effective_query[:200],
                    analysis_type="team_analysis",
                    depth=depth,
                    strategy=strategy,
                    conversation_id=_ctx.conversation_id if _ctx else None,
                )
        except Exception as e:
            logger.warning("Failed to create analysis report: %s", e)

    # 3. Run selected specialists using the chosen strategy
    specialist_runners = {
        "energy": _run_energy,
        "behavioral": _run_behavioral,
        "diagnostic": _run_diagnostic,
    }

    try:
        if strategy == "teamwork":
            # Teamwork: run specialists sequentially, sharing findings
            results = await _run_teamwork(
                selected, specialist_runners, effective_query, hours, entity_ids, depth
            )
        else:
            # Parallel: run all specialists simultaneously (current behavior)
            results = await _run_parallel(
                selected, specialist_runners, effective_query, hours, entity_ids, depth
            )

        # 4. Auto-synthesise if 2+ specialists contributed findings
        _ctx = _get_ctx()
        ta = _ctx.team_analysis if _ctx else None
        if ta and len(ta.findings) > 0 and len(selected) >= 2:
            try:
                synth = ProgrammaticSynthesizer()
                ta = synth.synthesize(ta)
                _set_team_analysis(ta)
            except Exception as e:
                logger.warning("Programmatic synthesis failed: %s", e)

        # 4b. Adaptive escalation: if conflicts detected in parallel mode,
        #     run a discussion round to resolve them (cap: 1 escalation).
        #     Feature 33: B2 — adaptive strategy escalation.
        _ctx = _get_ctx()
        ta = _ctx.team_analysis if _ctx else None
        if strategy == "parallel" and depth != "quick" and ta and ta.conflicts:
            from src.agents.execution_context import emit_communication as _emit_comm

            _emit_comm(
                from_agent="data_science_team",
                to_agent="team",
                message_type="status",
                content=(
                    f"Conflicts detected ({len(ta.conflicts)}), "
                    "escalating to teamwork discussion for resolution"
                ),
                metadata={"conflicts": ta.conflicts},
            )
            emit_progress(
                "status",
                "data_science_team",
                "Escalating to discussion round due to conflicts",
            )
            try:
                disc_entries = await _run_discussion_round(selected, ta)
                if disc_entries:
                    results.append(
                        f"\n**Escalation Discussion:** {len(disc_entries)} "
                        f"discussion message(s) to resolve conflicts"
                    )
            except Exception as e:
                logger.warning("Escalation discussion failed: %s", e)

        # 5. Format unified response
        parts = [
            f"**Data Science Team Report** "
            f"({len(selected)} specialist(s), {hours}h window, "
            f"depth={depth}, strategy={strategy})\n"
        ]
        parts.extend(results)

        if ta and ta.consensus:
            parts.append(f"\n**Team Consensus:** {ta.consensus}")
        if ta and ta.conflicts:
            parts.append("\n**Conflicts:**")
            for c in ta.conflicts:
                parts.append(f"- {c}")
        if ta and ta.holistic_recommendations:
            parts.append("\n**Recommendations:**")
            for i, r in enumerate(ta.holistic_recommendations, 1):
                parts.append(f"{i}. {r}")

        report = "\n".join(parts)

        # --- Report lifecycle: complete the report ---
        if report_obj and session_factory:
            try:
                _ctx = _get_ctx()
                comm_log = _ctx.communication_log if _ctx else []
                async with session_factory() as _session:
                    await complete_analysis_report(
                        session=_session,
                        report_id=str(report_obj.id),
                        summary=report[:2000],
                        communication_log=comm_log,
                    )
            except Exception as e:
                logger.warning("Failed to complete analysis report: %s", e)

        # Emit delegation: DS team -> architect with the synthesized report
        report_summary = report[:300] + ("..." if len(report) > 300 else "")
        emit_delegation("data_science_team", "architect", report_summary)
        emit_progress("agent_end", "data_science_team", "Data Science Team completed")

        return report

    except Exception as exc:
        # --- Report lifecycle: fail the report ---
        if report_obj and session_factory:
            try:
                async with session_factory() as _session:
                    await fail_analysis_report(
                        session=_session,
                        report_id=str(report_obj.id),
                        summary=str(exc)[:500],
                    )
            except Exception as e:
                logger.warning("Failed to mark analysis report as failed: %s", e)

        emit_progress("agent_end", "data_science_team", "Data Science Team failed")
        logger.error("DS team analysis failed: %s", exc, exc_info=True)
        return f"Data Science Team analysis failed: {exc}"
