"""Automation suggestion generation for Data Scientist agent."""

from typing import Any

from src.graph.state import AutomationSuggestion


def generate_automation_suggestion(
    insights: list[dict[str, Any]],
) -> AutomationSuggestion | None:
    """Generate a structured automation suggestion from high-value insights.

    Scans insights for high-confidence (>=0.7) and high/critical impact
    findings that could be addressed by a Home Assistant automation.

    Args:
        insights: List of insight dictionaries

    Returns:
        An AutomationSuggestion model, or None if no suggestion.
    """
    for insight in insights:
        confidence = insight.get("confidence", 0)
        impact = insight.get("impact", "low")
        insight_type = insight.get("type", "")

        # Only suggest automations for actionable, high-confidence findings
        if confidence >= 0.7 and impact in ("high", "critical"):
            title = insight.get("title", "Untitled")
            description = insight.get("description", "")
            entities = insight.get("entities", [])
            evidence = insight.get("evidence", {})

            # Determine proposed trigger and action based on insight type
            proposed_trigger = ""
            proposed_action = ""

            if insight_type in ("energy_optimization", "cost_saving"):
                proposed_trigger = "time: off-peak hours"
                proposed_action = "Schedule energy-intensive devices during off-peak hours"
            elif insight_type == "automation_gap":
                proposed_trigger = evidence.get(
                    "proposed_trigger",
                    f"time: {evidence.get('typical_time', 'detected pattern time')}",
                )
                proposed_action = evidence.get(
                    "proposed_action",
                    f"Automate the manual pattern: {title}",
                )
            elif insight_type == "automation_inefficiency":
                proposed_trigger = "existing automation trigger"
                proposed_action = f"Improve automation: {title}"
            elif insight_type == "anomaly_detection":
                proposed_trigger = "state change pattern"
                proposed_action = "Alert or take corrective action when anomaly recurs"
            elif insight_type in ("usage_pattern", "behavioral_pattern"):
                proposed_trigger = "detected usage schedule"
                proposed_action = "Optimize device scheduling to match actual usage"
            elif insight_type == "correlation":
                proposed_trigger = "state change of correlated entity"
                proposed_action = "Synchronize correlated entities automatically"
            elif insight_type == "device_health":
                proposed_trigger = "device unavailable for > threshold"
                proposed_action = "Send notification about device health issue"
            else:
                proposed_trigger = "detected pattern"
                proposed_action = f"Address: {title}"

            return AutomationSuggestion(
                pattern=(f"{title}: {description[:200]}"),
                entities=entities[:10],
                proposed_trigger=proposed_trigger,
                proposed_action=proposed_action,
                confidence=confidence,
                evidence=evidence,
                source_insight_type=insight_type,
            )

    return None
