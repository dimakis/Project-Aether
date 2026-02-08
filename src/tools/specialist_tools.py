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

import logging
import re
from typing import Any

from langchain_core.tools import tool

from src.agents.behavioral_analyst import BehavioralAnalyst
from src.agents.config_cache import is_agent_enabled
from src.agents.diagnostic_analyst import DiagnosticAnalyst
from src.agents.energy_analyst import EnergyAnalyst
from src.agents.execution_context import emit_progress
from src.agents.model_context import get_model_context, model_context
from src.agents.synthesis import LLMSynthesizer, ProgrammaticSynthesizer, SynthesisStrategy
from src.graph.state import AnalysisState, AnalysisType, TeamAnalysis
from src.tracing import get_active_span, trace_with_uri

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Smart routing — keyword-based specialist selection
# ---------------------------------------------------------------------------

SPECIALIST_TRIGGERS: dict[str, frozenset[str]] = {
    "energy": frozenset({
        "energy", "power", "consumption", "solar", "battery", "batteries",
        "kwh", "cost", "costs", "watt", "watts", "grid", "peak",
        "tariff", "electricity",
    }),
    "behavioral": frozenset({
        "pattern", "patterns", "behavior", "behaviour", "routine", "routines",
        "habit", "habits", "automation", "automations", "scene", "scenes",
        "script", "scripts", "usage", "schedule", "schedules",
        "occupancy", "manual", "trigger", "triggers", "frequency", "gap", "gaps",
    }),
    "diagnostic": frozenset({
        "error", "errors", "unavailable", "broken", "offline", "health",
        "diagnose", "diagnosis", "troubleshoot", "fix", "issue", "issues",
        "problem", "problems", "integration", "integrations",
        "sensor", "sensors", "unreliable",
    }),
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

# Module-level TeamAnalysis cache for the current analysis session.
# Reset when a new analysis begins.
_current_team_analysis: TeamAnalysis | None = None


def _get_or_create_team_analysis(query: str) -> TeamAnalysis:
    """Get the current team analysis or create a new one."""
    global _current_team_analysis  # noqa: PLW0603
    if _current_team_analysis is None:
        from uuid import uuid4

        _current_team_analysis = TeamAnalysis(
            request_id=str(uuid4()),
            request_summary=query,
        )
    return _current_team_analysis


def reset_team_analysis() -> None:
    """Reset the team analysis for a new session."""
    global _current_team_analysis  # noqa: PLW0603
    _current_team_analysis = None


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
            global _current_team_analysis  # noqa: PLW0603
            _current_team_analysis = result["team_analysis"]

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
            global _current_team_analysis  # noqa: PLW0603
            _current_team_analysis = result["team_analysis"]

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
            global _current_team_analysis  # noqa: PLW0603
            _current_team_analysis = result["team_analysis"]

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
    global _current_team_analysis  # noqa: PLW0603
    try:
        ta = _current_team_analysis
        if ta is None or not ta.findings:
            return "No specialist findings to synthesize. Consult specialists first."

        from src.llm import get_llm

        llm = get_llm()
        synth = LLMSynthesizer(llm=llm)
        result = await synth.synthesize(ta)

        # Update shared state
        _current_team_analysis = result

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

    Returns:
        A unified, synthesised summary of all specialist findings
        including cross-referenced insights and recommendations.
    """
    hours = min(max(hours, 1), 168)
    effective_query = custom_query or query

    # 1. Smart routing
    selected = _select_specialists(effective_query, specialists)
    logger.info(
        "DS team routing: query=%r  selected=%s  explicit=%s",
        effective_query[:80],
        selected,
        specialists is not None,
    )

    # 2. Reset shared state for a fresh analysis session
    reset_team_analysis()

    # 3. Run each selected specialist (sequentially — they share TeamAnalysis)
    results: list[str] = []
    specialist_runners = {
        "energy": _run_energy,
        "behavioral": _run_behavioral,
        "diagnostic": _run_diagnostic,
    }
    for name in selected:
        runner = specialist_runners.get(name)
        if runner:
            result = await runner(effective_query, hours, entity_ids)
            results.append(f"**{name.title()} Analyst:** {result}")

    # 4. Auto-synthesise if 2+ specialists contributed findings
    global _current_team_analysis  # noqa: PLW0603
    ta = _current_team_analysis
    if ta and len(ta.findings) > 0 and len(selected) >= 2:
        try:
            synth = ProgrammaticSynthesizer()
            ta = synth.synthesize(ta)
            _current_team_analysis = ta
        except Exception as e:
            logger.warning("Programmatic synthesis failed: %s", e)

    # 5. Format unified response
    parts = [f"**Data Science Team Report** ({len(selected)} specialist(s), {hours}h window)\n"]
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

    return "\n".join(parts)


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
        pass
    return model_name, temperature, parent_span_id


async def _run_energy(query: str, hours: int, entity_ids: list[str] | None) -> str:
    """Run the Energy Analyst and return formatted findings."""
    if not await is_agent_enabled("energy_analyst"):
        return "Energy Analyst is currently disabled."
    emit_progress("agent_start", "energy_analyst", "Energy Analyst started")
    try:
        emit_progress("status", "energy_analyst", f"Running energy analysis ({hours}h)...")
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = EnergyAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            global _current_team_analysis  # noqa: PLW0603
            _current_team_analysis = result["team_analysis"]
        return _format_findings(result)
    except Exception as e:
        logger.error("Energy analysis failed: %s", e, exc_info=True)
        return f"Energy analysis failed: {e}"
    finally:
        emit_progress("agent_end", "energy_analyst", "Energy Analyst completed")


async def _run_behavioral(query: str, hours: int, entity_ids: list[str] | None) -> str:
    """Run the Behavioral Analyst and return formatted findings."""
    if not await is_agent_enabled("behavioral_analyst"):
        return "Behavioral Analyst is currently disabled."
    emit_progress("agent_start", "behavioral_analyst", "Behavioral Analyst started")
    try:
        emit_progress("status", "behavioral_analyst", f"Running behavioral analysis ({hours}h)...")
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = BehavioralAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            global _current_team_analysis  # noqa: PLW0603
            _current_team_analysis = result["team_analysis"]
        return _format_findings(result)
    except Exception as e:
        logger.error("Behavioral analysis failed: %s", e, exc_info=True)
        return f"Behavioral analysis failed: {e}"
    finally:
        emit_progress("agent_end", "behavioral_analyst", "Behavioral Analyst completed")


async def _run_diagnostic(query: str, hours: int, entity_ids: list[str] | None) -> str:
    """Run the Diagnostic Analyst and return formatted findings."""
    if not await is_agent_enabled("diagnostic_analyst"):
        return "Diagnostic Analyst is currently disabled."
    emit_progress("agent_start", "diagnostic_analyst", "Diagnostic Analyst started")
    try:
        emit_progress("status", "diagnostic_analyst", f"Running diagnostic analysis ({hours}h)...")
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = DiagnosticAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            global _current_team_analysis  # noqa: PLW0603
            _current_team_analysis = result["team_analysis"]
        return _format_findings(result)
    except Exception as e:
        logger.error("Diagnostic analysis failed: %s", e, exc_info=True)
        return f"Diagnostic analysis failed: {e}"
    finally:
        emit_progress("agent_end", "diagnostic_analyst", "Diagnostic Analyst completed")


def get_specialist_tools() -> list:
    """Return all specialist delegation tools (including team tool)."""
    return [
        consult_energy_analyst,
        consult_behavioral_analyst,
        consult_diagnostic_analyst,
        request_synthesis_review,
        consult_data_science_team,
    ]
