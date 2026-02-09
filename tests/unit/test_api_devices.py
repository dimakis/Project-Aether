"""Unit tests for Device API routes.

Tests GET /devices and GET /devices/{device_id} endpoints with mock
repository -- no real database or app lifespan needed.

The get_db dependency is overridden with a mock AsyncSession so
the test never attempts a real Postgres connection (which would
hang indefinitely in a unit-test environment).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.routes.devices import get_db


def _make_test_app():
    """Create a minimal FastAPI app with the device router and mock DB."""
    from fastapi import FastAPI

    from src.api.routes.devices import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Override get_db so no real Postgres connection is attempted
    async def _mock_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _mock_get_db
    return app


@pytest.fixture
def device_app():
    """Lightweight FastAPI app with device routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def device_client(device_app):
    """Async HTTP client wired to the device test app."""
    async with AsyncClient(
        transport=ASGITransport(app=device_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_device():
    """Create a mock Device object."""
    device = MagicMock()
    device.id = "uuid-device-1"
    device.ha_device_id = "device_123"
    device.name = "Test Device"
    device.area_id = "area-uuid-1"
    device.manufacturer = "Test Manufacturer"
    device.model = "Model X"
    device.sw_version = "1.0.0"
    device.entity_count = 5
    device.last_synced_at = datetime(2026, 2, 4, 12, 0, 0)
    return device


@pytest.fixture
def mock_device_2():
    """Create a second mock Device object."""
    device = MagicMock()
    device.id = "uuid-device-2"
    device.ha_device_id = "device_456"
    device.name = "Another Device"
    device.area_id = "area-uuid-2"
    device.manufacturer = "Another Manufacturer"
    device.model = "Model Y"
    device.sw_version = "2.0.0"
    device.entity_count = 3
    device.last_synced_at = datetime(2026, 2, 4, 12, 0, 0)
    return device


@pytest.fixture
def mock_device_repo(mock_device, mock_device_2):
    """Create mock DeviceRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_device, mock_device_2])
    repo.count = AsyncMock(return_value=2)
    repo.get_by_ha_device_id = AsyncMock(return_value=mock_device)
    repo.get_by_id = AsyncMock(return_value=mock_device)
    return repo


@pytest.mark.asyncio
class TestListDevices:
    """Tests for GET /api/v1/devices."""

    async def test_list_devices_returns_paginated_results(self, device_client, mock_device_repo):
        """Should return devices with total count."""
        with patch("src.api.routes.devices.DeviceRepository", return_value=mock_device_repo):
            response = await device_client.get("/api/v1/devices")

            assert response.status_code == 200
            data = response.json()
            assert "devices" in data
            assert data["total"] == 2
            assert len(data["devices"]) == 2
            assert data["devices"][0]["ha_device_id"] == "device_123"
            assert data["devices"][0]["name"] == "Test Device"

    async def test_list_devices_with_area_filter(self, device_client, mock_device_repo):
        """Should pass area_id to repository."""
        with patch("src.api.routes.devices.DeviceRepository", return_value=mock_device_repo):
            response = await device_client.get("/api/v1/devices?area_id=area-uuid-1")

            assert response.status_code == 200
            mock_device_repo.list_all.assert_called_once()
            call_kwargs = mock_device_repo.list_all.call_args[1]
            assert call_kwargs["area_id"] == "area-uuid-1"

    async def test_list_devices_with_manufacturer_filter(self, device_client, mock_device_repo):
        """Should pass manufacturer to repository."""
        with patch("src.api.routes.devices.DeviceRepository", return_value=mock_device_repo):
            response = await device_client.get("/api/v1/devices?manufacturer=Test%20Manufacturer")

            assert response.status_code == 200
            mock_device_repo.list_all.assert_called_once()
            call_kwargs = mock_device_repo.list_all.call_args[1]
            assert call_kwargs["manufacturer"] == "Test Manufacturer"

    async def test_list_devices_with_limit_and_offset(self, device_client, mock_device_repo):
        """Should respect limit and offset parameters."""
        with patch("src.api.routes.devices.DeviceRepository", return_value=mock_device_repo):
            response = await device_client.get("/api/v1/devices?limit=10&offset=5")

            assert response.status_code == 200
            mock_device_repo.list_all.assert_called_once()
            call_kwargs = mock_device_repo.list_all.call_args[1]
            assert call_kwargs["limit"] == 10
            assert call_kwargs["offset"] == 5

    async def test_list_devices_default_limit(self, device_client, mock_device_repo):
        """Should use default limit when not provided."""
        with patch("src.api.routes.devices.DeviceRepository", return_value=mock_device_repo):
            response = await device_client.get("/api/v1/devices")

            assert response.status_code == 200
            mock_device_repo.list_all.assert_called_once()
            call_kwargs = mock_device_repo.list_all.call_args[1]
            assert call_kwargs["limit"] == 100  # Default

    async def test_list_devices_empty(self, device_client):
        """Should return empty list when no devices exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with patch("src.api.routes.devices.DeviceRepository", return_value=repo):
            response = await device_client.get("/api/v1/devices")

            assert response.status_code == 200
            data = response.json()
            assert data["devices"] == []
            assert data["total"] == 0

    async def test_list_devices_with_multiple_filters(self, device_client, mock_device_repo):
        """Should combine multiple filters."""
        with patch("src.api.routes.devices.DeviceRepository", return_value=mock_device_repo):
            response = await device_client.get(
                "/api/v1/devices?area_id=area-uuid-1&manufacturer=Test%20Manufacturer&limit=50"
            )

            assert response.status_code == 200
            mock_device_repo.list_all.assert_called_once()
            call_kwargs = mock_device_repo.list_all.call_args[1]
            assert call_kwargs["area_id"] == "area-uuid-1"
            assert call_kwargs["manufacturer"] == "Test Manufacturer"
            assert call_kwargs["limit"] == 50


@pytest.mark.asyncio
class TestGetDevice:
    """Tests for GET /api/v1/devices/{device_id}."""

    async def test_get_device_by_ha_id(self, device_client, mock_device_repo):
        """Should find device by HA device ID."""
        with patch("src.api.routes.devices.DeviceRepository", return_value=mock_device_repo):
            response = await device_client.get("/api/v1/devices/device_123")

            assert response.status_code == 200
            data = response.json()
            assert data["ha_device_id"] == "device_123"
            assert data["name"] == "Test Device"
            mock_device_repo.get_by_ha_device_id.assert_called_once_with("device_123")

    async def test_get_device_by_internal_id(self, device_client):
        """Should fall back to internal ID when HA ID not found."""
        device = MagicMock()
        device.id = "uuid-device-1"
        device.ha_device_id = "device_123"
        device.name = "Test Device"
        device.area_id = None
        device.manufacturer = None
        device.model = None
        device.sw_version = None
        device.entity_count = 0
        device.last_synced_at = None

        repo = MagicMock()
        repo.get_by_ha_device_id = AsyncMock(return_value=None)
        repo.get_by_id = AsyncMock(return_value=device)

        with patch("src.api.routes.devices.DeviceRepository", return_value=repo):
            response = await device_client.get("/api/v1/devices/uuid-device-1")

            assert response.status_code == 200
            repo.get_by_ha_device_id.assert_called_once_with("uuid-device-1")
            repo.get_by_id.assert_called_once_with("uuid-device-1")

    async def test_get_device_not_found(self, device_client):
        """Should return 404 when device not found."""
        repo = MagicMock()
        repo.get_by_ha_device_id = AsyncMock(return_value=None)
        repo.get_by_id = AsyncMock(return_value=None)

        with patch("src.api.routes.devices.DeviceRepository", return_value=repo):
            response = await device_client.get("/api/v1/devices/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    async def test_get_device_with_all_fields(self, device_client, mock_device_repo):
        """Should return all device fields."""
        with patch("src.api.routes.devices.DeviceRepository", return_value=mock_device_repo):
            response = await device_client.get("/api/v1/devices/device_123")

            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "ha_device_id" in data
            assert "name" in data
            assert "area_id" in data
            assert "manufacturer" in data
            assert "model" in data
            assert "sw_version" in data
            assert "entity_count" in data
            assert "last_synced_at" in data
