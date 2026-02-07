"""Unit tests for MCP client diagnostic methods.

TDD: Tests written FIRST to define the API contract for diagnostic
MCP methods (list_config_entries, get_config_entry_diagnostics,
reload_config_entry, list_services, list_event_types).
"""

from unittest.mock import AsyncMock

import pytest

from src.mcp.client import MCPClient, MCPClientConfig, MCPError


def _make_client() -> MCPClient:
    """Create an MCPClient with test config."""
    return MCPClient(MCPClientConfig(
        ha_url="http://localhost:8123",
        ha_token="test-token",
    ))


class TestListConfigEntries:
    """Tests for MCPClient.list_config_entries."""

    @pytest.mark.asyncio
    async def test_returns_integration_list(self):
        """Test listing all integration config entries."""
        client = _make_client()
        client._request = AsyncMock(return_value=[
            {
                "entry_id": "abc123",
                "domain": "zha",
                "title": "Zigbee Home Automation",
                "state": "loaded",
                "disabled_by": None,
            },
            {
                "entry_id": "def456",
                "domain": "mqtt",
                "title": "MQTT",
                "state": "loaded",
                "disabled_by": None,
            },
        ])

        result = await client.list_config_entries()

        assert len(result) == 2
        assert result[0]["domain"] == "zha"
        assert result[1]["entry_id"] == "def456"
        client._request.assert_called_once_with("GET", "/api/config/config_entries")

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self):
        """Test handling when no config entries exist."""
        client = _make_client()
        client._request = AsyncMock(return_value=None)

        result = await client.list_config_entries()

        assert result == []

    @pytest.mark.asyncio
    async def test_filters_by_domain(self):
        """Test filtering config entries by domain."""
        client = _make_client()
        client._request = AsyncMock(return_value=[
            {"entry_id": "abc", "domain": "zha", "title": "ZHA", "state": "loaded"},
            {"entry_id": "def", "domain": "mqtt", "title": "MQTT", "state": "loaded"},
            {"entry_id": "ghi", "domain": "zha", "title": "ZHA 2", "state": "loaded"},
        ])

        result = await client.list_config_entries(domain="zha")

        assert len(result) == 2
        assert all(e["domain"] == "zha" for e in result)


class TestGetConfigEntryDiagnostics:
    """Tests for MCPClient.get_config_entry_diagnostics."""

    @pytest.mark.asyncio
    async def test_returns_diagnostics(self):
        """Test fetching diagnostics for an integration."""
        client = _make_client()
        client._request = AsyncMock(return_value={
            "home_assistant": {"installation_type": "Home Assistant OS"},
            "data": {"config": {"host": "192.168.1.100"}},
        })

        result = await client.get_config_entry_diagnostics("abc123")

        assert result is not None
        assert "data" in result
        client._request.assert_called_once_with(
            "GET", "/api/config/config_entries/abc123/diagnostics"
        )

    @pytest.mark.asyncio
    async def test_returns_none_for_unsupported(self):
        """Test graceful handling when integration doesn't support diagnostics."""
        client = _make_client()
        client._request = AsyncMock(return_value=None)  # 404 -> None

        result = await client.get_config_entry_diagnostics("no_diag_entry")

        assert result is None


class TestReloadConfigEntry:
    """Tests for MCPClient.reload_config_entry."""

    @pytest.mark.asyncio
    async def test_reload_success(self):
        """Test successful integration reload."""
        client = _make_client()
        client._request = AsyncMock(return_value={
            "require_restart": False,
        })

        result = await client.reload_config_entry("abc123")

        assert result is not None
        client._request.assert_called_once_with(
            "POST", "/api/config/config_entries/entry/abc123/reload"
        )

    @pytest.mark.asyncio
    async def test_reload_failure_raises(self):
        """Test reload failure raises MCPError."""
        client = _make_client()
        client._request = AsyncMock(side_effect=MCPError(
            "All connection attempts failed", "request"
        ))

        with pytest.raises(MCPError):
            await client.reload_config_entry("bad_entry")


class TestListServices:
    """Tests for MCPClient.list_services."""

    @pytest.mark.asyncio
    async def test_returns_service_list(self):
        """Test listing available services."""
        client = _make_client()
        client._request = AsyncMock(return_value=[
            {
                "domain": "light",
                "services": {
                    "turn_on": {"description": "Turn on a light"},
                    "turn_off": {"description": "Turn off a light"},
                },
            },
            {
                "domain": "switch",
                "services": {
                    "toggle": {"description": "Toggle a switch"},
                },
            },
        ])

        result = await client.list_services()

        assert len(result) == 2
        assert result[0]["domain"] == "light"
        assert "turn_on" in result[0]["services"]
        client._request.assert_called_once_with("GET", "/api/services")

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self):
        """Test handling when no services available."""
        client = _make_client()
        client._request = AsyncMock(return_value=None)

        result = await client.list_services()

        assert result == []


class TestListEventTypes:
    """Tests for MCPClient.list_event_types."""

    @pytest.mark.asyncio
    async def test_returns_event_types(self):
        """Test listing event types."""
        client = _make_client()
        client._request = AsyncMock(return_value=[
            {"event_type": "state_changed", "listener_count": 50},
            {"event_type": "call_service", "listener_count": 10},
            {"event_type": "automation_triggered", "listener_count": 5},
        ])

        result = await client.list_event_types()

        assert len(result) == 3
        assert result[0]["event_type"] == "state_changed"
        client._request.assert_called_once_with("GET", "/api/events")

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self):
        """Test handling when no events available."""
        client = _make_client()
        client._request = AsyncMock(return_value=None)

        result = await client.list_event_types()

        assert result == []
