"""APScheduler-based scheduler for periodic insight analysis jobs.

Feature 10: Scheduled & Event-Driven Insights.

Uses APScheduler 3.x with AsyncIOScheduler. Jobs are synced from
the insight_schedules DB table on startup and after any CRUD operation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.settings import get_settings

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None  # type: ignore[assignment, misc]
    CronTrigger = None  # type: ignore[assignment, misc]
    logger.warning("APScheduler not installed — scheduled insights disabled. Install with: pip install apscheduler")

class SchedulerService:
    """Manages cron-based insight schedules via APScheduler.

    Lifecycle:
        scheduler = SchedulerService()
        await scheduler.start()    # Called in lifespan startup
        ...
        await scheduler.stop()     # Called in lifespan shutdown

    Job sync:
        After creating/updating/deleting a schedule via the API,
        call scheduler.sync_jobs() to reconcile APScheduler with the DB.
    """

    _instance: SchedulerService | None = None

    def __init__(self) -> None:
        settings = get_settings()
        if _APSCHEDULER_AVAILABLE and AsyncIOScheduler is not None:
            self._scheduler = AsyncIOScheduler(
                timezone=settings.scheduler_timezone,
            )
        else:
            self._scheduler = None  # type: ignore[assignment]
        self._running = False

    @classmethod
    def get_instance(cls) -> SchedulerService | None:
        """Get the singleton scheduler instance (None if not started)."""
        return cls._instance

    async def start(self) -> None:
        """Start the scheduler and load jobs from the database."""
        if not _APSCHEDULER_AVAILABLE or self._scheduler is None:
            logger.warning("APScheduler not available, scheduler cannot start")
            return

        settings = get_settings()
        if not settings.scheduler_enabled:
            logger.info("Scheduler disabled via settings")
            return

        self._scheduler.start()
        self._running = True
        SchedulerService._instance = self

        # Sync jobs from DB
        await self.sync_jobs()
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._running and self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._running = False
            SchedulerService._instance = None
            logger.info("Scheduler stopped")

    async def sync_jobs(self) -> None:
        """Sync APScheduler jobs with the insight_schedules DB table.

        Loads all enabled cron schedules and ensures APScheduler has
        a matching job for each. Removes stale jobs that are no longer
        in the DB or have been disabled.
        """
        if self._scheduler is None:
            return

        from src.dal.insight_schedules import InsightScheduleRepository
        from src.storage import get_session

        try:
            async with get_session() as session:
                repo = InsightScheduleRepository(session)
                schedules = await repo.list_cron_schedules()
        except Exception as e:
            # Table may not exist yet (migration not run)
            logger.warning("Could not load insight schedules: %s", e)
            return

        # Build set of expected job IDs
        expected_ids = set()

        for schedule in schedules:
            job_id = f"insight_schedule:{schedule.id}"
            expected_ids.add(job_id)

            try:
                trigger = CronTrigger.from_crontab(
                    schedule.cron_expression or "0 0 * * *",
                    timezone=get_settings().scheduler_timezone,
                )
            except ValueError:
                logger.error(
                    "Invalid cron expression for schedule %s: %s",
                    schedule.id,
                    schedule.cron_expression,
                )
                continue

            # Add or replace the job
            existing = self._scheduler.get_job(job_id)
            if existing:
                existing.reschedule(trigger)
                logger.debug("Updated schedule job %s", job_id)
            else:
                self._scheduler.add_job(
                    _execute_scheduled_analysis,
                    trigger=trigger,
                    id=job_id,
                    args=[schedule.id],
                    replace_existing=True,
                    name=f"insight:{schedule.name}",
                    misfire_grace_time=300,  # 5 min grace for misfires
                )
                logger.info("Added schedule job %s (%s)", job_id, schedule.cron_expression)

        # Remove jobs that are no longer in the DB
        for job in self._scheduler.get_jobs():
            if job.id.startswith("insight_schedule:") and job.id not in expected_ids:
                job.remove()
                logger.info("Removed stale schedule job %s", job.id)


async def _execute_scheduled_analysis(schedule_id: str) -> None:
    """Execute a scheduled insight analysis job.

    Called by APScheduler when a cron job fires.
    Runs the same analysis pipeline as POST /insights/analyze.
    """
    from src.dal.insight_schedules import InsightScheduleRepository
    from src.graph.workflows import run_analysis_workflow
    from src.storage import get_session

    logger.info("Executing scheduled analysis: %s", schedule_id)

    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        schedule = await repo.get(schedule_id)

        if not schedule or not schedule.enabled:
            logger.warning("Schedule %s not found or disabled, skipping", schedule_id)
            return

        try:
            # Run the analysis workflow
            # Options are passed via custom_query as a context hint
            custom_query = None
            if schedule.options:
                import json

                custom_query = f"Scheduled analysis options: {json.dumps(schedule.options)}"

            await run_analysis_workflow(
                analysis_type=schedule.analysis_type,
                entity_ids=schedule.entity_ids,
                hours=schedule.hours,
                custom_query=custom_query,
            )

            # Record success
            schedule.record_run(success=True)
            logger.info(
                "Scheduled analysis %s completed successfully (run #%d)",
                schedule.name,
                schedule.run_count,
            )
        except Exception as e:
            # Record failure
            schedule.record_run(success=False, error=str(e))
            logger.exception(
                "Scheduled analysis %s failed: %s",
                schedule.name,
                e,
            )

        await session.commit()
