"""Agent delegation tools for the Architect.

Allows the Architect to delegate tasks to specialist agents
(Data Scientist, Librarian) and receive conversational responses.

These tools enable a unified chat experience where users interact
with the Architect, who intelligently routes to specialists.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from src.agents.model_context import get_model_context, model_context
from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)


@tool("analyze_energy")
@trace_with_uri(name="agent.analyze_energy", span_type="TOOL")
async def analyze_energy(
    analysis_type: str = "energy_optimization",
    hours: int = 24,
    entity_ids: list[str] | None = None,
) -> str:
    """Analyze energy consumption patterns and get optimization insights.

    Use this tool when the user asks about:
    - Energy usage or consumption
    - Power optimization
    - Electricity costs or savings
    - Unusual energy patterns or anomalies
    - Peak usage times

    Args:
        analysis_type: Type of analysis to perform:
            - "energy_optimization": Find energy saving opportunities
            - "anomaly_detection": Detect unusual consumption patterns
            - "usage_patterns": Identify daily/weekly patterns
        hours: Hours of historical data to analyze (default: 24, max: 168)
        entity_ids: Specific energy sensors to analyze (optional, auto-discovers if empty)

    Returns:
        A conversational summary of the analysis with key insights
    """
    from src.agents import DataScientistWorkflow
    from src.graph.state import AnalysisType
    from src.storage import get_session

    # Map string to enum
    type_map = {
        "energy_optimization": AnalysisType.ENERGY_OPTIMIZATION,
        "anomaly_detection": AnalysisType.ANOMALY_DETECTION,
        "usage_patterns": AnalysisType.USAGE_PATTERNS,
        "pattern": AnalysisType.USAGE_PATTERNS,
        "anomaly": AnalysisType.ANOMALY_DETECTION,
        "energy": AnalysisType.ENERGY_OPTIMIZATION,
    }
    analysis_enum = type_map.get(analysis_type.lower(), AnalysisType.ENERGY_OPTIMIZATION)

    # Cap hours to reasonable limit
    hours = min(hours, 168)  # Max 1 week

    try:
        # Propagate model context to the Data Scientist.
        # The contextvars already flow through async calls, but we also
        # capture the parent span ID for inter-agent trace linking.
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
                    session=session,
                )
                await session.commit()

        # Generate conversational summary
        return _format_energy_analysis(state, analysis_type, hours)

    except Exception as e:
        return f"I wasn't able to complete the energy analysis: {e}"


def _format_energy_analysis(state: Any, analysis_type: str, hours: int) -> str:
    """Format analysis results as conversational response with data."""
    insights = state.insights or []
    recommendations = state.recommendations or []

    if not insights:
        return (
            f"I analyzed {hours} hours of energy data but didn't find any significant "
            f"patterns or issues. Your energy consumption appears to be normal."
        )

    # Build conversational response
    parts = []

    # Opening summary
    high_impact = [i for i in insights if i.get("impact") in ("high", "critical")]
    if high_impact:
        parts.append(
            f"I analyzed {hours} hours of energy data and found "
            f"**{len(high_impact)} important insight(s)** that need your attention:"
        )
    else:
        parts.append(
            f"I analyzed {hours} hours of energy data. Here's what I found:"
        )

    # Key insights as bullet points
    parts.append("\n**Key Findings:**")
    for i, insight in enumerate(insights[:5], 1):  # Limit to top 5
        confidence = insight.get("confidence", 0) * 100
        impact = insight.get("impact", "medium")
        title = insight.get("title", "Finding")
        description = insight.get("description", "")

        impact_indicator = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            impact, "⚪"
        )

        parts.append(f"\n{i}. {impact_indicator} **{title}** ({confidence:.0f}% confidence)")
        if description:
            parts.append(f"   {description[:200]}")

    # Recommendations
    if recommendations:
        parts.append("\n**Recommendations:**")
        for rec in recommendations[:3]:  # Limit to top 3
            parts.append(f"• {rec}")

    # Closing
    parts.append(
        f"\n_Analysis covered {hours} hours of data from {len(state.entity_ids)} sensors._"
    )

    # Reverse communication: if the Data Scientist suggests an automation
    suggestion = getattr(state, "automation_suggestion", None)
    if suggestion:
        # AutomationSuggestion is now a structured model
        desc = getattr(suggestion, "pattern", str(suggestion))
        entities = getattr(suggestion, "entities", [])
        confidence = getattr(suggestion, "confidence", 0)
        parts.append(
            f"\n---\n💡 **Data Scientist Suggestion:** {desc}"
        )
        if entities:
            parts.append(f"   Entities: {', '.join(entities[:5])}")
        if confidence:
            parts.append(f"   Confidence: {confidence:.0%}")
        parts.append("Would you like me to design an automation for this?")

    return "\n".join(parts)


@tool("discover_entities")
@trace_with_uri(name="agent.discover_entities", span_type="TOOL")
async def discover_entities(domain_filter: str | None = None) -> str:
    """Discover and catalog Home Assistant entities.

    Use this tool when the user asks to:
    - Refresh or update the entity list
    - Discover new devices
    - Sync with Home Assistant
    - Find all entities of a type

    Args:
        domain_filter: Optional domain to filter (e.g., "light", "sensor", "switch")

    Returns:
        A summary of discovered entities
    """
    from src.agents.librarian import LibrarianWorkflow
    from src.storage import get_session
    from src.tracing.context import session_context

    try:
        async with get_session() as session:
            with session_context():
                workflow = LibrarianWorkflow()
                state = await workflow.run_discovery(
                    triggered_by="architect_request",
                    domain_filter=domain_filter,
                )

        # Format response
        return _format_discovery_results(state, domain_filter)

    except Exception as e:
        return f"I wasn't able to complete the entity discovery: {e}"


def _format_discovery_results(state: Any, domain_filter: str | None) -> str:
    """Format discovery results as conversational response."""
    entities_found = len(state.entities_found)
    added = state.entities_added
    updated = state.entities_updated
    removed = state.entities_removed
    devices = state.devices_found
    areas = state.areas_found

    parts = []

    # Opening
    if domain_filter:
        parts.append(f"I've scanned Home Assistant for **{domain_filter}** entities.")
    else:
        parts.append("I've completed a full scan of your Home Assistant setup.")

    # Summary stats
    parts.append(f"\n**Discovery Summary:**")
    parts.append(f"• Found **{entities_found}** entities total")
    if devices:
        parts.append(f"• Identified **{devices}** devices")
    if areas:
        parts.append(f"• Organized into **{areas}** areas")

    # Changes
    if added or updated or removed:
        parts.append(f"\n**Changes since last sync:**")
        if added:
            parts.append(f"• ✅ {added} new entities added")
        if updated:
            parts.append(f"• 🔄 {updated} entities updated")
        if removed:
            parts.append(f"• ❌ {removed} entities removed")
    else:
        parts.append("\nNo changes detected since last discovery.")

    # Domain breakdown if full scan
    if not domain_filter and state.entities_found:
        domains: dict[str, int] = {}
        for entity in state.entities_found:
            domain = entity.domain
            domains[domain] = domains.get(domain, 0) + 1

        if domains:
            parts.append("\n**By Domain:**")
            for domain, count in sorted(domains.items(), key=lambda x: -x[1])[:8]:
                parts.append(f"• {domain}: {count}")

    return "\n".join(parts)


@tool("get_entity_history")
@trace_with_uri(name="agent.get_entity_history", span_type="TOOL")
async def get_entity_history(
    entity_id: str,
    hours: int = 24,
    detailed: bool = False,
) -> str:
    """Get historical state changes for an entity.

    Use this when the user asks about:
    - What happened to a specific device/sensor
    - History of state changes
    - When something turned on/off
    - Diagnosing data gaps or missing data

    Args:
        entity_id: The entity to get history for
        hours: Hours of history to fetch (default: 24, max: 168)
        detailed: If True, include gap detection, state distribution,
            and up to 20 recent changes instead of 5

    Returns:
        A summary of the entity's recent history
    """
    from src.ha import get_ha_client

    hours = min(hours, 168)

    try:
        ha = get_ha_client()
        history = await ha.get_history(entity_id=entity_id, hours=hours)

        if not history or not history.get("states"):
            return f"No history found for {entity_id} in the last {hours} hours."

        states = history.get("states", [])
        count = history.get("count", len(states))

        if detailed:
            return _format_detailed_history(entity_id, hours, states, count)

        # Basic summary (original behavior)
        parts = [f"**History for {entity_id}** (last {hours} hours):"]
        parts.append(f"• {count} state changes recorded")

        if states:
            # Show recent changes
            parts.append("\n**Recent changes:**")
            for state in states[-5:]:  # Last 5
                time = state.get("last_changed", "unknown")
                value = state.get("state", "unknown")
                parts.append(f"• {time}: {value}")

        return "\n".join(parts)

    except Exception as e:
        return f"Couldn't retrieve history for {entity_id}: {e}"


def _format_detailed_history(
    entity_id: str,
    hours: int,
    states: list[dict[str, Any]],
    count: int,
) -> str:
    """Format detailed history with gap detection, statistics, and more entries."""
    from datetime import datetime, timedelta, timezone

    parts = [f"**Detailed History for {entity_id}** (last {hours} hours):"]
    parts.append(f"• Total state changes: {count}")

    # First/last timestamps
    if states:
        first_changed = states[0].get("last_changed", "unknown")
        last_changed = states[-1].get("last_changed", "unknown")
        parts.append(f"• First recorded: {first_changed}")
        parts.append(f"• Last recorded: {last_changed}")

    # State distribution
    state_counts: dict[str, int] = {}
    for s in states:
        val = str(s.get("state", "unknown"))
        state_counts[val] = state_counts.get(val, 0) + 1

    if state_counts:
        parts.append("\n**State Distribution:**")
        for state_val, cnt in sorted(state_counts.items(), key=lambda x: -x[1]):
            pct = (cnt / len(states) * 100) if states else 0
            parts.append(f"• {state_val}: {cnt} ({pct:.1f}%)")

    # Gap detection
    gaps = _detect_gaps(states, hours)
    if gaps:
        parts.append(f"\n**Data Gaps Detected ({len(gaps)}):**")
        for gap in gaps[:5]:  # Show up to 5 gaps
            parts.append(
                f"• {gap['start']} → {gap['end']} "
                f"({gap['duration_hours']:.1f}h with no data)"
            )
    else:
        parts.append("\n**Data Gaps:** None detected")

    # Recent changes (up to 20)
    display_states = states[-20:]
    parts.append(f"\n**Recent Changes ({len(display_states)} of {count}):**")
    for s in display_states:
        time = s.get("last_changed", "unknown")
        value = s.get("state", "unknown")
        parts.append(f"• {time}: {value}")

    return "\n".join(parts)


def _detect_gaps(
    states: list[dict[str, Any]],
    hours: int,
) -> list[dict[str, Any]]:
    """Detect significant gaps in state history.

    A gap is a period longer than expected_interval where no state
    changes were recorded. For short time ranges, the threshold is
    smaller; for longer ranges, we allow bigger gaps.
    """
    from datetime import datetime, timezone

    if len(states) < 2:
        return []

    # Threshold: gaps longer than 10% of the total range, minimum 1 hour
    threshold_hours = max(1.0, hours * 0.1)

    gaps = []
    for i in range(1, len(states)):
        prev_time_str = states[i - 1].get("last_changed", "")
        curr_time_str = states[i].get("last_changed", "")

        if not prev_time_str or not curr_time_str:
            continue

        try:
            # Parse ISO format timestamps
            prev_time = datetime.fromisoformat(prev_time_str.replace("Z", "+00:00"))
            curr_time = datetime.fromisoformat(curr_time_str.replace("Z", "+00:00"))
            delta = (curr_time - prev_time).total_seconds() / 3600

            if delta > threshold_hours:
                gaps.append({
                    "start": prev_time_str,
                    "end": curr_time_str,
                    "duration_hours": delta,
                })
        except (ValueError, TypeError):
            continue

    return gaps


@tool("diagnose_issue")
@trace_with_uri(name="agent.diagnose_issue", span_type="TOOL")
async def diagnose_issue(
    entity_ids: list[str],
    diagnostic_context: str,
    instructions: str,
    hours: int = 72,
) -> str:
    """Delegate a diagnostic investigation to the Data Scientist.

    Use this AFTER gathering evidence (logs, history, config checks) to have
    the Data Scientist analyze the data and identify root causes.

    Args:
        entity_ids: Entities involved in the issue
        diagnostic_context: Pre-collected evidence from the Architect:
            error logs, entity history observations, config check results,
            user-reported symptoms
        instructions: Specific analysis instructions for the Data Scientist,
            e.g. "Look for data gaps in the last week and identify what
            integration might have failed"
        hours: Hours of historical data to include (default: 72, max: 168)

    Returns:
        Diagnostic findings and recommendations from the Data Scientist
    """
    from src.agents import DataScientistWorkflow
    from src.graph.state import AnalysisType
    from src.storage import get_session

    hours = min(hours, 168)

    try:
        # Propagate model context + parent span for trace linking
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
                    analysis_type=AnalysisType.DIAGNOSTIC,
                    entity_ids=entity_ids,
                    hours=hours,
                    custom_query=instructions,
                    diagnostic_context=diagnostic_context,
                    session=session,
                )
                await session.commit()

        return _format_diagnostic_results(state, entity_ids, hours)

    except Exception as e:
        return f"Diagnostic analysis failed: {e}"


def _format_diagnostic_results(state: Any, entity_ids: list[str], hours: int) -> str:
    """Format diagnostic analysis results as a conversational response."""
    insights = state.insights or []
    recommendations = state.recommendations or []

    if not insights:
        return (
            f"I analyzed {hours} hours of data for {len(entity_ids)} entities "
            f"but didn't identify any specific issues. The entities appear to be "
            f"functioning normally."
        )

    parts = []

    # Opening
    critical = [i for i in insights if i.get("impact") in ("critical", "high")]
    if critical:
        parts.append(
            f"**Diagnostic Analysis Complete** — found "
            f"**{len(critical)} significant issue(s)** across "
            f"{len(entity_ids)} entities:"
        )
    else:
        parts.append(
            f"**Diagnostic Analysis Complete** — analyzed {len(entity_ids)} "
            f"entities over {hours} hours:"
        )

    # Findings
    parts.append("\n**Findings:**")
    for i, insight in enumerate(insights[:8], 1):
        impact = insight.get("impact", "medium")
        title = insight.get("title", "Finding")
        description = insight.get("description", "")

        indicator = {
            "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"
        }.get(impact, "⚪")

        parts.append(f"\n{i}. {indicator} **{title}**")
        if description:
            parts.append(f"   {description[:300]}")

    # Recommendations
    if recommendations:
        parts.append("\n**Recommended Actions:**")
        for rec in recommendations[:5]:
            parts.append(f"• {rec}")

    parts.append(
        f"\n_Diagnostic covered {hours}h of data from "
        f"{len(entity_ids)} entities._"
    )

    # Reverse communication: if the Data Scientist suggests an automation
    suggestion = getattr(state, "automation_suggestion", None)
    if suggestion:
        desc = getattr(suggestion, "pattern", str(suggestion))
        entities = getattr(suggestion, "entities", [])
        confidence = getattr(suggestion, "confidence", 0)
        parts.append(
            f"\n---\n💡 **Data Scientist Suggestion:** {desc}"
        )
        if entities:
            parts.append(f"   Entities: {', '.join(entities[:5])}")
        if confidence:
            parts.append(f"   Confidence: {confidence:.0%}")
        parts.append("Would you like me to design an automation for this?")

    return "\n".join(parts)


@tool("analyze_behavior")
@trace_with_uri(name="agent.analyze_behavior", span_type="TOOL")
async def analyze_behavior(
    analysis_type: str = "behavior_analysis",
    hours: int = 168,
    entity_ids: list[str] | None = None,
) -> str:
    """Analyze behavioral patterns and find automation opportunities.

    Use this tool when the user asks about:
    - Usage patterns or behavioral analysis
    - Automation gaps or opportunities
    - Automation effectiveness
    - Entity correlations (devices used together)
    - Device health checks
    - Cost optimization

    Args:
        analysis_type: Type of analysis:
            - "behavior_analysis": Manual action patterns and timing
            - "automation_analysis": Automation effectiveness scoring
            - "automation_gap_detection": Find manual patterns to automate
            - "correlation_discovery": Find entity relationships
            - "device_health": Check device health and responsiveness
            - "cost_optimization": Cost projections and savings
        hours: Hours of historical data to analyze (default: 168 = 1 week, max: 720)
        entity_ids: Specific entities to analyze (optional)

    Returns:
        A conversational summary of the behavioral analysis
    """
    from src.agents import DataScientistWorkflow
    from src.graph.state import AnalysisType
    from src.storage import get_session

    # Map string to enum
    type_map = {
        "behavior_analysis": AnalysisType.BEHAVIOR_ANALYSIS,
        "behavior": AnalysisType.BEHAVIOR_ANALYSIS,
        "automation_analysis": AnalysisType.AUTOMATION_ANALYSIS,
        "automations": AnalysisType.AUTOMATION_ANALYSIS,
        "automation_gap_detection": AnalysisType.AUTOMATION_GAP_DETECTION,
        "gaps": AnalysisType.AUTOMATION_GAP_DETECTION,
        "correlation_discovery": AnalysisType.CORRELATION_DISCOVERY,
        "correlations": AnalysisType.CORRELATION_DISCOVERY,
        "device_health": AnalysisType.DEVICE_HEALTH,
        "health": AnalysisType.DEVICE_HEALTH,
        "cost_optimization": AnalysisType.COST_OPTIMIZATION,
        "cost": AnalysisType.COST_OPTIMIZATION,
    }
    analysis_enum = type_map.get(analysis_type.lower(), AnalysisType.BEHAVIOR_ANALYSIS)

    hours = min(hours, 720)  # Max 30 days

    try:
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
                    session=session,
                )
                await session.commit()

        return _format_behavioral_analysis(state, analysis_type, hours)

    except Exception as e:
        return f"I wasn't able to complete the behavioral analysis: {e}"


def _format_behavioral_analysis(state: Any, analysis_type: str, hours: int) -> str:
    """Format behavioral analysis results as conversational response."""
    insights = state.insights or []
    recommendations = state.recommendations or []

    if not insights:
        return (
            f"I analyzed {hours} hours of behavioral data but didn't find any "
            f"significant patterns. Your system appears to be operating normally."
        )

    parts = []
    high_impact = [i for i in insights if i.get("impact") in ("high", "critical")]

    if high_impact:
        parts.append(
            f"I analyzed {hours} hours of behavioral data and found "
            f"**{len(high_impact)} important finding(s)**:"
        )
    else:
        parts.append(
            f"I analyzed {hours} hours of behavioral data. Here's what I found:"
        )

    parts.append("\n**Key Findings:**")
    for i, insight in enumerate(insights[:5], 1):
        confidence = insight.get("confidence", 0) * 100
        impact = insight.get("impact", "medium")
        title = insight.get("title", "Finding")
        description = insight.get("description", "")
        insight_type = insight.get("type", "")

        impact_indicator = {
            "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"
        }.get(impact, "⚪")

        type_label = insight_type.replace("_", " ").title()
        parts.append(
            f"\n{i}. {impact_indicator} **{title}** "
            f"[{type_label}] ({confidence:.0f}% confidence)"
        )
        if description:
            parts.append(f"   {description[:200]}")

    if recommendations:
        parts.append("\n**Recommendations:**")
        for rec in recommendations[:3]:
            parts.append(f"• {rec}")

    # Automation suggestion
    suggestion = getattr(state, "automation_suggestion", None)
    if suggestion:
        desc = getattr(suggestion, "pattern", str(suggestion))
        trigger = getattr(suggestion, "proposed_trigger", "")
        action = getattr(suggestion, "proposed_action", "")
        parts.append(
            f"\n---\n💡 **Automation Suggestion:** {desc}"
        )
        if trigger:
            parts.append(f"   Trigger: {trigger}")
        if action:
            parts.append(f"   Action: {action}")
        parts.append("Would you like me to design an automation for this?")

    return "\n".join(parts)


@tool("propose_automation_from_insight")
@trace_with_uri(name="agent.propose_automation", span_type="TOOL")
async def propose_automation_from_insight(
    pattern: str,
    entities: list[str],
    proposed_trigger: str,
    proposed_action: str,
    confidence: float = 0.8,
    source_insight_type: str = "automation_gap",
) -> str:
    """Create an automation proposal from a Data Scientist insight.

    Use this when the Data Scientist has identified a pattern that could
    be automated and the user wants to proceed with creating it.

    Args:
        pattern: Description of the detected pattern
        entities: Entity IDs involved
        proposed_trigger: Suggested trigger for the automation
        proposed_action: Suggested action
        confidence: Confidence score 0.0-1.0
        source_insight_type: Type of insight that generated this

    Returns:
        The Architect's refined proposal or confirmation
    """
    from src.agents import ArchitectAgent
    from src.graph.state import AutomationSuggestion
    from src.storage import get_session

    suggestion = AutomationSuggestion(
        pattern=pattern,
        entities=entities,
        proposed_trigger=proposed_trigger,
        proposed_action=proposed_action,
        confidence=confidence,
        evidence={},
        source_insight_type=source_insight_type,
    )

    try:
        architect = ArchitectAgent()
        async with get_session() as session:
            result = await architect.receive_suggestion(suggestion, session)
            await session.commit()

        response_parts = []
        response_text = result.get("response", "")
        proposal_yaml = result.get("proposal_yaml")
        proposal_name = result.get("proposal_name")

        if proposal_name:
            response_parts.append(
                f"I've created an automation proposal: **{proposal_name}**"
            )
        if proposal_yaml:
            response_parts.append(f"\n```yaml\n{proposal_yaml}```")
        if response_text:
            response_parts.append(f"\n{response_text[:500]}")

        response_parts.append(
            "\nThis proposal is pending your approval before deployment."
        )

        return "\n".join(response_parts)

    except Exception as e:
        return f"I wasn't able to create a proposal from this suggestion: {e}"


def get_agent_tools() -> list[Any]:
    """Return all agent delegation tools for the Architect."""
    return [
        analyze_energy,
        analyze_behavior,
        discover_entities,
        get_entity_history,
        diagnose_issue,
        propose_automation_from_insight,
    ]


__all__ = [
    "analyze_energy",
    "analyze_behavior",
    "discover_entities",
    "get_entity_history",
    "diagnose_issue",
    "propose_automation_from_insight",
    "get_agent_tools",
]
