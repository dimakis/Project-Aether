"""APScheduler-based scheduler for periodic insight analysis jobs.

Feature 10: Scheduled & Event-Driven Insights.

Uses APScheduler 3.x with AsyncIOScheduler. Jobs are synced from
the insight_schedules DB table on startup and after any CRUD operation.
"""

from __future__ import annotations

import logging
import time

from src.settings import get_settings

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None  # type: ignore[assignment]
    CronTrigger = None  # type: ignore[assignment]
    IntervalTrigger = None  # type: ignore[assignment]
    logger.warning(
        "APScheduler not installed — scheduled insights disabled. Install with: pip install apscheduler"
    )


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
            self._scheduler = None
        self._running = False

    @classmethod
    def get_instance(cls) -> SchedulerService | None:
        """Get the singleton scheduler instance (None if not started)."""
        return cls._instance

    async def start(self) -> None:
        """Start the scheduler and load jobs from the database.

        Respects AETHER_ROLE: only starts when role is 'all' or 'scheduler'.
        This prevents duplicate job execution in multi-replica K8s deployments
        where API pods should NOT run the scheduler.
        """
        if not _APSCHEDULER_AVAILABLE or self._scheduler is None:
            logger.warning("APScheduler not available, scheduler cannot start")
            return

        settings = get_settings()

        # Role-based guard: skip scheduler in API-only pods
        if settings.aether_role == "api":
            logger.info(
                "Scheduler skipped: AETHER_ROLE=%s (only 'all' or 'scheduler' run jobs)",
                settings.aether_role,
            )
            return

        if not settings.scheduler_enabled:
            logger.info("Scheduler disabled via settings")
            return

        self._scheduler.start()
        self._running = True
        SchedulerService._instance = self

        # Sync insight schedule jobs from DB
        await self.sync_jobs()

        # Schedule periodic discovery sync
        self._schedule_discovery_sync(settings)

        # Schedule nightly trace evaluation (MLflow 3.x)
        self._schedule_trace_evaluation(settings)

        # Schedule nightly data retention cleanup
        self._schedule_data_cleanup(settings)

        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._running and self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._running = False
            SchedulerService._instance = None
            logger.info("Scheduler stopped")

    def _schedule_trace_evaluation(self, settings: object) -> None:
        """Register a nightly trace evaluation job if enabled.

        Uses MLflow 3.x GenAI scorers to evaluate recent agent traces,
        creating a continuous quality feedback loop.
        """
        if self._scheduler is None or CronTrigger is None:
            return

        if not getattr(settings, "trace_eval_enabled", True):
            logger.info("Trace evaluation disabled via settings")
            return

        cron_expr = getattr(settings, "trace_eval_cron", "0 2 * * *")

        try:
            trigger = CronTrigger.from_crontab(
                cron_expr,
                timezone=getattr(settings, "scheduler_timezone", "UTC"),
            )
        except ValueError:
            logger.error("Invalid cron expression for trace evaluation: %s", cron_expr)
            return

        self._scheduler.add_job(
            _execute_trace_evaluation,
            trigger=trigger,
            id="trace_eval:nightly",
            replace_existing=True,
            name="trace_eval:nightly_scorer_run",
            misfire_grace_time=600,  # 10 min grace for misfires
        )
        logger.info("Nightly trace evaluation scheduled: %s", cron_expr)

    def _schedule_data_cleanup(self, settings: object) -> None:
        """Register a nightly data retention cleanup job."""
        if self._scheduler is None or CronTrigger is None:
            return

        self._scheduler.add_job(
            _execute_data_cleanup,
            trigger=CronTrigger(hour=3, minute=30),
            id="retention:nightly_cleanup",
            replace_existing=True,
            name="retention:nightly_data_cleanup",
            misfire_grace_time=600,
        )
        logger.info("Nightly data retention cleanup scheduled at 03:30")

    def _schedule_discovery_sync(self, settings: object) -> None:
        """Register a periodic delta sync job if enabled.

        Uses an IntervalTrigger so the first run happens after one interval,
        and subsequent runs repeat at the configured frequency.

        When the real-time event stream (Feature 35) is active, entity states
        are kept current via WebSocket push.  The polling sync then only needs
        to catch structural changes (new/removed entities), so we widen the
        interval to 360 min (6 h) to reduce redundant DB churn.
        """
        if self._scheduler is None or IntervalTrigger is None:
            return

        if not getattr(settings, "discovery_sync_enabled", False):
            logger.info("Discovery periodic sync disabled via settings")
            return

        interval = getattr(settings, "discovery_sync_interval_minutes", 30)

        # When the event stream (Feature 35) is active, entity state updates
        # arrive in real-time via WebSocket push. The polling sync only needs
        # to catch structural changes (new/removed entities), so we widen the
        # interval to 6 h to reduce redundant DB churn.
        event_stream_available = False
        try:
            import importlib.util

            event_stream_available = importlib.util.find_spec("src.ha.event_stream") is not None
        except (ImportError, ValueError):
            pass

        if event_stream_available:
            event_stream_interval = 360  # 6 hours in minutes
            if interval < event_stream_interval:
                logger.info(
                    "Event stream active — widening discovery sync from %d to %d minutes",
                    interval,
                    event_stream_interval,
                )
                interval = event_stream_interval

        self._scheduler.add_job(
            _execute_discovery_sync,
            trigger=IntervalTrigger(minutes=interval),
            id="discovery:periodic_sync",
            replace_existing=True,
            name="discovery:periodic_delta_sync",
            misfire_grace_time=300,
        )
        logger.info(
            "Discovery periodic sync scheduled every %d minutes",
            interval,
        )

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
    from src.jobs import emit_job_agent, emit_job_complete, emit_job_failed, emit_job_start
    from src.storage import get_session

    logger.info("Executing scheduled analysis: %s", schedule_id)

    async with get_session() as session:
        repo = InsightScheduleRepository(session)
        schedule = await repo.get(schedule_id)

        if not schedule or not schedule.enabled:
            logger.warning("Schedule %s not found or disabled, skipping", schedule_id)
            return

        job_id = f"schedule:{schedule_id}:{int(time.time())}"
        emit_job_start(job_id, "schedule", schedule.name)

        try:
            custom_query = None
            if schedule.options:
                import json

                custom_query = f"Scheduled analysis options: {json.dumps(schedule.options)}"

            emit_job_agent(job_id, "data_scientist", "start")
            await run_analysis_workflow(
                analysis_type=schedule.analysis_type,
                entity_ids=schedule.entity_ids,
                hours=schedule.hours,
                custom_query=custom_query,
            )
            emit_job_agent(job_id, "data_scientist", "end")

            schedule.record_run(success=True)
            logger.info(
                "Scheduled analysis %s completed successfully (run #%d)",
                schedule.name,
                schedule.run_count,
            )
            emit_job_complete(job_id)

            # Feature 37: notify user of actionable insights from this run
            try:
                from src.dal.insights import InsightRepository
                from src.hitl.insight_notifier import InsightNotifier

                notifier = await InsightNotifier.from_settings()
                insight_repo = InsightRepository(session)
                recent_insights = await insight_repo.list_recent(hours=1)
                sent = await notifier.notify_if_actionable(recent_insights)
                if sent:
                    logger.info(
                        "Sent %d insight notification(s) for schedule %s", sent, schedule.name
                    )
            except Exception as exc:
                logger.warning(
                    "Insight notification failed for schedule %s: %s", schedule.name, exc
                )
        except Exception as e:
            schedule.record_run(success=False, error=str(e))
            logger.exception(
                "Scheduled analysis %s failed: %s",
                schedule.name,
                e,
            )
            emit_job_failed(job_id, str(e))

        await session.commit()


