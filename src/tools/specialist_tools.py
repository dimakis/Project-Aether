"""Specialist delegation tools for the Architect.

These tools allow the Architect to delegate analysis tasks to the
DS team specialists (Energy, Behavioral, Diagnostic) and request
LLM synthesis reviews for complex/conflicting findings.

The Architect calls these tools during conversation to gather
specialist insights, which are accumulated in a TeamAnalysis object
for cross-consultation and synthesis.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from src.agents.behavioral_analyst import BehavioralAnalyst
from src.agents.config_cache import is_agent_enabled
from src.agents.diagnostic_analyst import DiagnosticAnalyst
from src.agents.energy_analyst import EnergyAnalyst
from src.agents.synthesis import LLMSynthesizer, SynthesisStrategy
from src.graph.state import AnalysisState, AnalysisType, TeamAnalysis
from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)

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


def get_specialist_tools() -> list:
    """Return all specialist delegation tools."""
    return [
        consult_energy_analyst,
        consult_behavioral_analyst,
        consult_diagnostic_analyst,
        request_synthesis_review,
    ]
