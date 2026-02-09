"""Unit tests for HA Zones API routes.

Tests CRUD endpoints for HA zones with mock repositories --
no real database or app lifespan needed.

The get_session dependency is patched at the import site so
the test never attempts a real Postgres connection.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _make_test_app():
    """Create a minimal FastAPI app with the ha_zones router and mock DB."""
    from fastapi import FastAPI

    from src.api.routes.ha_zones import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    return app


@pytest.fixture
def ha_zones_app():
    """Lightweight FastAPI app with ha_zones routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def ha_zones_client(ha_zones_app):
    """Async HTTP client wired to the ha_zones test app."""
    async with AsyncClient(
        transport=ASGITransport(app=ha_zones_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_zone():
    """Create a mock HAZone object."""
    zone = MagicMock()
    zone.id = "zone-1"
    zone.name = "Test Zone"
    zone.slug = "test-zone"
    zone.ha_url = "http://localhost:8123"
    zone.ha_url_remote = None
    zone.is_default = False
    zone.latitude = None
    zone.longitude = None
    zone.icon = None
    zone.url_preference = "auto"
    zone.created_at = datetime.now(UTC)
    zone.updated_at = datetime.now(UTC)
    zone.ha_token_encrypted = "encrypted_token"
    return zone


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_zone_repo(mock_zone):
    """Create mock HAZoneRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_zone])
    repo.get_by_id = AsyncMock(return_value=mock_zone)
    repo.get_by_slug = AsyncMock(return_value=None)
    repo.get_default = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=mock_zone)
    repo.update = AsyncMock(return_value=mock_zone)
    repo.delete = AsyncMock(return_value=True)
    repo.set_default = AsyncMock(return_value=mock_zone)
    repo.get_connection = AsyncMock(
        return_value=("http://localhost:8123", None, "test_token", "auto")
    )
    return repo


@pytest.mark.asyncio
class TestListZones:
    """Tests for GET /api/v1/zones."""

    async def test_list_zones_success(
        self, ha_zones_client, mock_zone_repo, mock_zone, mock_session
    ):
        """Should return list of zones."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
        ):
            response = await ha_zones_client.get("/api/v1/zones")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "zone-1"
            assert data[0]["name"] == "Test Zone"
            assert data[0]["slug"] == "test-zone"

    async def test_list_zones_empty(self, ha_zones_client, mock_session):
        """Should return empty list when no zones exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=repo),
        ):
            response = await ha_zones_client.get("/api/v1/zones")

            assert response.status_code == 200
            data = response.json()
            assert data == []


@pytest.mark.asyncio
class TestCreateZone:
    """Tests for POST /api/v1/zones."""

    async def test_create_zone_success(
        self, ha_zones_client, mock_zone_repo, mock_zone, mock_session
    ):
        """Should create a new zone."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        def _get_session_factory():
            return _mock_get_session()

        async def _mock_verify_ha_connection(url: str, token: str):
            return {"version": "2024.1.0"}

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones.verify_ha_connection", new=_mock_verify_ha_connection),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
        ):
            response = await ha_zones_client.post(
                "/api/v1/zones",
                json={
                    "name": "New Zone",
                    "ha_url": "http://localhost:8123",
                    "ha_token": "test_token",
                    "is_default": False,
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "zone-1"
            assert data["name"] == "Test Zone"
            mock_zone_repo.create.assert_called_once()
            mock_session.commit.assert_called_once()

    async def test_create_zone_with_remote_url(
        self, ha_zones_client, mock_zone_repo, mock_zone, mock_session
    ):
        """Should create zone with remote URL."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        def _get_session_factory():
            return _mock_get_session()

        async def _mock_verify_ha_connection(url: str, token: str):
            return {"version": "2024.1.0"}

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones.verify_ha_connection", new=_mock_verify_ha_connection),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
        ):
            response = await ha_zones_client.post(
                "/api/v1/zones",
                json={
                    "name": "New Zone",
                    "ha_url": "http://localhost:8123",
                    "ha_url_remote": "https://example.com",
                    "ha_token": "test_token",
                    "is_default": False,
                },
            )

            assert response.status_code == 201
            mock_zone_repo.create.assert_called_once()

    async def test_create_zone_verification_failure(
        self, ha_zones_client, mock_zone_repo, mock_session
    ):
        """Should return error when HA connection verification fails."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        from fastapi import HTTPException

        async def _mock_verify_ha_connection(url: str, token: str):
            raise HTTPException(status_code=400, detail="Invalid token")

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.verify_ha_connection", new=_mock_verify_ha_connection),
        ):
            response = await ha_zones_client.post(
                "/api/v1/zones",
                json={
                    "name": "New Zone",
                    "ha_url": "http://localhost:8123",
                    "ha_token": "invalid_token",
                    "is_default": False,
                },
            )

            assert response.status_code == 400


@pytest.mark.asyncio
class TestUpdateZone:
    """Tests for PATCH /api/v1/zones/{zone_id}."""

    async def test_update_zone_success(
        self, ha_zones_client, mock_zone_repo, mock_zone, mock_session
    ):
        """Should update zone fields."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        def _get_session_factory():
            return _mock_get_session()

        async def _mock_verify_ha_connection(url: str, token: str):
            return {"version": "2024.1.0"}

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones.verify_ha_connection", new=_mock_verify_ha_connection),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
            patch("src.dal.system_config.decrypt_token", return_value="test_token"),
        ):
            response = await ha_zones_client.patch(
                "/api/v1/zones/zone-1",
                json={"name": "Updated Zone"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "zone-1"
            mock_zone_repo.update.assert_called_once()
            mock_session.commit.assert_called_once()

    async def test_update_zone_not_found(self, ha_zones_client, mock_zone_repo, mock_session):
        """Should return 404 when zone not found."""
        mock_zone_repo.get_by_id = AsyncMock(return_value=None)
        mock_zone_repo.update = AsyncMock(return_value=None)

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
        ):
            response = await ha_zones_client.patch(
                "/api/v1/zones/nonexistent",
                json={"name": "Updated Zone"},
            )

            assert response.status_code == 404

    async def test_update_zone_with_token_verification(
        self, ha_zones_client, mock_zone_repo, mock_zone, mock_session
    ):
        """Should verify connection when token is updated."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        def _get_session_factory():
            return _mock_get_session()

        async def _mock_verify_ha_connection(url: str, token: str):
            return {"version": "2024.1.0"}

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones.verify_ha_connection", new=_mock_verify_ha_connection),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
            patch("src.dal.system_config.decrypt_token", return_value="old_token"),
        ):
            response = await ha_zones_client.patch(
                "/api/v1/zones/zone-1",
                json={"ha_token": "new_token"},
            )

            assert response.status_code == 200
            # Verify connection should be called with new token
            # (verify_ha_connection is called in the route)


