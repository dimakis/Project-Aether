"""Unit tests for insight schedule tools module.

Tests create_insight_schedule tool with mocked dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_schedule():
    """Create a mock insight schedule."""
    schedule = MagicMock()
    schedule.id = "test-schedule-id-12345"
    schedule.name = "Test Schedule"
    schedule.analysis_type = "energy_optimization"
    schedule.trigger_type = "cron"
    schedule.cron_expression = "0 2 * * *"
    schedule.hours = 24
    schedule.entity_ids = None
    schedule.enabled = True
    return schedule


class TestCreateInsightSchedule:
    """Tests for create_insight_schedule tool."""

    @pytest.mark.asyncio
    async def test_create_cron_schedule_success(self, mock_schedule):
        """Test successful cron schedule creation."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_schedule)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_scheduler = MagicMock()
        mock_scheduler.sync_jobs = AsyncMock()

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.scheduler.service.SchedulerService.get_instance",
                return_value=mock_scheduler,
            ),
            patch("apscheduler.triggers.cron.CronTrigger"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Daily Energy Report",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "cron",
                    "cron_expression": "0 2 * * *",
                    "hours": 24,
                }
            )

        assert "Daily Energy Report" in result
        assert "Energy Optimization" in result
        assert "Cron: `0 2 * * *`" in result
        assert "24 hours" in result
        assert "test-sch" in result.lower()  # ID is truncated in formatted output
        assert "active" in result.lower()
        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["name"] == "Daily Energy Report"
        assert call_kwargs["analysis_type"] == "energy_optimization"
        assert call_kwargs["trigger_type"] == "cron"
        assert call_kwargs["cron_expression"] == "0 2 * * *"
        assert call_kwargs["hours"] == 24
        assert call_kwargs["enabled"] is True
        mock_session.commit.assert_called_once()
        mock_scheduler.sync_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_webhook_schedule_success(self, mock_schedule):
        """Test successful webhook schedule creation."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        mock_schedule.trigger_type = "webhook"
        mock_schedule.webhook_event = "device_offline"

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_schedule)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.scheduler.service.SchedulerService.get_instance",
                return_value=None,
            ),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Device Offline Analysis",
                    "analysis_type": "anomaly_detection",
                    "trigger_type": "webhook",
                    "webhook_event": "device_offline",
                    "hours": 48,
                }
            )

        assert "Device Offline Analysis" in result
        assert "Anomaly Detection" in result
        assert "Webhook: `device_offline`" in result
        assert "48 hours" in result
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["trigger_type"] == "webhook"
        assert call_kwargs["webhook_event"] == "device_offline"

    @pytest.mark.asyncio
    async def test_create_schedule_with_entity_ids(self, mock_schedule):
        """Test schedule creation with entity IDs."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        mock_schedule.entity_ids = ["sensor.energy", "sensor.power"]

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_schedule)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.scheduler.service.SchedulerService.get_instance",
                return_value=None,
            ),
            patch("apscheduler.triggers.cron.CronTrigger"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Energy Analysis",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "cron",
                    "cron_expression": "0 8 * * *",
                    "entity_ids": ["sensor.energy", "sensor.power"],
                }
            )

        assert "sensor.energy" in result
        assert "sensor.power" in result
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["entity_ids"] == ["sensor.energy", "sensor.power"]

    @pytest.mark.asyncio
    async def test_create_schedule_with_custom_prompt(self, mock_schedule):
        """Test schedule creation with custom prompt."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_schedule)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.scheduler.service.SchedulerService.get_instance",
                return_value=None,
            ),
            patch("apscheduler.triggers.cron.CronTrigger"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Custom Analysis",
                    "analysis_type": "custom",
                    "trigger_type": "cron",
                    "cron_expression": "0 0 * * *",
                    "custom_prompt": "Analyze HVAC efficiency",
                }
            )

        assert "HVAC efficiency" in result  # Custom prompt referenced in output
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["options"]["custom_query"] == "Analyze HVAC efficiency"

    @pytest.mark.asyncio
    async def test_invalid_analysis_type(self):
        """Test validation of analysis_type."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        with (
            patch("src.storage.get_session"),
            patch("src.dal.insight_schedules.InsightScheduleRepository"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "invalid_type",
                    "trigger_type": "cron",
                    "cron_expression": "0 0 * * *",
                }
            )

        assert "Invalid analysis_type" in result
        assert "invalid_type" in result

    @pytest.mark.asyncio
    async def test_invalid_trigger_type(self):
        """Test validation of trigger_type."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        with (
            patch("src.storage.get_session"),
            patch("src.dal.insight_schedules.InsightScheduleRepository"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "invalid",
                    "cron_expression": "0 0 * * *",
                }
            )

        assert "Invalid trigger_type" in result
        assert "invalid" in result

    @pytest.mark.asyncio
    async def test_missing_cron_expression(self):
        """Test validation when cron_expression is missing."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        with (
            patch("src.storage.get_session"),
            patch("src.dal.insight_schedules.InsightScheduleRepository"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "cron",
                }
            )

        assert "cron_expression is required" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_webhook_event(self):
        """Test validation when webhook_event is missing."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        with (
            patch("src.storage.get_session"),
            patch("src.dal.insight_schedules.InsightScheduleRepository"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "webhook",
                }
            )

        assert "webhook_event" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_cron_expression(self):
        """Test validation of cron expression syntax."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        with (
            patch("src.storage.get_session"),
            patch("src.dal.insight_schedules.InsightScheduleRepository"),
            patch("apscheduler.triggers.cron.CronTrigger") as mock_cron,
        ):
            mock_cron.from_crontab.side_effect = ValueError("Invalid cron expression")

            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "cron",
                    "cron_expression": "invalid cron",
                }
            )

        assert "Invalid cron expression" in result
        assert "invalid cron" in result

    @pytest.mark.asyncio
    async def test_custom_analysis_missing_prompt(self):
        """Test validation when custom analysis lacks prompt."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        with (
            patch("src.storage.get_session"),
            patch("src.dal.insight_schedules.InsightScheduleRepository"),
            patch("apscheduler.triggers.cron.CronTrigger"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "custom",
                    "trigger_type": "cron",
                    "cron_expression": "0 0 * * *",
                }
            )

        assert "custom_prompt is required" in result.lower()

    @pytest.mark.asyncio
    async def test_hours_capped(self, mock_schedule):
        """Test that hours are capped to reasonable limits."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_schedule)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.scheduler.service.SchedulerService.get_instance",
                return_value=None,
            ),
            patch("apscheduler.triggers.cron.CronTrigger"),
        ):
            # Test max cap (8760 hours)
            await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "cron",
                    "cron_expression": "0 0 * * *",
                    "hours": 10000,  # Should be capped to 8760
                }
            )
            call_kwargs = mock_repo.create.call_args[1]
            assert call_kwargs["hours"] == 8760

            # Test min cap (1 hour)
            await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "cron",
                    "cron_expression": "0 0 * * *",
                    "hours": 0,  # Should be capped to 1
                }
            )
            call_kwargs = mock_repo.create.call_args[1]
            assert call_kwargs["hours"] == 1

    @pytest.mark.asyncio
    async def test_scheduler_sync_skipped_when_not_running(self, mock_schedule):
        """Test that scheduler sync is skipped gracefully when scheduler not running."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_schedule)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.scheduler.service.SchedulerService.get_instance",
                return_value=None,  # Scheduler not running
            ),
            patch("apscheduler.triggers.cron.CronTrigger"),
        ):
            # Should not raise exception
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "cron",
                    "cron_expression": "0 0 * * *",
                }
            )

        assert "Test" in result

    @pytest.mark.asyncio
    async def test_create_schedule_error_handling(self, mock_schedule):
        """Test error handling during schedule creation."""
        from src.tools.insight_schedule_tools import create_insight_schedule

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(side_effect=Exception("Database error"))

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_repo,
            ),
            patch("apscheduler.triggers.cron.CronTrigger"),
        ):
            result = await create_insight_schedule.ainvoke(
                {
                    "name": "Test",
                    "analysis_type": "energy_optimization",
                    "trigger_type": "cron",
                    "cron_expression": "0 0 * * *",
                }
            )

        assert "Failed to create" in result
        assert "Database error" in result

    @pytest.mark.asyncio
    async def test_all_valid_analysis_types(self, mock_schedule):
        """Test that all valid analysis types are accepted."""
        from src.tools.insight_schedule_tools import VALID_ANALYSIS_TYPES, create_insight_schedule

        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_schedule)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        for analysis_type in VALID_ANALYSIS_TYPES:
            invoke_args = {
                "name": f"Test {analysis_type}",
                "analysis_type": analysis_type,
                "trigger_type": "cron",
                "cron_expression": "0 0 * * *",
            }
            # Custom type requires a custom_prompt
            if analysis_type == "custom":
                invoke_args["custom_prompt"] = "Analyze test data"

            with (
                patch("src.storage.get_session", return_value=mock_session),
                patch(
                    "src.dal.insight_schedules.InsightScheduleRepository",
                    return_value=mock_repo,
                ),
                patch(
                    "src.scheduler.service.SchedulerService.get_instance",
                    return_value=None,
                ),
                patch("apscheduler.triggers.cron.CronTrigger"),
            ):
                result = await create_insight_schedule.ainvoke(invoke_args)

                assert "Test" in result or "test" in result.lower()
                call_kwargs = mock_repo.create.call_args[1]
                assert call_kwargs["analysis_type"] == analysis_type


class TestGetInsightScheduleTools:
    """Tests for get_insight_schedule_tools."""

    def test_get_insight_schedule_tools_returns_list(self):
        """Test that get_insight_schedule_tools returns a list."""
        from src.tools.insight_schedule_tools import get_insight_schedule_tools

        tools = get_insight_schedule_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_get_insight_schedule_tools_includes_create_insight_schedule(self):
        """Test that create_insight_schedule is included."""
        from src.tools.insight_schedule_tools import (
            create_insight_schedule,
            get_insight_schedule_tools,
        )

        tools = get_insight_schedule_tools()
        assert create_insight_schedule in tools
