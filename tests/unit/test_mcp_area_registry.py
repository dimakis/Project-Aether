"""Unit tests for HA area registry direct API access.

Tests the HAClient.get_area_registry method which fetches areas
directly from the HA REST API (bypassing MCP tool limitations).
"""

from unittest.mock import AsyncMock

import pytest

from src.ha.client import HAClient, HAClientConfig


@pytest.fixture
def ha_client():
    """Create an HA client with mocked _request."""
    client = HAClient(HAClientConfig(
        ha_url="http://localhost:8123",
        ha_token="test-token",
    ))
    return client


class TestGetAreaRegistry:
    """Tests for HAClient.get_area_registry."""

    @pytest.mark.asyncio
    async def test_returns_area_list(self, ha_client):
        """Test that get_area_registry returns parsed area list from HA."""
        ha_client._request = AsyncMock(return_value=[
            {
                "area_id": "living_room",
                "name": "Living Room",
                "floor_id": "ground_floor",
                "icon": "mdi:sofa",
                "picture": None,
                "aliases": [],
            },
            {
                "area_id": "bedroom",
                "name": "Bedroom",
                "floor_id": "first_floor",
                "icon": None,
                "picture": "/local/bedroom.jpg",
                "aliases": ["Master Bedroom"],
            },
        ])

        areas = await ha_client.get_area_registry()

        assert len(areas) == 2
        assert areas[0]["area_id"] == "living_room"
        assert areas[0]["name"] == "Living Room"
        assert areas[0]["floor_id"] == "ground_floor"
        assert areas[0]["icon"] == "mdi:sofa"
        assert areas[1]["area_id"] == "bedroom"
        assert areas[1]["picture"] == "/local/bedroom.jpg"

        # Verify correct API endpoint called
        ha_client._request.assert_called_once_with(
            "GET", "/api/config/area_registry/list"
        )

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_none(self, ha_client):
        """Test graceful handling when HA returns None (404)."""
        ha_client._request = AsyncMock(return_value=None)

        areas = await ha_client.get_area_registry()

        assert areas == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_error(self, ha_client):
        """Test graceful fallback on connection error."""
        from src.ha.base import HAClientError

        ha_client._request = AsyncMock(side_effect=HAClientError("Connection failed", "request"))

        areas = await ha_client.get_area_registry()

        assert areas == []
