"""Unit tests for integration health diagnostics.

TDD: Tests written FIRST to define the API contract for
IntegrationHealth, get_integration_statuses, find_unhealthy_integrations,
and diagnose_integration.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.diagnostics.integration_health import (
    IntegrationHealth,
    diagnose_integration,
    find_unhealthy_integrations,
    get_integration_statuses,
)


def _mock_mcp_with_config_entries(entries: list[dict]) -> MagicMock:
    """Create mock MCP client with config entries."""
    mcp = MagicMock()
    mcp.list_config_entries = AsyncMock(return_value=entries)
    mcp.get_config_entry_diagnostics = AsyncMock(return_value=None)
    mcp.list_entities = AsyncMock(return_value=[])
    return mcp


class TestGetIntegrationStatuses:
    """Tests for get_integration_statuses."""

    @pytest.mark.asyncio
    async def test_returns_integration_health_list(self):
        """Test converting config entries to IntegrationHealth objects."""
        mcp = _mock_mcp_with_config_entries([
            {"entry_id": "abc", "domain": "zha", "title": "ZHA",
             "state": "loaded", "disabled_by": None, "reason": None},
            {"entry_id": "def", "domain": "mqtt", "title": "MQTT",
             "state": "loaded", "disabled_by": None, "reason": None},
        ])

        result = await get_integration_statuses(mcp)

        assert len(result) == 2
        assert all(isinstance(r, IntegrationHealth) for r in result)
        assert result[0].domain == "zha"
        assert result[0].state == "loaded"

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_entries(self):
        """Test empty config entries returns empty list."""
        mcp = _mock_mcp_with_config_entries([])

        result = await get_integration_statuses(mcp)

        assert result == []


class TestFindUnhealthyIntegrations:
    """Tests for find_unhealthy_integrations."""

    @pytest.mark.asyncio
    async def test_finds_errored_integrations(self):
        """Test filtering to integrations with error states."""
        mcp = _mock_mcp_with_config_entries([
            {"entry_id": "abc", "domain": "zha", "title": "ZHA",
             "state": "loaded", "disabled_by": None, "reason": None},
            {"entry_id": "def", "domain": "nest", "title": "Nest",
             "state": "setup_error", "disabled_by": None, "reason": "auth_expired"},
            {"entry_id": "ghi", "domain": "hue", "title": "Hue",
             "state": "not_loaded", "disabled_by": "user", "reason": None},
        ])

        result = await find_unhealthy_integrations(mcp)

        assert len(result) == 2  # nest (setup_error) + hue (not_loaded)
        domains = {r.domain for r in result}
        assert "nest" in domains
        assert "hue" in domains
        assert "zha" not in domains

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_healthy(self):
        """Test returns empty when all integrations are loaded."""
        mcp = _mock_mcp_with_config_entries([
            {"entry_id": "abc", "domain": "zha", "title": "ZHA",
             "state": "loaded", "disabled_by": None, "reason": None},
        ])

        result = await find_unhealthy_integrations(mcp)

        assert result == []


class TestDiagnoseIntegration:
    """Tests for diagnose_integration."""

    @pytest.mark.asyncio
    async def test_returns_full_diagnosis(self):
        """Test full integration diagnosis with diagnostics data."""
        mcp = MagicMock()
        mcp.list_config_entries = AsyncMock(return_value=[
            {"entry_id": "abc123", "domain": "zha", "title": "ZHA",
             "state": "setup_error", "disabled_by": None, "reason": "timeout"},
        ])
        mcp.get_config_entry_diagnostics = AsyncMock(return_value={
            "data": {"coordinator": {"status": "disconnected"}},
        })
        mcp.list_entities = AsyncMock(return_value=[
            {"entity_id": "sensor.zha_temp", "state": "unavailable",
             "last_changed": "2026-02-06T08:00:00Z", "attributes": {}},
        ])

        result = await diagnose_integration(mcp, "abc123")

        assert result["entry_id"] == "abc123"
        assert result["domain"] == "zha"
        assert result["state"] == "setup_error"
        assert result["diagnostics"] is not None
        assert "unavailable_entities" in result

    @pytest.mark.asyncio
    async def test_handles_missing_diagnostics(self):
        """Test diagnosis when integration doesn't support diagnostics."""
        mcp = MagicMock()
        mcp.list_config_entries = AsyncMock(return_value=[
            {"entry_id": "abc123", "domain": "mqtt", "title": "MQTT",
             "state": "loaded", "disabled_by": None, "reason": None},
        ])
        mcp.get_config_entry_diagnostics = AsyncMock(return_value=None)
        mcp.list_entities = AsyncMock(return_value=[])

        result = await diagnose_integration(mcp, "abc123")

        assert result["diagnostics"] is None
        assert result["unavailable_entities"] == []

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_entry(self):
        """Test returns None when entry_id doesn't exist."""
        mcp = MagicMock()
        mcp.list_config_entries = AsyncMock(return_value=[])

        result = await diagnose_integration(mcp, "nonexistent")

        assert result is None
