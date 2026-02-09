"""Repository for InsightSchedule CRUD operations.

Feature 10: Scheduled & Event-Driven Insights.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities.insight_schedule import InsightSchedule


class InsightScheduleRepository:
    """Repository for InsightSchedule CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        analysis_type: str,
        trigger_type: str,
        hours: int = 24,
        entity_ids: list[str] | None = None,
        options: dict[str, Any] | None = None,
        cron_expression: str | None = None,
        webhook_event: str | None = None,
        webhook_filter: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> InsightSchedule:
        """Create a new insight schedule."""
        schedule = InsightSchedule(
            id=str(uuid4()),
            name=name,
            enabled=enabled,
            analysis_type=analysis_type,
            entity_ids=entity_ids,
            hours=hours,
            options=options or {},
            trigger_type=trigger_type,
            cron_expression=cron_expression,
            webhook_event=webhook_event,
            webhook_filter=webhook_filter,
        )
        self.session.add(schedule)
        await self.session.flush()
        return schedule

    async def get(self, schedule_id: str) -> InsightSchedule | None:
        """Get a schedule by ID."""
        return await self.session.get(InsightSchedule, schedule_id)

    async def list_all(
        self,
        enabled_only: bool = False,
        trigger_type: str | None = None,
    ) -> list[InsightSchedule]:
        """List schedules with optional filtering."""
        stmt = select(InsightSchedule).order_by(InsightSchedule.created_at.desc())
        if enabled_only:
            stmt = stmt.where(InsightSchedule.enabled == True)  # noqa: E712
        if trigger_type:
            stmt = stmt.where(InsightSchedule.trigger_type == trigger_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_webhook_triggers(
        self,
        webhook_event: str | None = None,
    ) -> list[InsightSchedule]:
        """List enabled webhook triggers, optionally filtered by event name."""
        stmt = (
            select(InsightSchedule)
            .where(InsightSchedule.enabled == True)  # noqa: E712
            .where(InsightSchedule.trigger_type == "webhook")
        )
        if webhook_event:
            stmt = stmt.where(InsightSchedule.webhook_event == webhook_event)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_cron_schedules(self) -> list[InsightSchedule]:
        """List all enabled cron schedules."""
        stmt = (
            select(InsightSchedule)
            .where(InsightSchedule.enabled == True)  # noqa: E712
            .where(InsightSchedule.trigger_type == "cron")
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        schedule_id: str,
        **fields: Any,
    ) -> InsightSchedule | None:
        """Update a schedule's fields."""
        schedule = await self.get(schedule_id)
        if not schedule:
            return None
        for key, value in fields.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        schedule.updated_at = datetime.now(UTC)
        await self.session.flush()
        return schedule

    async def delete(self, schedule_id: str) -> bool:
        """Delete a schedule. Returns True if found and deleted."""
        schedule = await self.get(schedule_id)
        if not schedule:
            return False
        await self.session.delete(schedule)
        await self.session.flush()
        return True

    async def record_run(
        self,
        schedule_id: str,
        success: bool,
        error: str | None = None,
    ) -> InsightSchedule | None:
        """Record the result of a schedule execution."""
        schedule = await self.get(schedule_id)
        if not schedule:
            return None
        schedule.record_run(success=success, error=error)
        await self.session.flush()
        return schedule
