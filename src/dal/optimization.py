"""Optimization job and suggestion repositories.

Feature 38: Optimization Persistence.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from sqlalchemy import CursorResult, select, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities.automation_suggestion import (
    AutomationSuggestionEntity,
    SuggestionStatus,
)
from src.storage.entities.optimization_job import JobStatus, OptimizationJob

logger = logging.getLogger(__name__)


class OptimizationJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict[str, Any]) -> OptimizationJob:
        job = OptimizationJob(id=str(uuid4()), **data)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: str) -> OptimizationJob | None:
        result = await self.session.execute(
            select(OptimizationJob).where(OptimizationJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, status: str | None = None, limit: int = 50) -> list[OptimizationJob]:
        query = select(OptimizationJob).order_by(OptimizationJob.created_at.desc()).limit(limit)
        if status:
            query = query.where(OptimizationJob.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(self, job_id: str, status: str, **kwargs: Any) -> None:
        values: dict[str, Any] = {"status": status, **kwargs}
        await self.session.execute(
            update(OptimizationJob).where(OptimizationJob.id == job_id).values(**values)
        )

    async def reconcile_stale_jobs(self) -> int:
        """Mark jobs stuck in 'running' state as failed (e.g., after server restart)."""
        result = await self.session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.status == JobStatus.RUNNING.value)
            .values(
                status=JobStatus.FAILED.value,
                error="Server restarted during execution",
                completed_at=datetime.now(UTC),
            )
        )
        count = cast("CursorResult[Any]", result).rowcount
        if count:
            logger.info("Reconciled %d stale optimization jobs", count)
        return count


class AutomationSuggestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict[str, Any]) -> AutomationSuggestionEntity:
        entity = AutomationSuggestionEntity(id=str(uuid4()), **data)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def list_all(
        self,
        status: str | None = None,
        job_id: str | None = None,
    ) -> list[AutomationSuggestionEntity]:
        query = select(AutomationSuggestionEntity).order_by(
            AutomationSuggestionEntity.created_at.desc()
        )
        if status:
            query = query.where(AutomationSuggestionEntity.status == status)
        if job_id:
            query = query.where(AutomationSuggestionEntity.job_id == job_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, suggestion_id: str) -> AutomationSuggestionEntity | None:
        result = await self.session.execute(
            select(AutomationSuggestionEntity).where(AutomationSuggestionEntity.id == suggestion_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, suggestion_id: str, status: str) -> bool:
        result = await self.session.execute(
            update(AutomationSuggestionEntity)
            .where(AutomationSuggestionEntity.id == suggestion_id)
            .values(status=status)
        )
        return cast("CursorResult[Any]", result).rowcount > 0


# Suppress false-positive: these enums are re-exported for consumers
__all__ = [
    "AutomationSuggestionRepository",
    "JobStatus",
    "OptimizationJobRepository",
    "SuggestionStatus",
]
