"""Unit tests for POST /registry/sync endpoint.

Tests the registry sync API endpoint including:
- Successful sync returns stats
- MCP error handling (500)
- Response schema validation

Constitution: Reliability & Quality - comprehensive API testing.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.api.main import create_app
from src.settings import get_settings


@pytest.fixture
async def client(mock_settings, monkeypatch):
    """Create test client with auth disabled for registry tests."""
    get_settings.cache_clear()

    mock_settings.api_key = SecretStr("")

    from src import settings as settings_module
    monkeypatch.setattr(settings_module, "get_settings", lambda: mock_settings)

    app = create_app(mock_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    get_settings.cache_clear()


class TestRegistrySyncEndpoint:
    """Tests for POST /api/v1/registry/sync."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_returns_stats(self, client):
        """Test successful sync returns automations/scripts/scenes counts."""
        mock_result = {
            "automations_synced": 12,
            "scripts_synced": 5,
            "scenes_synced": 3,
            "duration_seconds": 1.23,
        }

        with patch("src.api.routes.ha_registry.run_registry_sync", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = mock_result

            response = await client.post("/api/v1/registry/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["automations_synced"] == 12
        assert data["scripts_synced"] == 5
        assert data["scenes_synced"] == 3
        assert data["duration_seconds"] == 1.23

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_handles_mcp_error(self, client):
        """Test that MCP failures return 500."""
        with patch("src.api.routes.ha_registry.run_registry_sync", new_callable=AsyncMock) as mock_sync:
            mock_sync.side_effect = Exception("MCP connection failed")

            response = await client.post("/api/v1/registry/sync")

        assert response.status_code == 500
        assert "MCP connection failed" in response.json()["detail"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_response_schema(self, client):
        """Test response contains all expected fields."""
        mock_result = {
            "automations_synced": 0,
            "scripts_synced": 0,
            "scenes_synced": 0,
            "duration_seconds": 0.05,
        }

        with patch("src.api.routes.ha_registry.run_registry_sync", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = mock_result

            response = await client.post("/api/v1/registry/sync")

        data = response.json()
        assert "automations_synced" in data
        assert "scripts_synced" in data
        assert "scenes_synced" in data
        assert "duration_seconds" in data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_with_auth_required(self, mock_settings, monkeypatch):
        """Test that sync endpoint requires auth when API key is configured."""
        get_settings.cache_clear()

        mock_settings.api_key = SecretStr("test-api-key-123")

        from src import settings as settings_module
        monkeypatch.setattr(settings_module, "get_settings", lambda: mock_settings)

        app = create_app(mock_settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as authed_client:
            # No API key provided - should get 403
            response = await authed_client.post("/api/v1/registry/sync")
            assert response.status_code == 403

            # With correct API key - should succeed
            with patch("src.api.routes.ha_registry.run_registry_sync", new_callable=AsyncMock) as mock_sync:
                mock_sync.return_value = {
                    "automations_synced": 0,
                    "scripts_synced": 0,
                    "scenes_synced": 0,
                    "duration_seconds": 0.01,
                }
                response = await authed_client.post(
                    "/api/v1/registry/sync",
                    headers={"X-API-Key": "test-api-key-123"},
                )
                assert response.status_code == 200

        get_settings.cache_clear()
