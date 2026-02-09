"""Unit tests for Insight Schedule API routes.

Tests CRUD endpoints for insight schedules with mock repositories.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter


def _make_test_app():
    """Create a minimal FastAPI app with the insight schedules router."""
    from fastapi import FastAPI

    from src.api.routes.insight_schedules import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Configure rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    return app


@pytest.fixture
def schedules_app():
    """Lightweight FastAPI app with insight schedule routes."""
    return _make_test_app()


@pytest.fixture
async def schedules_client(schedules_app):
    """Async HTTP client wired to the schedules test app."""
    async with AsyncClient(
        transport=ASGITransport(app=schedules_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_schedule():
    """Create a mock insight schedule."""
    schedule = MagicMock()
    schedule.id = str(uuid4())
    schedule.name = "Daily Energy Analysis"
    schedule.enabled = True
    schedule.analysis_type = "energy"
    schedule.trigger_type = "cron"
    schedule.entity_ids = ["sensor.power"]
    schedule.hours = 24
    schedule.options = {}
    schedule.cron_expression = "0 2 * * *"
    schedule.webhook_event = None
    schedule.webhook_filter = None
    schedule.last_run_at = None
    schedule.last_result = None
    schedule.last_error = None
    schedule.run_count = 0
    schedule.created_at = datetime.now(UTC)
    schedule.updated_at = datetime.now(UTC)
    return schedule


@pytest.mark.asyncio
class TestListSchedules:
    """Tests for GET /api/v1/insight-schedules."""

    async def test_list_schedules_success(self, schedules_client, mock_session, mock_schedule):
        """Should return list of schedules."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
        ):
            MockRepo.return_value.list_all = AsyncMock(return_value=[mock_schedule])

            response = await schedules_client.get("/api/v1/insight-schedules")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["name"] == "Daily Energy Analysis"

    async def test_list_schedules_with_filters(self, schedules_client, mock_session, mock_schedule):
        """Should filter schedules by trigger_type and enabled."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
        ):
            MockRepo.return_value.list_all = AsyncMock(return_value=[mock_schedule])

            response = await schedules_client.get(
                "/api/v1/insight-schedules?trigger_type=cron&enabled_only=true"
            )

            assert response.status_code == 200
            MockRepo.return_value.list_all.assert_called_once_with(
                enabled_only=True, trigger_type="cron"
            )

    async def test_list_schedules_empty(self, schedules_client, mock_session):
        """Should return empty list when no schedules."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
        ):
            MockRepo.return_value.list_all = AsyncMock(return_value=[])

            response = await schedules_client.get("/api/v1/insight-schedules")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []


@pytest.mark.asyncio
class TestCreateSchedule:
    """Tests for POST /api/v1/insight-schedules."""

    async def test_create_cron_schedule_success(
        self, schedules_client, mock_session, mock_schedule
    ):
        """Should create a cron schedule successfully."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
            patch("src.api.routes.insight_schedules._sync_scheduler") as mock_sync,
            patch("apscheduler.triggers.cron.CronTrigger") as MockCronTrigger,
        ):
            MockRepo.return_value.create = AsyncMock(return_value=mock_schedule)
            MockCronTrigger.from_crontab.return_value = MagicMock()
            mock_sync.return_value = None

            response = await schedules_client.post(
                "/api/v1/insight-schedules",
                json={
                    "name": "Daily Energy Analysis",
                    "analysis_type": "energy",
                    "trigger_type": "cron",
                    "cron_expression": "0 2 * * *",
                    "entity_ids": ["sensor.power"],
                    "hours": 24,
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Daily Energy Analysis"
            assert data["trigger_type"] == "cron"
            mock_sync.assert_called_once()

    async def test_create_webhook_schedule_success(
        self, schedules_client, mock_session, mock_schedule
    ):
        """Should create a webhook schedule successfully."""
        mock_schedule.trigger_type = "webhook"
        mock_schedule.webhook_event = "device_offline"
        mock_schedule.cron_expression = None

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
            patch("src.api.routes.insight_schedules._sync_scheduler"),
        ):
            MockRepo.return_value.create = AsyncMock(return_value=mock_schedule)

            response = await schedules_client.post(
                "/api/v1/insight-schedules",
                json={
                    "name": "Device Offline Analysis",
                    "analysis_type": "device_health",
                    "trigger_type": "webhook",
                    "webhook_event": "device_offline",
                    "webhook_filter": {"entity_id": "sensor.temp"},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["trigger_type"] == "webhook"
            assert data["webhook_event"] == "device_offline"

    async def test_create_schedule_missing_cron_expression(self, schedules_client, mock_session):
        """Should return 400 when cron_expression missing for cron trigger."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with patch(
            "src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory
        ):
            response = await schedules_client.post(
                "/api/v1/insight-schedules",
                json={
                    "name": "Test",
                    "analysis_type": "energy",
                    "trigger_type": "cron",
                },
            )

            assert response.status_code == 400

    async def test_create_schedule_missing_webhook_event(self, schedules_client, mock_session):
        """Should return 400 when webhook_event missing for webhook trigger."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with patch(
            "src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory
        ):
            response = await schedules_client.post(
                "/api/v1/insight-schedules",
                json={
                    "name": "Test",
                    "analysis_type": "energy",
                    "trigger_type": "webhook",
                },
            )

            assert response.status_code == 400

    async def test_create_schedule_invalid_cron(self, schedules_client, mock_session):
        """Should return 400 for invalid cron expression."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("apscheduler.triggers.cron.CronTrigger") as MockCronTrigger,
        ):
            MockCronTrigger.from_crontab.side_effect = ValueError("Invalid cron")

            response = await schedules_client.post(
                "/api/v1/insight-schedules",
                json={
                    "name": "Test",
                    "analysis_type": "energy",
                    "trigger_type": "cron",
                    "cron_expression": "invalid",
                },
            )

            assert response.status_code == 400


