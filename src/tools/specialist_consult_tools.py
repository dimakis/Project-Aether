"""Individual specialist consult tools (energy, behavioral, diagnostic, synthesis, dashboard)."""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.agents.behavioral_analyst import BehavioralAnalyst
from src.agents.config_cache import is_agent_enabled
from src.agents.diagnostic_analyst import DiagnosticAnalyst
from src.agents.energy_analyst import EnergyAnalyst
from src.agents.execution_context import emit_delegation, emit_progress
from src.agents.synthesis import LLMSynthesizer
from src.graph.state import AnalysisState, AnalysisType
from src.tools.specialist_routing import (
    _format_findings,
    _get_or_create_team_analysis,
    _set_team_analysis,
)
from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)


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


@tool("consult_dashboard_designer")
@trace_with_uri(name="agent.consult_dashboard_designer", span_type="TOOL")
async def consult_dashboard_designer(
    query: str,
) -> str:
    """Consult the Dashboard Designer for Lovelace dashboards.

    Args:
        query: Dashboard request
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
        raw_messages = result.get("messages", [])
        messages = list(raw_messages) if isinstance(raw_messages, list) else []
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                c = last_msg.content
                response = c if isinstance(c, str) else str(c)
            else:
                response = str(last_msg)
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
