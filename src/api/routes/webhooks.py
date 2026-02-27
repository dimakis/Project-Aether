"""Webhook receiver for Home Assistant event-driven insights.

Feature 10: Scheduled & Event-Driven Insights.

HA automations fire webhooks to this endpoint when events occur
(e.g., device goes unavailable, power spike, etc.). Aether matches
the incoming event against registered InsightSchedule webhook triggers
and runs the corresponding analysis.

Also handles ``entity_registry_updated`` events from HA to trigger
an immediate registry sync (automations/scripts/scenes).
"""

from __future__ import annotations

import fnmatch
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.rate_limit import limiter
from src.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class HAWebhookPayload(BaseModel):
    """Payload from a Home Assistant webhook automation action."""

    event_type: str = Field(
        ...,
        description="HA event type, e.g. 'state_changed', 'automation_triggered', 'custom'",
    )
    entity_id: str | None = Field(
        default=None,
        description="HA entity ID that triggered the event",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event data: old_state, new_state, attributes, etc.",
    )
    # Optional metadata
    webhook_event: str | None = Field(
        default=None,
        description="Custom event label to match against registered triggers (e.g. 'device_offline')",
    )


class WebhookResponse(BaseModel):
    """Response after processing a webhook."""

    status: str
    matched_schedules: int
    message: str


