"""Tests for HA dashboard mixin (list_dashboards, get_dashboard_config, save).

Validates the HAClient methods for fetching/saving Lovelace dashboard
configuration from Home Assistant, including WebSocket primary path
and REST fallback.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions import HAClientError
from src.ha.base import HAClientConfig


def _make_client():
    """Create an HAClient with a dummy config (no real connection)."""
    from src.ha.client import HAClient

    config = HAClientConfig(
        ha_url="http://ha.local:8123",
        ha_token="test-token",
    )
    return HAClient(config=config)


# ---------------------------------------------------------------------------
# _get_ws_url
# ---------------------------------------------------------------------------


class TestGetWsUrl:
    """Tests for BaseHAClient._get_ws_url."""

    def test_http_to_ws(self):
        """http:// URL is converted to ws:// with /api/websocket."""
        client = _make_client()
        assert client._get_ws_url() == "ws://ha.local:8123/api/websocket"

    def test_https_to_wss(self):
        """https:// URL is converted to wss://."""
        config = HAClientConfig(
            ha_url="https://ha.example.com",
            ha_token="test-token",
        )
        from src.ha.client import HAClient

        client = HAClient(config=config)
        assert client._get_ws_url() == "wss://ha.example.com/api/websocket"

    def test_uses_active_url(self):
        """_get_ws_url uses _active_url when set (from previous successful request)."""
        client = _make_client()
        client._active_url = "http://192.168.1.100:8123"
        assert client._get_ws_url() == "ws://192.168.1.100:8123/api/websocket"

    def test_trailing_slash_stripped(self):
        """Trailing slash on URL should not produce double slashes."""
        config = HAClientConfig(
            ha_url="http://ha.local:8123/",
            ha_token="test-token",
        )
        from src.ha.client import HAClient

        client = HAClient(config=config)
        assert client._get_ws_url() == "ws://ha.local:8123/api/websocket"


# ---------------------------------------------------------------------------
# list_dashboards (REST — unchanged)
# ---------------------------------------------------------------------------


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
    async def test_propagates_error(self):
        """list_dashboards propagates exceptions to the caller."""
        client = _make_client()
        client._request = AsyncMock(side_effect=Exception("connection failed"))

        with pytest.raises(Exception, match="connection failed"):
            await client.list_dashboards()


# ---------------------------------------------------------------------------
# get_dashboard_config (WebSocket primary, REST fallback)
# ---------------------------------------------------------------------------


class TestGetDashboardConfig:
    """Tests for DashboardMixin.get_dashboard_config."""

    @pytest.mark.asyncio
    async def test_fetches_default_via_websocket(self):
        """get_dashboard_config(None) uses WebSocket with url_path=None."""
        client = _make_client()
        expected = {
            "title": "Home",
            "views": [{"title": "Overview", "cards": []}],
        }

        with patch("src.ha.dashboards.ws_command", new_callable=AsyncMock) as mock_ws:
            mock_ws.return_value = expected
            result = await client.get_dashboard_config()

        assert result == expected
        mock_ws.assert_called_once_with(
            "ws://ha.local:8123/api/websocket",
            "test-token",
            "lovelace/config",
            url_path=None,
            force=False,
        )

    @pytest.mark.asyncio
    async def test_fetches_specific_via_websocket(self):
        """get_dashboard_config('energy') passes url_path to WebSocket."""
        client = _make_client()
        expected = {"title": "Energy", "views": []}

        with patch("src.ha.dashboards.ws_command", new_callable=AsyncMock) as mock_ws:
            mock_ws.return_value = expected
            result = await client.get_dashboard_config("energy")

        assert result == expected
        mock_ws.assert_called_once_with(
            "ws://ha.local:8123/api/websocket",
            "test-token",
            "lovelace/config",
            url_path="energy",
            force=False,
        )

    @pytest.mark.asyncio
    async def test_falls_back_to_rest_on_ws_error(self):
        """When WebSocket fails, falls back to REST API."""
        client = _make_client()
        expected = {"title": "Home", "views": []}

        with patch(
            "src.ha.dashboards.ws_command",
            new_callable=AsyncMock,
            side_effect=HAClientError("ws failed"),
        ):
            client._request = AsyncMock(return_value=expected)
            result = await client.get_dashboard_config()

        assert result == expected
        client._request.assert_called_once_with("GET", "/api/lovelace/config")

    @pytest.mark.asyncio
    async def test_falls_back_to_rest_specific_path(self):
        """REST fallback uses the correct path for specific dashboards."""
        client = _make_client()
        expected = {"title": "Energy", "views": []}

        with patch(
            "src.ha.dashboards.ws_command",
            new_callable=AsyncMock,
            side_effect=HAClientError("ws failed"),
        ):
            client._request = AsyncMock(return_value=expected)
            result = await client.get_dashboard_config("energy")

        assert result == expected
        client._request.assert_called_once_with("GET", "/api/lovelace/config/energy")

    @pytest.mark.asyncio
    async def test_returns_none_when_both_fail(self):
        """Returns None when WebSocket errors and REST returns None (404)."""
        client = _make_client()

        with patch(
            "src.ha.dashboards.ws_command",
            new_callable=AsyncMock,
            side_effect=HAClientError("ws failed"),
        ):
            client._request = AsyncMock(return_value=None)
            result = await client.get_dashboard_config("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_raises_on_both_fail_hard(self):
        """Raises HAClientError when both WebSocket and REST raise."""
        client = _make_client()

        with patch(
            "src.ha.dashboards.ws_command",
            new_callable=AsyncMock,
            side_effect=HAClientError("ws failed"),
        ):
            client._request = AsyncMock(side_effect=HAClientError("rest failed", "test"))
            with pytest.raises(HAClientError):
                await client.get_dashboard_config()


# ---------------------------------------------------------------------------
# save_dashboard_config (WebSocket only)
# ---------------------------------------------------------------------------


class TestSaveDashboardConfig:
    """Tests for DashboardMixin.save_dashboard_config."""

    @pytest.mark.asyncio
    async def test_saves_default_dashboard(self):
        """save_dashboard_config(None, config) sends lovelace/config/save."""
        client = _make_client()
        config = {"views": [{"title": "New"}]}

        with patch("src.ha.dashboards.ws_command", new_callable=AsyncMock) as mock_ws:
            mock_ws.return_value = None
            await client.save_dashboard_config(None, config)

        mock_ws.assert_called_once_with(
            "ws://ha.local:8123/api/websocket",
            "test-token",
            "lovelace/config/save",
            url_path=None,
            config=config,
        )

    @pytest.mark.asyncio
    async def test_saves_specific_dashboard(self):
        """save_dashboard_config('energy', config) sends with url_path."""
        client = _make_client()
        config = {"views": [{"title": "Solar"}]}

        with patch("src.ha.dashboards.ws_command", new_callable=AsyncMock) as mock_ws:
            mock_ws.return_value = None
            await client.save_dashboard_config("energy", config)

        mock_ws.assert_called_once_with(
            "ws://ha.local:8123/api/websocket",
            "test-token",
            "lovelace/config/save",
            url_path="energy",
            config=config,
        )

    @pytest.mark.asyncio
    async def test_save_raises_on_error(self):
        """save_dashboard_config propagates HAClientError."""
        client = _make_client()

        with patch(
            "src.ha.dashboards.ws_command",
            new_callable=AsyncMock,
            side_effect=HAClientError("write failed"),
        ):
            with pytest.raises(HAClientError, match="write failed"):
                await client.save_dashboard_config(None, {"views": []})
