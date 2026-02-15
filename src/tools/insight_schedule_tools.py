"""Insight schedule tools for the Architect agent.

Allows the Architect to create and manage insight schedules
through natural language conversation. Schedule creation goes
through the DAL directly (same path as the API endpoint).

Constitution: These are non-destructive data-analysis schedules,
not HA mutations, so they don't require seek_approval. They only
configure *when* analysis runs — the analysis itself is read-only.
"""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)

# Valid analysis types matching AnalysisType enum
VALID_ANALYSIS_TYPES = {
    "energy_optimization",
    "anomaly_detection",
    "usage_patterns",
    "device_health",
    "behavior_analysis",
    "automation_analysis",
    "automation_gap_detection",
    "correlation_discovery",
    "cost_optimization",
    "comfort_analysis",
    "security_audit",
    "weather_correlation",
    "custom",
}

# Valid trigger types
VALID_TRIGGER_TYPES = {"cron", "webhook"}


@tool("create_insight_schedule")
@trace_with_uri(name="schedule.create_insight_schedule", span_type="TOOL")
async def create_insight_schedule(
    name: str,
    analysis_type: str,
    trigger_type: str = "cron",
    cron_expression: str | None = None,
    hours: int = 24,
    entity_ids: list[str] | None = None,
    webhook_event: str | None = None,
    custom_prompt: str | None = None,
) -> str:
    """Create a recurring or event-driven analysis schedule.

    Args:
        name: Schedule name
        analysis_type: energy_optimization, anomaly_detection, usage_patterns,
            device_health, behavior_analysis, automation_analysis,
            automation_gap_detection, correlation_discovery, cost_optimization,
            comfort_analysis, security_audit, weather_correlation, custom
        trigger_type: "cron" or "webhook"
        cron_expression: Cron expression (e.g. "0 2 * * *")
        hours: Lookback hours (default 24, max 8760)
        entity_ids: Entity IDs to analyze (optional)
        webhook_event: Event label for webhook triggers
        custom_prompt: Analysis description (required for "custom" type)
    """
    from src.dal.insight_schedules import InsightScheduleRepository
    from src.storage import get_session

    # Validate analysis_type
    if analysis_type not in VALID_ANALYSIS_TYPES:
        return (
            f"Invalid analysis_type '{analysis_type}'. "
            f"Valid types: {', '.join(sorted(VALID_ANALYSIS_TYPES))}"
        )

    # Validate trigger_type
    if trigger_type not in VALID_TRIGGER_TYPES:
        return f"Invalid trigger_type '{trigger_type}'. Must be 'cron' or 'webhook'."

    # Validate trigger-specific requirements
    if trigger_type == "cron" and not cron_expression:
        return (
            "A cron_expression is required for cron triggers (e.g., '0 2 * * *' for daily at 2am)."
        )

    if trigger_type == "webhook" and not webhook_event:
        return "A webhook_event label is required for webhook triggers (e.g., 'device_offline')."

    # Validate cron expression syntax
    if cron_expression:
        try:
            from apscheduler.triggers.cron import CronTrigger

            CronTrigger.from_crontab(cron_expression)
        except (ValueError, ImportError) as e:
            return f"Invalid cron expression '{cron_expression}': {e}"

    # Validate custom analysis requires a prompt
    if analysis_type == "custom" and not custom_prompt:
        return "A custom_prompt is required when analysis_type is 'custom'. Describe what you want to analyze."

    # Cap hours
    hours = max(1, min(hours, 8760))

    # Build options dict
    options: dict = {}
    if custom_prompt:
        options["custom_query"] = custom_prompt

    try:
        async with get_session() as session:
            repo = InsightScheduleRepository(session)
            schedule = await repo.create(
                name=name,
                analysis_type=analysis_type,
                trigger_type=trigger_type,
                hours=hours,
                entity_ids=entity_ids,
                options=options,
                cron_expression=cron_expression,
                webhook_event=webhook_event,
                enabled=True,
            )
            await session.commit()

            # Sync APScheduler if it's a cron schedule
            if trigger_type == "cron":
                try:
                    from src.scheduler.service import SchedulerService

                    scheduler = SchedulerService.get_instance()
                    if scheduler:
                        await scheduler.sync_jobs()
                except Exception:
                    logger.debug("Scheduler sync skipped (not running)", exc_info=True)

            logger.info("Created insight schedule %s: %s", schedule.id, name)

            # Build confirmation message
            trigger_desc = (
                f"Cron: `{cron_expression}`"
                if trigger_type == "cron"
                else f"Webhook: `{webhook_event}`"
            )
            parts = [
                f"I've created the insight schedule **{name}**:\n",
                f"- **Analysis**: {analysis_type.replace('_', ' ').title()}",
                f"- **Trigger**: {trigger_desc}",
                f"- **Lookback**: {hours} hours",
                f"- **Schedule ID**: `{schedule.id[:8]}...`",
            ]
            if entity_ids:
                parts.append(f"- **Entities**: {', '.join(f'`{e}`' for e in entity_ids[:5])}")
            if custom_prompt:
                parts.append(f"- **Custom query**: {custom_prompt}")
            parts.append(
                "\nThe schedule is now **active** and will run automatically. "
                "You can manage it on the **Schedules** page."
            )
            return "\n".join(parts)

    except Exception as e:
        logger.error("Failed to create insight schedule: %s", e)
        return f"Failed to create the insight schedule: {e}"


def get_insight_schedule_tools() -> list:
    """Return insight schedule tools for the Architect agent."""
    return [create_insight_schedule]
