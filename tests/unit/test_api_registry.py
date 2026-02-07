"""Unit tests for registry sync endpoint handler and response model.

Tests the sync_registry route handler directly (not via HTTP)
to avoid app lifespan/DB issues in unit tests.

Constitution: Reliability & Quality - comprehensive API testing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient
from starlette.requests import Request as StarletteRequest

from src.api.routes.ha_registry import RegistrySyncResponse, sync_registry


def _make_request() -> StarletteRequest:
    """Create a minimal Starlette Request for rate-limiter compatibility."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/registry/sync",
        "headers": [],
        "query_string": b"",
        "root_path": "",
        "server": ("testserver", 80),
        "app": MagicMock(),
    }
    return StarletteRequest(scope)


class TestRegistrySyncEndpoint:
    """Tests for the sync_registry route handler."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_returns_stats(self):
        """Test successful sync returns automations/scripts/scenes counts."""
        mock_result = {
            "automations_synced": 12,
            "scripts_synced": 5,
            "scenes_synced": 3,
            "duration_seconds": 1.23,
        }

        mock_session = AsyncMock()

        with patch("src.api.routes.ha_registry.run_registry_sync", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = mock_result

            response = await sync_registry(request=_make_request(), session=mock_session)

        assert isinstance(response, RegistrySyncResponse)
        assert response.automations_synced == 12
        assert response.scripts_synced == 5
        assert response.scenes_synced == 3
        assert response.duration_seconds == 1.23

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_handles_mcp_error(self):
        """Test that MCP failures raise HTTPException with 500."""
        from fastapi import HTTPException

        mock_session = AsyncMock()

        with patch("src.api.routes.ha_registry.run_registry_sync", new_callable=AsyncMock) as mock_sync:
            mock_sync.side_effect = Exception("MCP connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await sync_registry(request=_make_request(), session=mock_session)

        assert exc_info.value.status_code == 500
        assert "MCP connection failed" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_response_schema(self):
        """Test response contains all expected fields."""
        mock_result = {
            "automations_synced": 0,
            "scripts_synced": 0,
            "scenes_synced": 0,
            "duration_seconds": 0.05,
        }

        mock_session = AsyncMock()

        with patch("src.api.routes.ha_registry.run_registry_sync", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = mock_result

            response = await sync_registry(request=_make_request(), session=mock_session)

        # Verify all fields present via Pydantic model
        assert hasattr(response, "automations_synced")
        assert hasattr(response, "scripts_synced")
        assert hasattr(response, "scenes_synced")
        assert hasattr(response, "duration_seconds")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_passes_session_to_run_registry_sync(self):
        """Test that the DB session is passed to the sync function."""
        mock_session = AsyncMock()

        with patch("src.api.routes.ha_registry.run_registry_sync", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                "automations_synced": 0,
                "scripts_synced": 0,
                "scenes_synced": 0,
                "duration_seconds": 0.01,
            }

            await sync_registry(request=_make_request(), session=mock_session)

        mock_sync.assert_called_once_with(session=mock_session)


class TestRegistrySyncResponseModel:
    """Tests for the RegistrySyncResponse Pydantic model."""

    @pytest.mark.unit
    def test_valid_response(self):
        """Test valid response creation."""
        response = RegistrySyncResponse(
            automations_synced=5,
            scripts_synced=3,
            scenes_synced=2,
            duration_seconds=1.5,
        )
        assert response.automations_synced == 5
        assert response.scripts_synced == 3
        assert response.scenes_synced == 2
        assert response.duration_seconds == 1.5

    @pytest.mark.unit
    def test_serialization(self):
        """Test response serializes to expected JSON structure."""
        response = RegistrySyncResponse(
            automations_synced=10,
            scripts_synced=4,
            scenes_synced=6,
            duration_seconds=2.34,
        )
        data = response.model_dump()
        assert data == {
            "automations_synced": 10,
            "scripts_synced": 4,
            "scenes_synced": 6,
            "duration_seconds": 2.34,
        }
