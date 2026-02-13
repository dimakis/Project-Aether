"""Unit tests for HA Registry helper routes.

Tests GET/POST/DELETE /registry/helpers endpoints with mocked HA client.
"""

from unittest.mock import AsyncMock, patch

HA_CLIENT_PATCH = "src.ha.get_ha_client"

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter


def _make_test_app():
    """Create a minimal FastAPI app with the registry router."""
    from fastapi import FastAPI

    from src.api.routes.ha_registry import router

    app = FastAPI()
    app.include_router(router, prefix="/registry")

    # Configure rate limiter for tests
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    return app


@pytest.fixture
def helpers_app():
    """Lightweight FastAPI app with registry routes."""
    return _make_test_app()


@pytest.fixture
async def helpers_client(helpers_app):
    """Async HTTP client wired to the test app."""
    async with AsyncClient(
        transport=ASGITransport(app=helpers_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_ha_client():
    """Mock HA client with helper methods."""
    client = AsyncMock()
    client.list_helpers = AsyncMock(return_value=[])
    client.create_input_boolean = AsyncMock(
        return_value={"success": True, "input_id": "test", "entity_id": "input_boolean.test"}
    )
    client.delete_helper = AsyncMock(
        return_value={"success": True, "entity_id": "input_boolean.test"}
    )
    return client


class TestListHelpers:
    """Tests for GET /registry/helpers."""

    @pytest.mark.asyncio
    async def test_list_helpers_empty(self, helpers_client, mock_ha_client):
        """Test listing helpers when none exist."""
        with patch(HA_CLIENT_PATCH, return_value=mock_ha_client):
            resp = await helpers_client.get("/registry/helpers")

        assert resp.status_code == 200
        data = resp.json()
        assert data["helpers"] == []
        assert data["total"] == 0
        assert data["by_type"] == {}

    @pytest.mark.asyncio
    async def test_list_helpers_with_data(self, helpers_client, mock_ha_client):
        """Test listing helpers returns structured data."""
        mock_ha_client.list_helpers.return_value = [
            {
                "entity_id": "input_boolean.vacation",
                "domain": "input_boolean",
                "name": "Vacation Mode",
                "state": "off",
                "attributes": {"icon": "mdi:beach"},
            },
            {
                "entity_id": "counter.visitors",
                "domain": "counter",
                "name": "Visitors",
                "state": "3",
                "attributes": {},
            },
        ]

        with patch(HA_CLIENT_PATCH, return_value=mock_ha_client):
            resp = await helpers_client.get("/registry/helpers")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["by_type"]["input_boolean"] == 1
        assert data["by_type"]["counter"] == 1
        assert data["helpers"][0]["entity_id"] == "input_boolean.vacation"


class TestCreateHelper:
    """Tests for POST /registry/helpers."""

    @pytest.mark.asyncio
    async def test_create_input_boolean(self, helpers_client, mock_ha_client):
        """Test creating an input_boolean helper."""
        with patch(HA_CLIENT_PATCH, return_value=mock_ha_client):
            resp = await helpers_client.post(
                "/registry/helpers",
                json={
                    "helper_type": "input_boolean",
                    "input_id": "vacation_mode",
                    "name": "Vacation Mode",
                    "icon": "mdi:beach",
                    "config": {"initial": True},
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["helper_type"] == "input_boolean"
        mock_ha_client.create_input_boolean.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_input_number(self, helpers_client, mock_ha_client):
        """Test creating an input_number helper."""
        mock_ha_client.create_input_number = AsyncMock(
            return_value={
                "success": True,
                "input_id": "threshold",
                "entity_id": "input_number.threshold",
            }
        )

        with patch(HA_CLIENT_PATCH, return_value=mock_ha_client):
            resp = await helpers_client.post(
                "/registry/helpers",
                json={
                    "helper_type": "input_number",
                    "input_id": "threshold",
                    "name": "Threshold",
                    "config": {"min": 0, "max": 100, "step": 5},
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        mock_ha_client.create_input_number.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_counter(self, helpers_client, mock_ha_client):
        """Test creating a counter helper."""
        mock_ha_client.create_counter = AsyncMock(
            return_value={"success": True, "input_id": "visitors", "entity_id": "counter.visitors"}
        )

        with patch(HA_CLIENT_PATCH, return_value=mock_ha_client):
            resp = await helpers_client.post(
                "/registry/helpers",
                json={
                    "helper_type": "counter",
                    "input_id": "visitors",
                    "name": "Visitors",
                    "config": {"initial": 0, "step": 1},
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_create_timer(self, helpers_client, mock_ha_client):
        """Test creating a timer helper."""
        mock_ha_client.create_timer = AsyncMock(
            return_value={"success": True, "input_id": "cooking", "entity_id": "timer.cooking"}
        )

        with patch(HA_CLIENT_PATCH, return_value=mock_ha_client):
            resp = await helpers_client.post(
                "/registry/helpers",
                json={
                    "helper_type": "timer",
                    "input_id": "cooking",
                    "name": "Cooking Timer",
                    "config": {"duration": "00:30:00"},
                },
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_create_helper_invalid_input_id(self, helpers_client):
        """Test validation rejects invalid input_id."""
        resp = await helpers_client.post(
            "/registry/helpers",
            json={
                "helper_type": "input_boolean",
                "input_id": "Invalid ID!",
                "name": "Test",
            },
        )

        assert resp.status_code == 422  # validation error

    @pytest.mark.asyncio
    async def test_create_helper_invalid_type(self, helpers_client):
        """Test validation rejects unknown helper type."""
        resp = await helpers_client.post(
            "/registry/helpers",
            json={
                "helper_type": "not_a_real_type",
                "input_id": "test",
                "name": "Test",
            },
        )

        assert resp.status_code == 422


class TestDeleteHelper:
    """Tests for DELETE /registry/helpers/{domain}/{input_id}."""

    @pytest.mark.asyncio
    async def test_delete_helper_success(self, helpers_client, mock_ha_client):
        """Test successful helper deletion."""
        with patch(HA_CLIENT_PATCH, return_value=mock_ha_client):
            resp = await helpers_client.delete("/registry/helpers/input_boolean/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["entity_id"] == "input_boolean.test"

    @pytest.mark.asyncio
    async def test_delete_helper_not_found(self, helpers_client, mock_ha_client):
        """Test deletion of non-existent helper."""
        mock_ha_client.delete_helper.return_value = {
            "success": False,
            "entity_id": "input_boolean.nonexistent",
            "error": "Not found",
        }

        with patch(HA_CLIENT_PATCH, return_value=mock_ha_client):
            resp = await helpers_client.delete("/registry/helpers/input_boolean/nonexistent")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "Not found"