@pytest.mark.asyncio
class TestDeleteZone:
    """Tests for DELETE /api/v1/zones/{zone_id}."""

    async def test_delete_zone_success(self, ha_zones_client, mock_zone_repo, mock_session):
        """Should delete a zone."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
        ):
            response = await ha_zones_client.delete("/api/v1/zones/zone-1")

            assert response.status_code == 204
            mock_zone_repo.delete.assert_called_once_with("zone-1")
            mock_session.commit.assert_called_once()

    async def test_delete_zone_not_found(self, ha_zones_client, mock_zone_repo, mock_session):
        """Should return 400 when zone cannot be deleted."""
        mock_zone_repo.delete = AsyncMock(return_value=False)

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
        ):
            response = await ha_zones_client.delete("/api/v1/zones/nonexistent")

            assert response.status_code == 400
            assert "Cannot delete" in response.json()["detail"]


@pytest.mark.asyncio
class TestSetDefaultZone:
    """Tests for POST /api/v1/zones/{zone_id}/set-default."""

    async def test_set_default_zone_success(
        self, ha_zones_client, mock_zone_repo, mock_zone, mock_session
    ):
        """Should set a zone as default."""
        mock_zone.is_default = True

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
        ):
            response = await ha_zones_client.post("/api/v1/zones/zone-1/set-default")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "zone-1"
            mock_zone_repo.set_default.assert_called_once_with("zone-1")
            mock_session.commit.assert_called_once()

    async def test_set_default_zone_not_found(self, ha_zones_client, mock_zone_repo, mock_session):
        """Should return 404 when zone not found."""
        mock_zone_repo.set_default = AsyncMock(return_value=None)

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
        ):
            response = await ha_zones_client.post("/api/v1/zones/nonexistent/set-default")

            assert response.status_code == 404


@pytest.mark.asyncio
class TestTestZone:
    """Tests for POST /api/v1/zones/{zone_id}/test."""

    async def test_test_zone_success(self, ha_zones_client, mock_zone_repo, mock_session):
        """Should test zone connectivity."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        def _get_session_factory():
            return _mock_get_session()

        async def _mock_verify_ha_connection(url: str, token: str):
            return {"version": "2024.1.0"}

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones.verify_ha_connection", new=_mock_verify_ha_connection),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
        ):
            response = await ha_zones_client.post("/api/v1/zones/zone-1/test")

            assert response.status_code == 200
            data = response.json()
            assert data["local_ok"] is True
            assert data["local_version"] == "2024.1.0"
            assert data["remote_ok"] is None  # No remote URL configured

    async def test_test_zone_with_remote(self, ha_zones_client, mock_zone_repo, mock_session):
        """Should test both local and remote URLs."""
        mock_zone_repo.get_connection = AsyncMock(
            return_value=(
                "http://localhost:8123",
                "https://example.com",
                "test_token",
                "auto",
            )
        )

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        def _get_session_factory():
            return _mock_get_session()

        async def _mock_verify_ha_connection(url: str, token: str):
            return {"version": "2024.1.0"}

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones.verify_ha_connection", new=_mock_verify_ha_connection),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
        ):
            response = await ha_zones_client.post("/api/v1/zones/zone-1/test")

            assert response.status_code == 200
            data = response.json()
            assert data["local_ok"] is True
            assert data["remote_ok"] is True
            assert data["local_version"] == "2024.1.0"
            assert data["remote_version"] == "2024.1.0"

    async def test_test_zone_connection_error(self, ha_zones_client, mock_zone_repo, mock_session):
        """Should handle connection errors gracefully."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        from fastapi import HTTPException

        async def _mock_verify_ha_connection(url: str, token: str):
            raise HTTPException(status_code=400, detail="Connection failed")

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones.verify_ha_connection", new=_mock_verify_ha_connection),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
        ):
            response = await ha_zones_client.post("/api/v1/zones/zone-1/test")

            assert response.status_code == 200
            data = response.json()
            assert data["local_ok"] is False
            assert data["local_error"] == "Connection failed"

    async def test_test_zone_not_found(self, ha_zones_client, mock_zone_repo, mock_session):
        """Should return 404 when zone not found."""
        mock_zone_repo.get_connection = AsyncMock(return_value=None)

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.ha_zones.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.ha_zones.HAZoneRepository", return_value=mock_zone_repo),
            patch("src.api.routes.ha_zones._get_secret", return_value="test_secret"),
        ):
            response = await ha_zones_client.post("/api/v1/zones/nonexistent/test")

            assert response.status_code == 404
