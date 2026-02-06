"""Agent delegation tools for the Architect.

Allows the Architect to delegate tasks to specialist agents
(Data Scientist, Librarian) and receive conversational responses.

These tools enable a unified chat experience where users interact
with the Architect, who intelligently routes to specialists.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.tracing import trace_with_uri


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
    from src.mcp import get_mcp_client

    hours = min(hours, 168)

    try:
        mcp = get_mcp_client()
        history = await mcp.get_history(entity_id=entity_id, hours=hours)

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


def get_agent_tools() -> list[Any]:
    """Return all agent delegation tools for the Architect."""
    return [
        analyze_energy,
        discover_entities,
        get_entity_history,
    ]


__all__ = [
    "analyze_energy",
    "discover_entities",
    "get_entity_history",
    "get_agent_tools",
]
