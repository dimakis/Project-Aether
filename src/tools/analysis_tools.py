"""Custom analysis tools for the Architect agent.

Allows the Architect to delegate free-form analysis requests to the
Data Scientist agent. Results are persisted as insights visible in
the Insights page.

This leverages the existing AnalysisType.CUSTOM with custom_query
support already built into the Data Scientist pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from src.agents.model_context import get_model_context, model_context
from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)


@tool("run_custom_analysis")
@trace_with_uri(name="agent.run_custom_analysis", span_type="TOOL")
async def run_custom_analysis(
    description: str,
    hours: int = 24,
    entity_ids: list[str] | None = None,
    analysis_type: str = "custom",
) -> str:
    """Run a custom analysis based on a natural language description.

    Use this tool when the user asks for:
    - A specific analysis that doesn't match preset types
      (e.g., "check if my HVAC is short-cycling")
    - Ad-hoc investigation of patterns or anomalies
    - Custom data exploration
    - Any "why is X happening?" or "analyze Y" question

    The Data Scientist agent will generate and execute a Python script
    in a sandboxed environment to answer the question. Results are
    saved as insights visible on the Insights page.

    Args:
        description: Natural language description of what to analyze.
            Be specific about what patterns, metrics, or behaviors to look for.
            Examples:
            - "Check if the HVAC system is short-cycling (turning on/off too frequently)"
            - "Find which devices consume the most energy between midnight and 6am"
            - "Analyze if there's a correlation between outdoor temperature and heating costs"
        hours: Hours of historical data to analyze (default: 24, max: 168)
        entity_ids: Specific entity IDs to analyze (optional, auto-discovers if empty)
        analysis_type: Override analysis type if a preset fits better.
            Defaults to "custom" for free-form queries.

    Returns:
        A conversational summary of the analysis findings and any insights generated
    """
    from src.agents import DataScientistWorkflow
    from src.graph.state import AnalysisType
    from src.storage import get_session

    # Map string to enum
    type_map = {
        "custom": AnalysisType.CUSTOM,
        "energy_optimization": AnalysisType.ENERGY_OPTIMIZATION,
        "anomaly_detection": AnalysisType.ANOMALY_DETECTION,
        "usage_patterns": AnalysisType.USAGE_PATTERNS,
        "device_health": AnalysisType.DEVICE_HEALTH,
        "behavior_analysis": AnalysisType.BEHAVIOR_ANALYSIS,
        "comfort_analysis": AnalysisType.CUSTOM,
        "security_audit": AnalysisType.CUSTOM,
        "weather_correlation": AnalysisType.CUSTOM,
    }
    analysis_enum = type_map.get(analysis_type, AnalysisType.CUSTOM)

    # Cap hours to reasonable limit
    hours = max(1, min(hours, 168))

    try:
        # Propagate model context to the Data Scientist
        ctx = get_model_context()
        parent_span_id = None
        try:
            from src.tracing import get_active_span

            active_span = get_active_span()
            if active_span and hasattr(active_span, "span_id"):
                parent_span_id = active_span.span_id
        except Exception:
            pass

        with model_context(
            model_name=ctx.model_name if ctx else None,
            temperature=ctx.temperature if ctx else None,
            parent_span_id=parent_span_id,
        ):
            workflow = DataScientistWorkflow()

            async with get_session() as session:
                state = await workflow.run_analysis(
                    analysis_type=analysis_enum,
                    entity_ids=entity_ids,
                    hours=hours,
                    custom_query=description,
                    session=session,
                )
                await session.commit()

        # Format results
        return _format_custom_analysis(state, description, hours)

    except Exception as e:
        logger.error("Custom analysis failed: %s", e)
        return f"I wasn't able to complete the analysis: {e}"


def _format_custom_analysis(state: Any, description: str, hours: int) -> str:
    """Format custom analysis results as a conversational response."""
    insights = state.insights or []
    recommendations = state.recommendations or []

    if not insights:
        return (
            f"I analyzed {hours} hours of data for your question: *\"{description}\"*\n\n"
            "I didn't find any significant patterns or issues matching your query. "
            "This could mean everything is operating normally, or the data may not "
            "contain enough information for this specific analysis.\n\n"
            "You can try:\n"
            "- Extending the lookback window (more hours)\n"
            "- Specifying particular entity IDs to focus on\n"
            "- Rephrasing the question with more specific criteria"
        )

    parts = [
        f"Here are the results for: *\"{description}\"* "
        f"({hours}h lookback, {len(insights)} insight(s) found):\n"
    ]

    # Key insights
    for i, insight in enumerate(insights[:5], 1):
        confidence = insight.get("confidence", 0) * 100
        impact = insight.get("impact", "medium")
        title = insight.get("title", "Finding")
        desc = insight.get("description", "")

        impact_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }.get(impact, "🟡")

        parts.append(f"{impact_icon} **{title}** ({confidence:.0f}% confidence)")
        if desc:
            parts.append(f"   {desc[:200]}")
        parts.append("")

    # Recommendations
    if recommendations:
        parts.append("**Recommendations:**")
        for rec in recommendations[:3]:
            parts.append(f"- {rec}")

    parts.append(
        "\nThese insights have been saved and are visible on the **Insights** page "
        "for detailed review."
    )
    return "\n".join(parts)


def get_analysis_tools() -> list:
    """Return custom analysis tools for the Architect agent."""
    return [run_custom_analysis]