async def _execute_trace_evaluation() -> None:
    """Execute nightly trace evaluation using MLflow 3.x GenAI scorers.

    Called by APScheduler. Searches recent traces and runs all
    custom scorers, logging results back to MLflow.
    """
    from src.jobs import emit_job_complete, emit_job_failed, emit_job_start, emit_job_status

    job_id = f"evaluation:{int(time.time())}"
    emit_job_start(job_id, "evaluation", "Nightly trace evaluation")
    logger.info("Starting nightly trace evaluation")

    try:
        import mlflow
        import mlflow.genai

        from src.settings import get_settings
        from src.tracing import init_mlflow
        from src.tracing.scorers import get_all_scorers

        client = init_mlflow()
        if client is None:
            logger.warning("MLflow not available, skipping trace evaluation")
            emit_job_failed(job_id, "MLflow not available")
            return

        settings = get_settings()
        scorers = get_all_scorers()
        if not scorers:
            logger.warning("No scorers available, skipping trace evaluation")
            emit_job_failed(job_id, "No scorers available")
            return

        trace_df = mlflow.search_traces(
            experiment_names=[settings.mlflow_experiment_name],
            max_results=settings.trace_eval_max_traces,
        )

        if trace_df is None or len(trace_df) == 0:
            logger.info("No traces found for evaluation")
            emit_job_complete(job_id)
            return

        emit_job_status(job_id, f"Evaluating {len(trace_df)} traces with {len(scorers)} scorers")

        eval_result = mlflow.genai.evaluate(
            data=trace_df,
            scorers=scorers,
        )

        run_id = getattr(eval_result, "run_id", "unknown")
        logger.info(
            "Nightly trace evaluation complete: run_id=%s, traces=%d",
            run_id,
            len(trace_df),
        )
        emit_job_complete(job_id)

    except Exception as e:
        logger.exception("Nightly trace evaluation failed: %s", e)
        emit_job_failed(job_id, str(e))


