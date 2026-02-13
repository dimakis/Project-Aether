"""Specialist delegation tools for the Architect.

These tools allow the Architect to delegate analysis tasks to the
DS team specialists (Energy, Behavioral, Diagnostic) and request
LLM synthesis reviews for complex/conflicting findings.

The Architect calls these tools during conversation to gather
specialist insights, which are accumulated in a TeamAnalysis object
for cross-consultation and synthesis.

The primary entry point is ``consult_data_science_team`` which acts
as a programmatic "Head DS" — it selects the right specialists based
on query keywords (or an explicit override), runs them with shared
TeamAnalysis, and auto-synthesises a unified response.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from langchain_core.tools import tool

from src.agents.behavioral_analyst import BehavioralAnalyst
from src.agents.config_cache import is_agent_enabled
from src.agents.diagnostic_analyst import DiagnosticAnalyst
from src.agents.energy_analyst import EnergyAnalyst
from src.agents.execution_context import emit_delegation, emit_progress
from src.agents.model_context import get_model_context, model_context
from src.agents.synthesis import LLMSynthesizer, ProgrammaticSynthesizer
from src.graph.state import AnalysisState, AnalysisType, TeamAnalysis
from src.tools.report_lifecycle import (
    complete_analysis_report,
    create_analysis_report,
    fail_analysis_report,
)
from src.tracing import get_active_span, trace_with_uri

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Smart routing — keyword-based specialist selection
# ---------------------------------------------------------------------------

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


@tool("consult_energy_analyst")
@trace_with_uri(name="agent.consult_energy_analyst", span_type="TOOL")
async def consult_energy_analyst(
    query: str = "Analyze energy patterns",
    hours: int = 24,
    entity_ids: list[str] | None = None,
) -> str:
    """Consult the Energy Analyst for energy consumption insights.

    Use when the user asks about:
    - Energy usage, consumption patterns, or costs
    - Power optimization or savings opportunities
    - Unusual energy spikes or anomalies
    - Peak usage times and trends

    The Energy Analyst will analyze HA energy sensor data and return
    findings that can be cross-referenced by other specialists.

    Args:
        query: What to analyze (e.g., "Why is energy high overnight?")
        hours: Hours of history to analyze (default: 24, max: 168)
        entity_ids: Specific energy sensors (auto-discovers if empty)

    Returns:
        Summary of energy findings
    """
    if not await is_agent_enabled("energy_analyst"):
        return "Energy Analyst is currently disabled. Enable it on the Agents page to use."
    try:
        analyst = EnergyAnalyst()
        hours = min(max(hours, 1), 168)

        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
        )

        result = await analyst.invoke(state)

        # Update shared team analysis
        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])

        return _format_findings(result)

    except Exception as e:
        logger.error(f"Energy analysis failed: {e}", exc_info=True)
        return f"Energy analysis failed: {e}"


@tool("consult_behavioral_analyst")
@trace_with_uri(name="agent.consult_behavioral_analyst", span_type="TOOL")
async def consult_behavioral_analyst(
    query: str = "Analyze user behavior patterns",
    analysis_type: str = "behavior_analysis",
    hours: int = 168,
    entity_ids: list[str] | None = None,
) -> str:
    """Consult the Behavioral Analyst for user interaction patterns.

    Use when the user asks about:
    - How they use their home (manual actions, button presses)
    - Automation effectiveness and override rates
    - Patterns that could be automated (automation gaps)
    - Script and scene usage frequency
    - Whether actions are automation-triggered or human-triggered

    Args:
        query: What to analyze
        analysis_type: One of: behavior_analysis, automation_analysis,
            automation_gap_detection, correlation_discovery, device_health
        hours: Hours of history (default: 168 = 7 days for behavioral)
        entity_ids: Specific entities to focus on

    Returns:
        Summary of behavioral findings
    """
    if not await is_agent_enabled("behavioral_analyst"):
        return "Behavioral Analyst is currently disabled. Enable it on the Agents page to use."
    try:
        analyst = BehavioralAnalyst()
        hours = min(max(hours, 1), 168)

        type_map = {
            "behavior_analysis": AnalysisType.BEHAVIOR_ANALYSIS,
            "automation_analysis": AnalysisType.AUTOMATION_ANALYSIS,
            "automation_gap_detection": AnalysisType.AUTOMATION_GAP_DETECTION,
            "correlation_discovery": AnalysisType.CORRELATION_DISCOVERY,
            "device_health": AnalysisType.DEVICE_HEALTH,
        }
        a_type = type_map.get(analysis_type, AnalysisType.BEHAVIOR_ANALYSIS)

        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=a_type,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
        )

        result = await analyst.invoke(state)

        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])

        return _format_findings(result)

    except Exception as e:
        logger.error(f"Behavioral analysis failed: {e}", exc_info=True)
        return f"Behavioral analysis failed: {e}"


@tool("consult_diagnostic_analyst")
@trace_with_uri(name="agent.consult_diagnostic_analyst", span_type="TOOL")
async def consult_diagnostic_analyst(
    query: str = "Check system health",
    entity_ids: list[str] | None = None,
    diagnostic_context: str | None = None,
    hours: int = 24,
) -> str:
    """Consult the Diagnostic Analyst for system health analysis.

    Use when the user asks about:
    - Entity or sensor problems (offline, unavailable, drifting)
    - Integration health issues
    - Error log analysis
    - Configuration problems
    - Troubleshooting specific devices

    Args:
        query: What to diagnose
        entity_ids: Specific entities to investigate
        diagnostic_context: Additional context about the issue
        hours: Hours of history for analysis

    Returns:
        Summary of diagnostic findings
    """
    if not await is_agent_enabled("diagnostic_analyst"):
        return "Diagnostic Analyst is currently disabled. Enable it on the Agents page to use."
    try:
        analyst = DiagnosticAnalyst()
        hours = min(max(hours, 1), 168)

        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            diagnostic_context=diagnostic_context,
            team_analysis=ta,
        )

        result = await analyst.invoke(state)

        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])

        return _format_findings(result)

    except Exception as e:
        logger.error(f"Diagnostic analysis failed: {e}", exc_info=True)
        return f"Diagnostic analysis failed: {e}"


@tool("request_synthesis_review")
@trace_with_uri(name="agent.request_synthesis_review", span_type="TOOL")
async def request_synthesis_review(
    reason: str = "Conflicting findings need deeper analysis",
) -> str:
    """Request an LLM-powered synthesis review of specialist findings.

    Use when the programmatic synthesis has:
    - Unresolved conflicts between specialists
    - Ambiguous findings that need reasoning
    - Complex trade-offs that need narrative explanation

    The LLM synthesizer re-analyzes all accumulated specialist findings
    and provides a deeper, more nuanced synthesis.

    Args:
        reason: Why you're requesting a second opinion

    Returns:
        Enhanced synthesis with narrative conflict resolution
    """
    try:
        from src.agents.execution_context import get_execution_context

        ctx = get_execution_context()
        ta = ctx.team_analysis if ctx else None
        if ta is None or not ta.findings:
            return "No specialist findings to synthesize. Consult specialists first."

        from src.llm import get_llm

        llm = get_llm()
        synth = LLMSynthesizer(llm=llm)
        result = await synth.synthesize(ta)

        # Update shared state
        _set_team_analysis(result)

        parts = [f"**LLM Synthesis** (reason: {reason})\n"]
        if result.consensus:
            parts.append(f"**Consensus:** {result.consensus}\n")
        if result.conflicts:
            parts.append("**Conflicts:**")
            for c in result.conflicts:
                parts.append(f"- {c}")
        if result.holistic_recommendations:
            parts.append("\n**Recommendations:**")
            for i, r in enumerate(result.holistic_recommendations, 1):
                parts.append(f"{i}. {r}")

        return "\n".join(parts)

    except Exception as e:
        logger.error(f"Synthesis review failed: {e}", exc_info=True)
        return f"Synthesis review failed: {e}"


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
    """Consult the Data Science team for analysis, insights, and diagnostics.

    This is the primary tool for ANY data analysis, pattern detection,
    energy optimization, behavioral analysis, troubleshooting, or custom
    investigation.  The team automatically selects the right specialist(s)
    based on your query, runs their analyses with shared cross-consultation,
    and returns a synthesised unified response.

    Args:
        query: What to analyze (e.g., "Why is energy high overnight?",
            "Check system health", "Find automation opportunities")
        hours: Hours of historical data to analyze (default: 24, max: 168)
        entity_ids: Specific entity IDs to focus on (auto-discovers if empty)
        specialists: Override auto-routing.  Valid values: "energy",
            "behavioral", "diagnostic".  If omitted the team decides
            based on query keywords.
        custom_query: Free-form analysis prompt for ad-hoc investigations
            (e.g., "Check if HVAC is short-cycling").  When provided,
            the most relevant specialist will run a custom script.
        depth: Analysis depth — "quick" (fast summary), "standard" (default),
            or "deep" (comprehensive EDA with charts and statistical tests).
        strategy: Execution strategy — "parallel" (fast, all specialists
            run simultaneously) or "teamwork" (sequential with
            cross-consultation between specialists for deeper analysis).

    Returns:
        A unified, synthesised summary of all specialist findings
        including cross-referenced insights and recommendations.
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
) -> list:
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

    all_entries: list = []
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


