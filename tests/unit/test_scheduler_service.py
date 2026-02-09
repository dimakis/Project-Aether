"""Unit tests for SchedulerService.

All inline imports (InsightScheduleRepository, get_session, etc.) are
patched at their SOURCE modules, not at src.scheduler.service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scheduler.service import SchedulerService


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton between tests."""
    SchedulerService._instance = None
    yield
    SchedulerService._instance = None


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.scheduler_timezone = "UTC"
    s.scheduler_enabled = True
    s.aether_role = "all"
    s.discovery_sync_enabled = False
    s.trace_eval_enabled = False
    return s


class TestSchedulerInit:
    """Tests for SchedulerService initialization."""

    def test_init_with_apscheduler(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        assert svc._scheduler is not None
        assert svc._running is False

    def test_get_instance_none_before_start(self):
        assert SchedulerService.get_instance() is None


class TestSchedulerStart:
    """Tests for SchedulerService.start."""

    async def test_start_when_role_api_skips(self, mock_settings):
        mock_settings.aether_role = "api"
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
            await svc.start()
        assert svc._running is False

    async def test_start_when_disabled_skips(self, mock_settings):
        mock_settings.scheduler_enabled = False
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
            await svc.start()
        assert svc._running is False

    async def test_start_success(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()

        # Mock the scheduler internals
        svc._scheduler = MagicMock()
        svc._scheduler.start = MagicMock()
        svc._scheduler.get_jobs = MagicMock(return_value=[])

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_repo = MagicMock()
        mock_repo.list_cron_schedules = AsyncMock(return_value=[])

        with (
            patch("src.scheduler.service.get_settings", return_value=mock_settings),
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
        ):
            await svc.start()

        assert svc._running is True
        assert SchedulerService.get_instance() is svc


class TestSchedulerStop:
    """Tests for SchedulerService.stop."""

    async def test_stop_running(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._running = True
        svc._scheduler = MagicMock()
        SchedulerService._instance = svc

        await svc.stop()

        assert svc._running is False
        assert SchedulerService._instance is None
        svc._scheduler.shutdown.assert_called_once_with(wait=False)

    async def test_stop_not_running(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        await svc.stop()  # Should not raise


class TestSchedulerSyncJobs:
    """Tests for SchedulerService.sync_jobs."""

    async def test_sync_jobs_no_scheduler(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._scheduler = None
        await svc.sync_jobs()  # Should return early without error

    async def test_sync_jobs_with_schedules(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()

        mock_schedule = MagicMock()
        mock_schedule.id = "sched-1"
        mock_schedule.name = "Test Schedule"
        mock_schedule.cron_expression = "0 0 * * *"

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_repo = MagicMock()
        mock_repo.list_cron_schedules = AsyncMock(return_value=[mock_schedule])

        svc._scheduler = MagicMock()
        svc._scheduler.get_job = MagicMock(return_value=None)
        svc._scheduler.get_jobs = MagicMock(return_value=[])

        with (
            patch("src.scheduler.service.get_settings", return_value=mock_settings),
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
        ):
            await svc.sync_jobs()

        svc._scheduler.add_job.assert_called_once()

    async def test_sync_jobs_removes_stale(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_repo = MagicMock()
        mock_repo.list_cron_schedules = AsyncMock(return_value=[])  # no DB schedules

        stale_job = MagicMock()
        stale_job.id = "insight_schedule:old-one"

        svc._scheduler = MagicMock()
        svc._scheduler.get_jobs = MagicMock(return_value=[stale_job])

        with (
            patch("src.scheduler.service.get_settings", return_value=mock_settings),
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
        ):
            await svc.sync_jobs()

        stale_job.remove.assert_called_once()

    async def test_sync_jobs_handles_db_error(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()

        svc._scheduler = MagicMock()

        with patch(
            "src.storage.get_session",
            side_effect=Exception("DB unavailable"),
        ):
            await svc.sync_jobs()  # Should not raise


class TestScheduleDiscoverySync:
    """Tests for _schedule_discovery_sync."""

    def test_no_scheduler(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._scheduler = None
        svc._schedule_discovery_sync(mock_settings)  # Should not raise

    def test_disabled(self, mock_settings):
        mock_settings.discovery_sync_enabled = False
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._scheduler = MagicMock()
        svc._schedule_discovery_sync(mock_settings)
        svc._scheduler.add_job.assert_not_called()

    def test_enabled(self, mock_settings):
        mock_settings.discovery_sync_enabled = True
        mock_settings.discovery_sync_interval_minutes = 15
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._scheduler = MagicMock()
        svc._schedule_discovery_sync(mock_settings)
        svc._scheduler.add_job.assert_called_once()


class TestScheduleTraceEvaluation:
    """Tests for _schedule_trace_evaluation."""

    def test_no_scheduler(self, mock_settings):
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._scheduler = None
        svc._schedule_trace_evaluation(mock_settings)

    def test_disabled(self, mock_settings):
        mock_settings.trace_eval_enabled = False
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._scheduler = MagicMock()
        svc._schedule_trace_evaluation(mock_settings)
        svc._scheduler.add_job.assert_not_called()

    def test_enabled(self, mock_settings):
        mock_settings.trace_eval_enabled = True
        mock_settings.trace_eval_cron = "0 2 * * *"
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._scheduler = MagicMock()
        svc._schedule_trace_evaluation(mock_settings)
        svc._scheduler.add_job.assert_called_once()

    def test_invalid_cron(self, mock_settings):
        mock_settings.trace_eval_enabled = True
        mock_settings.trace_eval_cron = "invalid cron"
        with patch("src.scheduler.service.get_settings", return_value=mock_settings):
            svc = SchedulerService()
        svc._scheduler = MagicMock()
        # CronTrigger.from_crontab raises ValueError for invalid cron
        svc._schedule_trace_evaluation(mock_settings)
        svc._scheduler.add_job.assert_not_called()


class TestExecuteScheduledAnalysis:
    """Tests for _execute_scheduled_analysis standalone function."""

    async def test_execute_success(self):
        from src.scheduler.service import _execute_scheduled_analysis

        mock_schedule = MagicMock()
        mock_schedule.id = "sched-1"
        mock_schedule.enabled = True
        mock_schedule.analysis_type = "energy"
        mock_schedule.entity_ids = []
        mock_schedule.hours = 24
        mock_schedule.options = None
        mock_schedule.name = "Test"
        mock_schedule.run_count = 0

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.get = AsyncMock(return_value=mock_schedule)

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
            patch("src.graph.workflows.run_analysis_workflow", new_callable=AsyncMock),
        ):
            await _execute_scheduled_analysis("sched-1")

        mock_schedule.record_run.assert_called_once_with(success=True)

    async def test_execute_disabled_schedule(self):
        from src.scheduler.service import _execute_scheduled_analysis

        mock_schedule = MagicMock()
        mock_schedule.enabled = False

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.get = AsyncMock(return_value=mock_schedule)

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
        ):
            await _execute_scheduled_analysis("sched-1")

        mock_schedule.record_run.assert_not_called()

    async def test_execute_not_found(self):
        from src.scheduler.service import _execute_scheduled_analysis

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_repo = MagicMock()
        mock_repo.get = AsyncMock(return_value=None)

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
        ):
            await _execute_scheduled_analysis("sched-missing")
        # Should return early, no error


class TestExecuteDiscoverySync:
    """Tests for _execute_discovery_sync standalone function."""

    async def test_execute_success(self):
        from src.scheduler.service import _execute_discovery_sync

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_ha_client = MagicMock()
        mock_service = MagicMock()
        mock_service.run_delta_sync = AsyncMock(
            return_value={
                "added": 3,
                "updated": 1,
                "skipped": 10,
                "removed": 0,
                "duration_seconds": 2.5,
            }
        )

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.ha.get_ha_client", return_value=mock_ha_client),
            patch("src.dal.sync.DiscoverySyncService", return_value=mock_service),
        ):
            await _execute_discovery_sync()

        mock_service.run_delta_sync.assert_called_once()

    async def test_execute_handles_error(self):
        from src.scheduler.service import _execute_discovery_sync

        with patch(
            "src.storage.get_session",
            side_effect=Exception("DB down"),
        ):
            await _execute_discovery_sync()  # Should not raise
