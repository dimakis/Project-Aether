"""Tests for HA dashboard mixin (list_dashboards, get_dashboard_config).

Validates the HAClient methods for fetching Lovelace dashboard
metadata and full configuration from Home Assistant.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.ha.base import HAClientConfig


def _make_client():
    """Create an HAClient with a dummy config (no real connection)."""
    from src.ha.client import HAClient

    config = HAClientConfig(
        ha_url="http://ha.local:8123",
        ha_token="test-token",
    )
    return HAClient(config=config)


class TestListDashboards:
    """Tests for DashboardMixin.list_dashboards."""

    @pytest.mark.asyncio
    async def test_returns_dashboard_list(self):
        """list_dashboards returns the list from HA API."""
        client = _make_client()
        expected = [
            {"id": "abc123", "title": "Home", "mode": "storage", "url_path": "lovelace"},
            {"id": "def456", "title": "Energy", "mode": "yaml", "url_path": "energy"},
        ]
        client._request = AsyncMock(return_value=expected)

        result = await client.list_dashboards()

        assert result == expected
        client._request.assert_called_once_with("GET", "/api/lovelace/dashboards")

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_none(self):
        """list_dashboards returns [] when HA returns None."""
        client = _make_client()
        client._request = AsyncMock(return_value=None)

        result = await client.list_dashboards()

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_error(self):
        """list_dashboards returns [] on request failure."""
        client = _make_client()
        client._request = AsyncMock(side_effect=Exception("connection failed"))

        result = await client.list_dashboards()

        assert result == []


class TestGetDashboardConfig:
    """Tests for DashboardMixin.get_dashboard_config."""

    @pytest.mark.asyncio
    async def test_fetches_default_dashboard_config(self):
        """get_dashboard_config(None) fetches default dashboard."""
        client = _make_client()
        expected = {
            "title": "Home",
            "views": [{"title": "Overview", "cards": []}],
        }
        client._request = AsyncMock(return_value=expected)

        result = await client.get_dashboard_config()

        assert result == expected
        client._request.assert_called_once_with("GET", "/api/lovelace/config")

    @pytest.mark.asyncio
    async def test_fetches_specific_dashboard_config(self):
        """get_dashboard_config('energy') fetches that dashboard."""
        client = _make_client()
        expected = {
            "title": "Energy",
            "views": [{"title": "Solar", "cards": []}],
        }
        client._request = AsyncMock(return_value=expected)

        result = await client.get_dashboard_config("energy")

        assert result == expected
        client._request.assert_called_once_with("GET", "/api/lovelace/config/energy")

    @pytest.mark.asyncio
    async def test_returns_none_on_not_found(self):
        """get_dashboard_config returns None when HA returns None (404)."""
        client = _make_client()
        client._request = AsyncMock(return_value=None)

        result = await client.get_dashboard_config("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_raises_on_error(self):
        """get_dashboard_config propagates exceptions."""
        from src.exceptions import HAClientError

        client = _make_client()
        client._request = AsyncMock(side_effect=HAClientError("fail", "test"))

        with pytest.raises(HAClientError):
            await client.get_dashboard_config()