# ---------------------------------------------------------------------------
# Internal runners (thin wrappers around the consult_* functions' logic)
# ---------------------------------------------------------------------------


def _capture_parent_span_context() -> tuple[str | None, float | None, str | None]:
    """Capture current model context + active span ID for trace propagation.

    Returns (model_name, temperature, parent_span_id) so that analyst
    spans appear as children of the coordinator span in the trace tree.
    """
    ctx = get_model_context()
    model_name = ctx.model_name if ctx else None
    temperature = ctx.temperature if ctx else None
    parent_span_id = None
    try:
        active_span = get_active_span()
        if active_span and hasattr(active_span, "span_id"):
            parent_span_id = active_span.span_id
    except Exception:
        logger.debug("Failed to get active span for parent span ID", exc_info=True)
    return model_name, temperature, parent_span_id


async def _run_energy(
    query: str, hours: int, entity_ids: list[str] | None, *, depth: str = "standard"
) -> str:
    """Run the Energy Analyst and return formatted findings."""
    if not await is_agent_enabled("energy_analyst"):
        return "Energy Analyst is currently disabled."
    emit_progress("agent_start", "energy_analyst", "Energy Analyst started")
    try:
        emit_progress(
            "status", "energy_analyst", f"Running energy analysis ({hours}h, depth={depth})..."
        )
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = EnergyAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
            depth=depth,
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])
        return _format_findings(result)
    except Exception as e:
        logger.error("Energy analysis failed: %s", e, exc_info=True)
        return f"Energy analysis failed: {e}"
    finally:
        emit_progress("agent_end", "energy_analyst", "Energy Analyst completed")


