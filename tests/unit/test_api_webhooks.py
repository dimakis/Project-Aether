"""Unit tests for Webhook API routes.

Tests POST /webhooks/ha endpoint with mock repository -- no real database
or app lifespan needed.

The get_session() function is called directly (not a FastAPI dependency),
so it must be patched at the source: "src.storage.get_session".
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter


def _make_test_app():
    """Create a minimal FastAPI app with the webhook router and mock DB."""
    from fastapi import FastAPI

    from src.api.routes.webhooks import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Configure rate limiter for tests (required by @limiter.limit decorators)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    return app


@pytest.fixture
def webhook_app():
    """Lightweight FastAPI app with webhook routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def webhook_client(webhook_app):
    """Async HTTP client wired to the webhook test app."""
    async with AsyncClient(
        transport=ASGITransport(app=webhook_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_get_session(mock_session):
    """Create a mock get_session async context manager."""

    @asynccontextmanager
    async def _mock_get_session():
        yield mock_session

    return _mock_get_session


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.webhook_secret = None
    settings.environment = "development"
    return settings


@pytest.fixture
def mock_settings_with_secret():
    """Create mock settings with webhook secret."""
    settings = MagicMock()
    settings.webhook_secret = "test-secret-123"
    settings.environment = "production"
    return settings


@pytest.fixture
def mock_insight_schedule():
    """Create a mock InsightSchedule object."""
    schedule = MagicMock()
    schedule.id = "schedule-uuid-1"
    schedule.name = "Test Schedule"
    schedule.enabled = True
    schedule.analysis_type = "behavior_analysis"
    schedule.entity_ids = ["sensor.power"]
    schedule.hours = 24
    schedule.options = {}
    schedule.webhook_event = "device_offline"
    schedule.webhook_filter = {"entity_id": "sensor.power*"}
    schedule.record_run = MagicMock()
    schedule.run_count = 0
    return schedule


@pytest.fixture
def mock_insight_schedule_repo(mock_insight_schedule):
    """Create mock InsightScheduleRepository."""
    repo = MagicMock()
    repo.list_webhook_triggers = AsyncMock(return_value=[mock_insight_schedule])
    repo.get = AsyncMock(return_value=mock_insight_schedule)
    return repo


@pytest.mark.asyncio
class TestReceiveHAWebhook:
    """Tests for POST /api/v1/webhooks/ha."""

    async def test_receive_webhook_no_secret_development(
        self,
        webhook_client,
        mock_get_session,
        mock_insight_schedule_repo,
        mock_settings,
    ):
        """Should accept webhook in development without secret."""
        with (
            patch("src.storage.get_session", mock_get_session),
            patch("src.api.routes.webhooks.get_settings", return_value=mock_settings),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_insight_schedule_repo,
            ),
            patch("src.api.routes.webhooks._run_webhook_analysis"),
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "state_changed",
                    "entity_id": "sensor.power_1",
                    "webhook_event": "device_offline",
                    "data": {"old_state": "on", "new_state": "off"},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["matched_schedules"] == 1
            assert "Queued 1 analysis job(s)" in data["message"]
            # Background task should be queued (doesn't run in tests)

    async def test_receive_webhook_with_valid_secret(
        self,
        webhook_client,
        mock_get_session,
        mock_insight_schedule_repo,
        mock_settings_with_secret,
    ):
        """Should accept webhook with valid secret."""
        with (
            patch("src.storage.get_session", mock_get_session),
            patch(
                "src.api.routes.webhooks.get_settings",
                return_value=mock_settings_with_secret,
            ),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_insight_schedule_repo,
            ),
            patch("src.api.routes.webhooks._run_webhook_analysis"),
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "state_changed",
                    "entity_id": "sensor.power_1",
                    "webhook_event": "device_offline",
                },
                headers={"X-Webhook-Secret": "test-secret-123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"

    async def test_receive_webhook_invalid_secret(
        self,
        webhook_client,
        mock_settings_with_secret,
    ):
        """Should reject webhook with invalid secret."""
        with patch(
            "src.api.routes.webhooks.get_settings",
            return_value=mock_settings_with_secret,
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "state_changed",
                    "entity_id": "sensor.power_1",
                },
                headers={"X-Webhook-Secret": "wrong-secret"},
            )

            assert response.status_code == 401
            assert "Invalid webhook secret" in response.json()["detail"]

    async def test_receive_webhook_missing_secret_production(
        self,
        webhook_client,
        mock_settings,
    ):
        """Should reject webhook in production without secret configured."""
        mock_settings.webhook_secret = None
        mock_settings.environment = "production"

        with patch(
            "src.api.routes.webhooks.get_settings",
            return_value=mock_settings,
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "state_changed",
                    "entity_id": "sensor.power_1",
                },
            )

            assert response.status_code == 500
            assert "WEBHOOK_SECRET" in response.json()["detail"]

    async def test_receive_webhook_no_matching_triggers(
        self,
        webhook_client,
        mock_get_session,
        mock_settings,
    ):
        """Should return no_match when no triggers match."""
        repo = MagicMock()
        repo.list_webhook_triggers = AsyncMock(return_value=[])

        with (
            patch("src.storage.get_session", mock_get_session),
            patch("src.api.routes.webhooks.get_settings", return_value=mock_settings),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=repo,
            ),
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "state_changed",
                    "entity_id": "sensor.other",
                    "webhook_event": "unknown_event",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "no_match"
            assert data["matched_schedules"] == 0
            assert "No matching triggers found" in data["message"]

    async def test_receive_webhook_entity_registry_updated(
        self,
        webhook_client,
        mock_get_session,
        mock_insight_schedule_repo,
        mock_settings,
    ):
        """Should trigger registry sync for entity_registry_updated events."""
        with (
            patch("src.storage.get_session", mock_get_session),
            patch("src.api.routes.webhooks.get_settings", return_value=mock_settings),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=mock_insight_schedule_repo,
            ),
            patch("src.api.routes.webhooks._run_registry_sync"),
            patch("src.api.routes.webhooks._run_webhook_analysis"),
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "entity_registry_updated",
                    "entity_id": "automation.test",
                    "data": {"action": "create"},
                },
            )

            assert response.status_code == 200
            # Background task should be queued (doesn't run in tests)

    async def test_receive_webhook_with_filter_match(
        self,
        webhook_client,
        mock_get_session,
        mock_insight_schedule_repo,
        mock_settings,
    ):
        """Should match webhook using filter criteria."""
        schedule = MagicMock()
        schedule.id = "schedule-uuid-1"
        schedule.webhook_filter = {
            "entity_id": "sensor.power*",
            "event_type": "state_changed",
            "to_state": "off",
        }
        repo = MagicMock()
        repo.list_webhook_triggers = AsyncMock(return_value=[schedule])

        with (
            patch("src.storage.get_session", mock_get_session),
            patch("src.api.routes.webhooks.get_settings", return_value=mock_settings),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=repo,
            ),
            patch("src.api.routes.webhooks._run_webhook_analysis"),
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "state_changed",
                    "entity_id": "sensor.power_main",
                    "data": {"old_state": "on", "new_state": "off"},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["matched_schedules"] == 1

    async def test_receive_webhook_with_filter_no_match(
        self,
        webhook_client,
        mock_get_session,
        mock_settings,
    ):
        """Should not match webhook when filter doesn't match."""
        schedule = MagicMock()
        schedule.id = "schedule-uuid-1"
        schedule.webhook_filter = {
            "entity_id": "sensor.power*",
            "event_type": "state_changed",
            "to_state": "on",
        }
        repo = MagicMock()
        repo.list_webhook_triggers = AsyncMock(return_value=[schedule])

        with (
            patch("src.storage.get_session", mock_get_session),
            patch("src.api.routes.webhooks.get_settings", return_value=mock_settings),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=repo,
            ),
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "state_changed",
                    "entity_id": "sensor.power_main",
                    "data": {"old_state": "off", "new_state": "off"},  # to_state is "off", not "on"
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "no_match"
            assert data["matched_schedules"] == 0

    async def test_receive_webhook_multiple_matches(
        self,
        webhook_client,
        mock_get_session,
        mock_settings,
    ):
        """Should match multiple triggers."""
        schedule1 = MagicMock()
        schedule1.id = "schedule-uuid-1"
        schedule1.webhook_filter = None  # No filter = match everything
        schedule2 = MagicMock()
        schedule2.id = "schedule-uuid-2"
        schedule2.webhook_filter = {"entity_id": "sensor.*"}
        repo = MagicMock()
        repo.list_webhook_triggers = AsyncMock(return_value=[schedule1, schedule2])

        with (
            patch("src.storage.get_session", mock_get_session),
            patch("src.api.routes.webhooks.get_settings", return_value=mock_settings),
            patch(
                "src.dal.insight_schedules.InsightScheduleRepository",
                return_value=repo,
            ),
            patch("src.api.routes.webhooks._run_webhook_analysis"),
        ):
            response = await webhook_client.post(
                "/api/v1/webhooks/ha",
                json={
                    "event_type": "state_changed",
                    "entity_id": "sensor.power_main",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["matched_schedules"] == 2