@router.post("/ha", response_model=WebhookResponse)
@limiter.limit("30/minute")
async def receive_ha_webhook(
    request: Request,
    payload: HAWebhookPayload,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    """Receive a webhook from Home Assistant and trigger matching insight analyses.

    HA automation example (YAML):
    ```yaml
    automation:
      trigger:
        - platform: state
          entity_id: sensor.grid_power
          to: "unavailable"
      action:
        - service: rest_command.aether_webhook
          data:
            event_type: state_changed
            entity_id: sensor.grid_power
            webhook_event: device_offline
            data:
              old_state: "{{ trigger.from_state.state }}"
              new_state: "{{ trigger.to_state.state }}"
    ```

    Rate limited to 30/minute to prevent HA event storms.
    """
    settings = get_settings()

    # Validate webhook secret — required in production, optional in development
    if settings.webhook_secret:
        import secrets as _secrets

        auth_header = request.headers.get("X-Webhook-Secret", "")
        if not _secrets.compare_digest(auth_header, settings.webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
    elif settings.environment == "production":
        raise HTTPException(
            status_code=500,
            detail="Webhook secret not configured. Set WEBHOOK_SECRET for production use.",
        )

    # HITL push notification: handle HA Companion App actionable notification callbacks.
    # The Companion App fires event type "mobile_app_notification_action" with the
    # action identifier in event_data.action.
    if payload.event_type == "mobile_app_notification_action":
        action_id = payload.data.get("action", "")
        if action_id.startswith(("APPROVE_", "REJECT_")):
            from src.hitl.action_log import record_action
            from src.hitl.push_notification import handle_notification_action

            result = await handle_notification_action(action_id)
            record_action(
                proposal_id=result.get("proposal_id", ""),
                action=result.get("action", "unknown"),
                status=result.get("status", "error"),
            )
            logger.info("Push notification action handled: %s", result)
            return WebhookResponse(
                status=result.get("status", "error"),
                matched_schedules=0,
                message=f"Proposal {result.get('action', 'unknown')}: {result.get('proposal_id', '')[:8]}",
            )

    # Entity registry sync: trigger immediate sync on registry changes
    if payload.event_type == "entity_registry_updated":
        background_tasks.add_task(_run_registry_sync)
        logger.info(
            "Entity registry updated — queued registry sync (data=%s)",
            payload.data,
        )

    # Find matching triggers
    from src.dal.insight_schedules import InsightScheduleRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = InsightScheduleRepository(session)

        # Get all enabled webhook triggers
        # Filter by webhook_event if provided, otherwise get all
        triggers = await repo.list_webhook_triggers(
            webhook_event=payload.webhook_event,
        )

        # If no event label match, try matching all webhook triggers by filter
        if not triggers and not payload.webhook_event:
            triggers = await repo.list_webhook_triggers()

    # Match triggers against the payload
    matched = []
    for trigger in triggers:
        if _matches_filter(trigger.webhook_filter, payload):
            matched.append(trigger)

    if not matched:
        logger.info(
            "Webhook received but no triggers matched: event_type=%s entity_id=%s webhook_event=%s",
            payload.event_type,
            payload.entity_id,
            payload.webhook_event,
        )
        return WebhookResponse(
            status="no_match",
            matched_schedules=0,
            message="No matching triggers found",
        )

    # Queue analysis jobs for each matched trigger
    for trigger in matched:
        background_tasks.add_task(
            _run_webhook_analysis,
            schedule_id=trigger.id,
            payload=payload,
        )

    logger.info(
        "Webhook matched %d trigger(s): event_type=%s entity_id=%s",
        len(matched),
        payload.event_type,
        payload.entity_id,
    )

    return WebhookResponse(
        status="accepted",
        matched_schedules=len(matched),
        message=f"Queued {len(matched)} analysis job(s)",
    )


def _matches_filter(
    webhook_filter: dict[str, Any] | None,
    payload: HAWebhookPayload,
) -> bool:
    """Check if a webhook payload matches a trigger's filter criteria.

    Supports:
    - entity_id: glob match (e.g., "sensor.power*", "light.*")
    - event_type: exact match
    - to_state / from_state: exact match against data.new_state / data.old_state
    """
    if not webhook_filter:
        # No filter = match everything
        return True

    # Check entity_id (glob matching)
    if "entity_id" in webhook_filter and payload.entity_id:
        pattern = webhook_filter["entity_id"]
        if not fnmatch.fnmatch(payload.entity_id, pattern):
            return False
    elif "entity_id" in webhook_filter and not payload.entity_id:
        return False

    # Check event_type
    if "event_type" in webhook_filter and payload.event_type != webhook_filter["event_type"]:
        return False

    # Check to_state
    if "to_state" in webhook_filter:
        new_state = payload.data.get("new_state")
        if new_state != webhook_filter["to_state"]:
            return False

    # Check from_state
    if "from_state" in webhook_filter:
        old_state = payload.data.get("old_state")
        if old_state != webhook_filter["from_state"]:
            return False

    return True


async def _run_webhook_analysis(
    schedule_id: str,
    payload: HAWebhookPayload,
) -> None:
    """Execute an insight analysis triggered by a webhook event."""
    import time as _time

    from src.dal.insight_schedules import InsightScheduleRepository
    from src.graph.workflows import run_analysis_workflow
    from src.jobs import emit_job_complete, emit_job_failed, emit_job_start
    from src.storage import get_session

    logger.info("Running webhook-triggered analysis: schedule=%s", schedule_id)

    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        schedule = await repo.get(schedule_id)

        if not schedule or not schedule.enabled:
            logger.warning("Schedule %s not found or disabled", schedule_id)
            return

        job_id = f"webhook:{schedule_id}:{int(_time.time())}"
        trigger_label = payload.webhook_event or payload.event_type or "event"
        emit_job_start(job_id, "webhook", f"Webhook: {schedule.name} ({trigger_label})")

        try:
            import json

            context_parts = []
            if schedule.options:
                context_parts.append(f"Schedule options: {json.dumps(schedule.options)}")
            context_parts.append(
                f"Triggered by webhook: {payload.webhook_event or payload.event_type}"
            )
            if payload.entity_id:
                context_parts.append(f"Trigger entity: {payload.entity_id}")
            if payload.data:
                context_parts.append(f"Trigger data: {json.dumps(payload.data)}")
            custom_query = "; ".join(context_parts) if context_parts else None

            # If the schedule doesn't scope entity_ids, use the webhook entity
            entity_ids = schedule.entity_ids
            if not entity_ids and payload.entity_id:
                entity_ids = [payload.entity_id]

            await run_analysis_workflow(
                analysis_type=schedule.analysis_type,
                entity_ids=entity_ids,
                hours=schedule.hours,
                custom_query=custom_query,
            )

            schedule.record_run(success=True)
            logger.info(
                "Webhook analysis %s completed (run #%d)",
                schedule.name,
                schedule.run_count,
            )
            emit_job_complete(job_id)
        except Exception as e:
            schedule.record_run(success=False, error=str(e))
            logger.exception("Webhook analysis %s failed: %s", schedule.name, e)
            emit_job_failed(job_id, str(e))

        await session.commit()


async def _run_registry_sync() -> None:
    """Run a lightweight registry sync (automations/scripts/scenes).

    Called as a background task when HA fires ``entity_registry_updated``.
    Uses ``run_registry_sync`` which only re-syncs registry tables,
    not all entities.
    """
    from src.dal.sync import run_registry_sync
    from src.storage import get_session

    logger.info("Running webhook-triggered registry sync")

    try:
        async with get_session() as session:
            stats = await run_registry_sync(session)
        logger.info("Webhook registry sync complete: %s", stats)
    except Exception as e:
        logger.exception("Webhook registry sync failed: %s", e)
