"""CRUD API for insight schedules.

Feature 10: Scheduled & Event-Driven Insights.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.dal.insight_schedules import InsightScheduleRepository
from src.storage import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insight-schedules", tags=["Insight Schedules"])


# ─── Request / Response Schemas ───────────────────────────────────────────────


class InsightScheduleCreate(BaseModel):
    """Request body for creating an insight schedule."""

    name: str = Field(..., min_length=1, max_length=255)
    analysis_type: str = Field(
        ...,
        description="energy, behavioral, anomaly, device_health, etc.",
    )
    trigger_type: str = Field(
        ...,
        description="'cron' or 'webhook'",
        pattern="^(cron|webhook)$",
    )
    enabled: bool = True

    # Analysis params
    entity_ids: list[str] | None = None
    hours: int = Field(default=24, ge=1, le=8760)
    options: dict[str, Any] = Field(default_factory=dict)

    # Cron trigger
    cron_expression: str | None = Field(
        default=None,
        description="Cron expression, e.g. '0 2 * * *'. Required for cron triggers.",
    )

    # Webhook trigger
    webhook_event: str | None = Field(
        default=None,
        description="Event label for matching, e.g. 'device_offline'. Required for webhook triggers.",
    )
    webhook_filter: dict[str, Any] | None = Field(
        default=None,
        description="Match criteria: {entity_id, event_type, to_state, from_state}",
    )


class InsightScheduleUpdate(BaseModel):
    """Request body for updating an insight schedule (partial)."""

    name: str | None = None
    enabled: bool | None = None
    analysis_type: str | None = None
    entity_ids: list[str] | None = None
    hours: int | None = Field(default=None, ge=1, le=8760)
    options: dict[str, Any] | None = None
    cron_expression: str | None = None
    webhook_event: str | None = None
    webhook_filter: dict[str, Any] | None = None


class InsightScheduleResponse(BaseModel):
    """Response schema for an insight schedule."""

    id: str
    name: str
    enabled: bool
    analysis_type: str
    trigger_type: str
    entity_ids: list[str] | None
    hours: int
    options: dict[str, Any]
    cron_expression: str | None
    webhook_event: str | None
    webhook_filter: dict[str, Any] | None
    last_run_at: str | None
    last_result: str | None
    last_error: str | None
    run_count: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class InsightScheduleList(BaseModel):
    """Paginated list of insight schedules."""

    items: list[InsightScheduleResponse]
    total: int


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=InsightScheduleList)
async def list_schedules(
    trigger_type: str | None = None,
    enabled_only: bool = False,
) -> InsightScheduleList:
    """List all insight schedules."""
    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        schedules = await repo.list_all(
            enabled_only=enabled_only,
            trigger_type=trigger_type,
        )
        items = [
            InsightScheduleResponse(
                **_serialize(s),
            )
            for s in schedules
        ]
        return InsightScheduleList(items=items, total=len(items))


@router.post("", response_model=InsightScheduleResponse, status_code=201)
async def create_schedule(body: InsightScheduleCreate) -> InsightScheduleResponse:
    """Create a new insight schedule.

    For cron triggers, the schedule is immediately registered with APScheduler.
    """
    # Validate trigger-specific fields
    if body.trigger_type == "cron" and not body.cron_expression:
        raise HTTPException(
            status_code=400,
            detail="cron_expression is required for cron triggers",
        )
    if body.trigger_type == "webhook" and not body.webhook_event:
        raise HTTPException(
            status_code=400,
            detail="webhook_event is required for webhook triggers",
        )

    # Validate cron expression
    if body.cron_expression:
        try:
            from apscheduler.triggers.cron import CronTrigger

            CronTrigger.from_crontab(body.cron_expression)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cron expression: {e}",
            ) from e

    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        schedule = await repo.create(
            name=body.name,
            analysis_type=body.analysis_type,
            trigger_type=body.trigger_type,
            enabled=body.enabled,
            entity_ids=body.entity_ids,
            hours=body.hours,
            options=body.options,
            cron_expression=body.cron_expression,
            webhook_event=body.webhook_event,
            webhook_filter=body.webhook_filter,
        )
        await session.commit()

        # Sync APScheduler if it's a cron schedule
        if body.trigger_type == "cron":
            await _sync_scheduler()

        return InsightScheduleResponse(**_serialize(schedule))


@router.get("/{schedule_id}", response_model=InsightScheduleResponse)
async def get_schedule(schedule_id: str) -> InsightScheduleResponse:
    """Get a single insight schedule by ID."""
    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        schedule = await repo.get(schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return InsightScheduleResponse(**_serialize(schedule))


@router.put("/{schedule_id}", response_model=InsightScheduleResponse)
async def update_schedule(
    schedule_id: str,
    body: InsightScheduleUpdate,
) -> InsightScheduleResponse:
    """Update an insight schedule."""
    # Validate cron expression if provided
    if body.cron_expression:
        try:
            from apscheduler.triggers.cron import CronTrigger

            CronTrigger.from_crontab(body.cron_expression)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cron expression: {e}",
            ) from e

    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        schedule = await repo.update(schedule_id, **fields)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        await session.commit()

        # Re-sync scheduler
        await _sync_scheduler()

        return InsightScheduleResponse(**_serialize(schedule))


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str) -> None:
    """Delete an insight schedule."""
    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        deleted = await repo.delete(schedule_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Schedule not found")
        await session.commit()

    # Re-sync scheduler
    await _sync_scheduler()


@router.post("/{schedule_id}/run", response_model=dict)
async def run_schedule_now(
    schedule_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """Manually trigger a scheduled insight analysis."""
    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        schedule = await repo.get(schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

    # Import here to avoid circular imports
    from src.scheduler.service import _execute_scheduled_analysis

    background_tasks.add_task(_execute_scheduled_analysis, schedule_id)
    return {"status": "queued", "schedule_id": schedule_id}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _serialize(schedule: Any) -> dict[str, Any]:
    """Serialize an InsightSchedule to dict for the response model."""
    return {
        "id": schedule.id,
        "name": schedule.name,
        "enabled": schedule.enabled,
        "analysis_type": schedule.analysis_type,
        "trigger_type": schedule.trigger_type,
        "entity_ids": schedule.entity_ids,
        "hours": schedule.hours,
        "options": schedule.options or {},
        "cron_expression": schedule.cron_expression,
        "webhook_event": schedule.webhook_event,
        "webhook_filter": schedule.webhook_filter,
        "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        "last_result": schedule.last_result,
        "last_error": schedule.last_error,
        "run_count": schedule.run_count,
        "created_at": schedule.created_at.isoformat() if schedule.created_at else "",
        "updated_at": schedule.updated_at.isoformat() if schedule.updated_at else "",
    }


async def _sync_scheduler() -> None:
    """Sync APScheduler jobs after a DB change."""
    from src.scheduler.service import SchedulerService

    scheduler = SchedulerService.get_instance()
    if scheduler:
        await scheduler.sync_jobs()