@pytest.mark.asyncio
class TestGetSchedule:
    """Tests for GET /api/v1/insight-schedules/{schedule_id}."""

    async def test_get_schedule_success(self, schedules_client, mock_session, mock_schedule):
        """Should return schedule by ID."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
        ):
            MockRepo.return_value.get = AsyncMock(return_value=mock_schedule)

            response = await schedules_client.get(f"/api/v1/insight-schedules/{mock_schedule.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == mock_schedule.id
            assert data["name"] == "Daily Energy Analysis"

    async def test_get_schedule_not_found(self, schedules_client, mock_session):
        """Should return 404 when schedule not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
        ):
            MockRepo.return_value.get = AsyncMock(return_value=None)

            response = await schedules_client.get("/api/v1/insight-schedules/nonexistent")

            assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateSchedule:
    """Tests for PUT /api/v1/insight-schedules/{schedule_id}."""

    async def test_update_schedule_success(self, schedules_client, mock_session, mock_schedule):
        """Should update schedule successfully."""
        mock_schedule.name = "Updated Name"
        mock_schedule.enabled = False

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
            patch("src.api.routes.insight_schedules._sync_scheduler") as mock_sync,
        ):
            MockRepo.return_value.update = AsyncMock(return_value=mock_schedule)

            response = await schedules_client.put(
                f"/api/v1/insight-schedules/{mock_schedule.id}",
                json={"name": "Updated Name", "enabled": False},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"
            assert data["enabled"] is False
            mock_sync.assert_called_once()

    async def test_update_schedule_invalid_cron(self, schedules_client, mock_session):
        """Should return 400 for invalid cron expression."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("apscheduler.triggers.cron.CronTrigger") as MockCronTrigger,
        ):
            MockCronTrigger.from_crontab.side_effect = ValueError("Invalid cron")

            response = await schedules_client.put(
                "/api/v1/insight-schedules/test-id",
                json={"cron_expression": "invalid"},
            )

            assert response.status_code == 400

    async def test_update_schedule_no_fields(self, schedules_client, mock_session):
        """Should return 400 when no fields to update."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with patch(
            "src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory
        ):
            response = await schedules_client.put(
                "/api/v1/insight-schedules/test-id",
                json={},
            )

            assert response.status_code == 400

    async def test_update_schedule_not_found(self, schedules_client, mock_session):
        """Should return 404 when schedule not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
        ):
            MockRepo.return_value.update = AsyncMock(return_value=None)

            response = await schedules_client.put(
                "/api/v1/insight-schedules/nonexistent",
                json={"name": "Updated"},
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteSchedule:
    """Tests for DELETE /api/v1/insight-schedules/{schedule_id}."""

    async def test_delete_schedule_success(self, schedules_client, mock_session, mock_schedule):
        """Should delete schedule successfully."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
            patch("src.api.routes.insight_schedules._sync_scheduler") as mock_sync,
        ):
            MockRepo.return_value.delete = AsyncMock(return_value=True)

            response = await schedules_client.delete(
                f"/api/v1/insight-schedules/{mock_schedule.id}"
            )

            assert response.status_code == 204
            mock_sync.assert_called_once()

    async def test_delete_schedule_not_found(self, schedules_client, mock_session):
        """Should return 404 when schedule not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
        ):
            MockRepo.return_value.delete = AsyncMock(return_value=False)

            response = await schedules_client.delete("/api/v1/insight-schedules/nonexistent")

            assert response.status_code == 404


@pytest.mark.asyncio
class TestRunScheduleNow:
    """Tests for POST /api/v1/insight-schedules/{schedule_id}/run."""

    async def test_run_schedule_now_success(self, schedules_client, mock_session, mock_schedule):
        """Should queue schedule execution."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
            patch("src.scheduler.service._execute_scheduled_analysis"),
        ):
            MockRepo.return_value.get = AsyncMock(return_value=mock_schedule)

            response = await schedules_client.post(
                f"/api/v1/insight-schedules/{mock_schedule.id}/run"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "queued"
            assert data["schedule_id"] == mock_schedule.id

    async def test_run_schedule_now_not_found(self, schedules_client, mock_session):
        """Should return 404 when schedule not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.insight_schedules.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.insight_schedules.InsightScheduleRepository") as MockRepo,
        ):
            MockRepo.return_value.get = AsyncMock(return_value=None)

            response = await schedules_client.post("/api/v1/insight-schedules/nonexistent/run")

            assert response.status_code == 404
