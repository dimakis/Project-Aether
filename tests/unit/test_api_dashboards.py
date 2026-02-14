"""Unit tests for dashboard API endpoints.

Tests the /api/v1/dashboards/* endpoints that proxy to HA's
Lovelace API for listing dashboards and fetching configs.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.api.main import create_app
from src.settings import Settings, get_settings

JWT_SECRET = "test-jwt-secret-key-for-testing-minimum-32bytes"


def _make_settings(**overrides) -> Settings:
    defaults = {
        "environment": "testing",
        "debug": True,
        "database_url": "postgresql+asyncpg://test:test@localhost:5432/aether_test",
        "ha_url": "http://localhost:8123",
        "ha_token": SecretStr("test-token"),
        "openai_api_key": SecretStr("test-api-key"),
        "mlflow_tracking_uri": "http://localhost:5000",
        "sandbox_enabled": False,
        "auth_username": "admin",
        "auth_password": SecretStr("test-password"),
        "jwt_secret": SecretStr(JWT_SECRET),
        "api_key": SecretStr(""),
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_jwt() -> str:
    payload = {
        "sub": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 72 * 3600,
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture
async def client(monkeypatch):
    """Test client with auth configured."""
    get_settings.cache_clear()
    settings = _make_settings()
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    get_settings.cache_clear()


@pytest.mark.asyncio
class TestListDashboards:
    """Test GET /api/v1/dashboards."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/dashboards")
        assert response.status_code == 401

    async def test_returns_dashboard_list(self, client: AsyncClient):
        token = _make_jwt()
        mock_dashboards = [
            {"id": "abc123", "title": "Home", "mode": "storage", "url_path": "lovelace"},
            {"id": "def456", "title": "Energy", "mode": "yaml", "url_path": "energy"},
        ]

        with patch("src.api.routes.dashboards.get_ha_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.list_dashboards = AsyncMock(return_value=mock_dashboards)
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/v1/dashboards",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Home"
        assert data[1]["url_path"] == "energy"

    async def test_returns_empty_list(self, client: AsyncClient):
        token = _make_jwt()

        with patch("src.api.routes.dashboards.get_ha_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.list_dashboards = AsyncMock(return_value=[])
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/v1/dashboards",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
class TestGetDashboardConfig:
    """Test GET /api/v1/dashboards/{url_path}/config."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/dashboards/lovelace/config")
        assert response.status_code == 401

    async def test_returns_config(self, client: AsyncClient):
        token = _make_jwt()
        mock_config = {
            "title": "Home",
            "views": [{"title": "Overview", "cards": []}],
        }

        with patch("src.api.routes.dashboards.get_ha_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_dashboard_config = AsyncMock(return_value=mock_config)
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/v1/dashboards/lovelace/config",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Home"
        assert len(data["views"]) == 1

    async def test_default_dashboard_config(self, client: AsyncClient):
        token = _make_jwt()
        mock_config = {"title": "Default", "views": []}

        with patch("src.api.routes.dashboards.get_ha_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_dashboard_config = AsyncMock(return_value=mock_config)
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/v1/dashboards/default/config",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        # "default" should be mapped to None for the HA API call
        mock_client.get_dashboard_config.assert_called_once_with(None)

    async def test_not_found(self, client: AsyncClient):
        token = _make_jwt()

        with patch("src.api.routes.dashboards.get_ha_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_dashboard_config = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/v1/dashboards/nonexistent/config",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 404