async def _run_behavioral(
    query: str, hours: int, entity_ids: list[str] | None, *, depth: str = "standard"
) -> str:
    """Run the Behavioral Analyst and return formatted findings."""
    if not await is_agent_enabled("behavioral_analyst"):
        return "Behavioral Analyst is currently disabled."
    emit_progress("agent_start", "behavioral_analyst", "Behavioral Analyst started")
    try:
        emit_progress(
            "status",
            "behavioral_analyst",
            f"Running behavioral analysis ({hours}h, depth={depth})...",
        )
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = BehavioralAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
            depth=depth,
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])
        return _format_findings(result)
    except Exception as e:
        logger.error("Behavioral analysis failed: %s", e, exc_info=True)
        return f"Behavioral analysis failed: {e}"
    finally:
        emit_progress("agent_end", "behavioral_analyst", "Behavioral Analyst completed")


async def _run_diagnostic(
    query: str, hours: int, entity_ids: list[str] | None, *, depth: str = "standard"
) -> str:
    """Run the Diagnostic Analyst and return formatted findings."""
    if not await is_agent_enabled("diagnostic_analyst"):
        return "Diagnostic Analyst is currently disabled."
    emit_progress("agent_start", "diagnostic_analyst", "Diagnostic Analyst started")
    try:
        emit_progress(
            "status",
            "diagnostic_analyst",
            f"Running diagnostic analysis ({hours}h, depth={depth})...",
        )
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = DiagnosticAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
            depth=depth,
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])
        return _format_findings(result)
    except Exception as e:
        logger.error("Diagnostic analysis failed: %s", e, exc_info=True)
        return f"Diagnostic analysis failed: {e}"
    finally:
        emit_progress("agent_end", "diagnostic_analyst", "Diagnostic Analyst completed")


@tool("consult_dashboard_designer")
@trace_with_uri(name="agent.consult_dashboard_designer", span_type="TOOL")
async def consult_dashboard_designer(
    query: str,
) -> str:
    """Consult the Dashboard Designer to create or update Lovelace dashboards.

    Use when the user asks about:
    - Creating a new Home Assistant dashboard
    - Updating or redesigning an existing dashboard
    - Adding cards, views, or sections to a dashboard
    - Dashboard layout or visualisation recommendations

    The Dashboard Designer will generate valid Lovelace YAML configuration
    based on the user's requirements, consulting DS team data as needed.

    Args:
        query: What the user wants for their dashboard (e.g.,
            "Create an energy monitoring dashboard",
            "Update my overview dashboard with temperature cards")

    Returns:
        Dashboard Designer's response with Lovelace YAML and explanation.
    """
    if not await is_agent_enabled("dashboard_designer"):
        return "Dashboard Designer is currently disabled. Enable it on the Agents page to use."

    # Emit delegation: architect -> dashboard_designer
    emit_delegation("architect", "dashboard_designer", query)
    emit_progress("agent_start", "dashboard_designer", "Dashboard Designer started")

    try:
        from langchain_core.messages import HumanMessage

        from src.agents.dashboard_designer import DashboardDesignerAgent
        from src.graph.state import DashboardState

        agent = DashboardDesignerAgent()
        state = DashboardState(messages=[HumanMessage(content=query)])
        result = await agent.invoke(state)

        # Extract the text response from the agent's messages
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            response = (
                last_msg.content if hasattr(last_msg, "content") else str(last_msg)  # type: ignore[misc]
            )
        else:
            response = "Dashboard Designer returned no response."

        # Emit delegation back: dashboard_designer -> architect
        summary = response[:300] + ("..." if len(response) > 300 else "")
        emit_delegation("dashboard_designer", "architect", summary)

        return response

    except Exception as e:
        logger.error("Dashboard design failed: %s", e, exc_info=True)
        return f"Dashboard design failed: {e}"
    finally:
        emit_progress("agent_end", "dashboard_designer", "Dashboard Designer completed")


def get_specialist_tools() -> list:
    """Return all specialist delegation tools (including team tool)."""
    return [
        consult_energy_analyst,
        consult_behavioral_analyst,
        consult_diagnostic_analyst,
        request_synthesis_review,
        consult_data_science_team,
        consult_dashboard_designer,
    ]
