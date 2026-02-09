"""Unit tests for Area API routes.

Tests GET /areas and GET /areas/{area_id} endpoints with mock
repository -- no real database or app lifespan needed.

The get_db dependency is overridden with a mock AsyncSession so
the test never attempts a real Postgres connection (which would
hang indefinitely in a unit-test environment).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.routes.areas import get_db


def _make_test_app():
    """Create a minimal FastAPI app with the area router and mock DB."""
    from fastapi import FastAPI

    from src.api.routes.areas import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Override get_db so no real Postgres connection is attempted
    async def _mock_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _mock_get_db
    return app


@pytest.fixture
def area_app():
    """Lightweight FastAPI app with area routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def area_client(area_app):
    """Async HTTP client wired to the area test app."""
    async with AsyncClient(
        transport=ASGITransport(app=area_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_area():
    """Create a mock Area object."""
    area = MagicMock()
    area.id = "uuid-area-1"
    area.ha_area_id = "living_room"
    area.name = "Living Room"
    area.floor_id = "ground"
    area.icon = "mdi:sofa"
    area.entity_count = 5
    area.last_synced_at = datetime(2026, 2, 4, 12, 0, 0)
    return area


@pytest.fixture
def mock_area_2():
    """Create a second mock Area object."""
    area = MagicMock()
    area.id = "uuid-area-2"
    area.ha_area_id = "bedroom"
    area.name = "Bedroom"
    area.floor_id = "first"
    area.icon = "mdi:bed"
    area.entity_count = 3
    area.last_synced_at = datetime(2026, 2, 4, 12, 0, 0)
    return area


@pytest.fixture
def mock_area_repo(mock_area, mock_area_2):
    """Create mock AreaRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_area, mock_area_2])
    repo.count = AsyncMock(return_value=2)
    repo.get_by_ha_area_id = AsyncMock(return_value=mock_area)
    repo.get_by_id = AsyncMock(return_value=mock_area)
    return repo


@pytest.mark.asyncio
class TestListAreas:
    """Tests for GET /api/v1/areas."""

    async def test_list_areas_returns_paginated_results(self, area_client, mock_area_repo):
        """Should return areas with total count."""
        with patch("src.api.routes.areas.AreaRepository", return_value=mock_area_repo):
            response = await area_client.get("/api/v1/areas")

            assert response.status_code == 200
            data = response.json()
            assert "areas" in data
            assert data["total"] == 2
            assert len(data["areas"]) == 2
            assert data["areas"][0]["ha_area_id"] == "living_room"
            assert data["areas"][0]["name"] == "Living Room"

    async def test_list_areas_with_floor_filter(self, area_client, mock_area_repo):
        """Should pass floor_id to repository."""
        with patch("src.api.routes.areas.AreaRepository", return_value=mock_area_repo):
            response = await area_client.get("/api/v1/areas?floor_id=ground")

            assert response.status_code == 200
            mock_area_repo.list_all.assert_called_once()
            call_kwargs = mock_area_repo.list_all.call_args[1]
            assert call_kwargs["floor_id"] == "ground"

    async def test_list_areas_empty(self, area_client):
        """Should return empty list when no areas exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with patch("src.api.routes.areas.AreaRepository", return_value=repo):
            response = await area_client.get("/api/v1/areas")

            assert response.status_code == 200
            data = response.json()
            assert data["areas"] == []
            assert data["total"] == 0


@pytest.mark.asyncio
class TestGetArea:
    """Tests for GET /api/v1/areas/{area_id}."""

    async def test_get_area_by_ha_id(self, area_client, mock_area_repo):
        """Should find area by HA area ID."""
        with patch("src.api.routes.areas.AreaRepository", return_value=mock_area_repo):
            response = await area_client.get("/api/v1/areas/living_room")

            assert response.status_code == 200
            data = response.json()
            assert data["ha_area_id"] == "living_room"
            assert data["name"] == "Living Room"
            mock_area_repo.get_by_ha_area_id.assert_called_once_with("living_room")

    async def test_get_area_by_internal_id(self, area_client):
        """Should fall back to internal ID when HA ID not found."""
        area = MagicMock()
        area.id = "uuid-area-1"
        area.ha_area_id = "living_room"
        area.name = "Living Room"
        area.floor_id = None
        area.icon = None
        area.entity_count = 0
        area.last_synced_at = None

        repo = MagicMock()
        repo.get_by_ha_area_id = AsyncMock(return_value=None)
        repo.get_by_id = AsyncMock(return_value=area)

        with patch("src.api.routes.areas.AreaRepository", return_value=repo):
            response = await area_client.get("/api/v1/areas/uuid-area-1")

            assert response.status_code == 200
            repo.get_by_ha_area_id.assert_called_once_with("uuid-area-1")
            repo.get_by_id.assert_called_once_with("uuid-area-1")

    async def test_get_area_not_found(self, area_client):
        """Should return 404 when area not found."""
        repo = MagicMock()
        repo.get_by_ha_area_id = AsyncMock(return_value=None)
        repo.get_by_id = AsyncMock(return_value=None)

        with patch("src.api.routes.areas.AreaRepository", return_value=repo):
            response = await area_client.get("/api/v1/areas/nonexistent")

            assert response.status_code == 404