async def _execute_discovery_sync() -> None:
    """Execute a periodic delta discovery sync.

    Called by APScheduler at the configured interval.
    Runs run_delta_sync which only upserts changed entities.
    """
    from src.dal.sync import DiscoverySyncService
    from src.ha import get_ha_client
    from src.storage import get_session

    logger.info("Starting periodic discovery delta sync")

    try:
        async with get_session() as session:
            ha_client = get_ha_client()
            service = DiscoverySyncService(session, ha_client)
            stats = await service.run_delta_sync()

        logger.info(
            "Periodic discovery sync complete: added=%s, updated=%s, "
            "skipped=%s, removed=%s, duration=%.1fs",
            stats.get("added", 0),
            stats.get("updated", 0),
            stats.get("skipped", 0),
            stats.get("removed", 0),
            stats.get("duration_seconds", 0),
        )
    except Exception as e:
        logger.exception("Periodic discovery sync failed: %s", e)


async def _execute_data_cleanup() -> None:
    """Delete old records from unbounded tables based on retention settings.

    Runs nightly to prevent database bloat from llm_usage, messages,
    analysis_reports, and dismissed/actioned insights.
    """
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import delete

    from src.settings import get_settings
    from src.storage import get_session

    settings = get_settings()
    logger.info("Starting nightly data retention cleanup")

    try:
        async with get_session() as session:
            total_deleted = 0

            # LLM usage (high-volume)
            llm_cutoff = datetime.now(UTC) - timedelta(days=settings.llm_usage_retention_days)
            from src.storage.entities.llm_usage import LLMUsage

            result = await session.execute(delete(LLMUsage).where(LLMUsage.created_at < llm_cutoff))
            llm_count = result.rowcount or 0
            total_deleted += llm_count

            # Analysis reports
            report_cutoff = datetime.now(UTC) - timedelta(days=settings.data_retention_days)
            from src.storage.entities.analysis_report import AnalysisReport

            result = await session.execute(
                delete(AnalysisReport).where(AnalysisReport.created_at < report_cutoff)
            )
            report_count = result.rowcount or 0
            total_deleted += report_count

            # Dismissed/actioned insights
            from src.storage.entities.insight import Insight

            result = await session.execute(
                delete(Insight).where(
                    Insight.created_at < report_cutoff,
                    Insight.status.in_(["dismissed", "actioned"]),
                )
            )
            insight_count = result.rowcount or 0
            total_deleted += insight_count

            await session.commit()

            logger.info(
                "Data retention cleanup complete: llm_usage=%d, reports=%d, insights=%d, total=%d",
                llm_count,
                report_count,
                insight_count,
                total_deleted,
            )

    except Exception as e:
        logger.exception("Data retention cleanup failed: %s", e)
