"""Unit tests for agent diagnostic tools.

TDD: Tests written FIRST to define the API contract for
analyze_error_log, find_unavailable_entities, diagnose_entity,
check_integration_health, and validate_config tools.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAnalyzeErrorLogTool:
    """Tests for analyze_error_log tool."""

    @pytest.mark.asyncio
    async def test_returns_structured_analysis(self):
        """Test analyzing error log returns parsed analysis."""
        from src.tools.diagnostic_tools import analyze_error_log

        mock_mcp = MagicMock()
        mock_mcp.get_error_log = AsyncMock(return_value=(
            "2026-02-06 10:00:00.000 ERROR (MainThread) [homeassistant.components.zha] "
            "Failed to connect to coordinator\n"
            "2026-02-06 10:01:00.000 ERROR (MainThread) [homeassistant.components.zha] "
            "Failed to connect to coordinator\n"
            "2026-02-06 10:02:00.000 WARNING (MainThread) [homeassistant.components.mqtt] "
            "Connection lost\n"
        ))

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await analyze_error_log.ainvoke({})

        assert "zha" in result.lower()
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_handles_empty_log(self):
        """Test handling when log is empty."""
        from src.tools.diagnostic_tools import analyze_error_log

        mock_mcp = MagicMock()
        mock_mcp.get_error_log = AsyncMock(return_value="")

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await analyze_error_log.ainvoke({})

        assert "no errors" in result.lower() or "clean" in result.lower()

    @pytest.mark.asyncio
    async def test_handles_mcp_failure(self):
        """Test error handling when MCP fails."""
        from src.tools.diagnostic_tools import analyze_error_log

        mock_mcp = MagicMock()
        mock_mcp.get_error_log = AsyncMock(side_effect=Exception("Connection failed"))

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await analyze_error_log.ainvoke({})

        assert "failed" in result.lower() or "error" in result.lower()


class TestFindUnavailableEntitiesTool:
    """Tests for find_unavailable_entities tool."""

    @pytest.mark.asyncio
    async def test_lists_unavailable_with_grouping(self):
        """Test finding and grouping unavailable entities."""
        from src.tools.diagnostic_tools import find_unavailable_entities_tool

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value=[
            {"entity_id": "sensor.zha_temp", "state": "unavailable",
             "last_changed": "2026-02-06T08:00:00Z", "attributes": {}},
            {"entity_id": "sensor.zha_motion", "state": "unavailable",
             "last_changed": "2026-02-06T08:00:00Z", "attributes": {}},
            {"entity_id": "light.kitchen", "state": "on",
             "last_changed": "2026-02-06T10:00:00Z", "attributes": {}},
        ])

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await find_unavailable_entities_tool.ainvoke({})

        assert "2" in result  # 2 unavailable entities
        assert "sensor" in result.lower()

    @pytest.mark.asyncio
    async def test_all_healthy(self):
        """Test when all entities are healthy."""
        from src.tools.diagnostic_tools import find_unavailable_entities_tool

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value=[
            {"entity_id": "light.kitchen", "state": "on",
             "last_changed": "2026-02-06T10:00:00Z", "attributes": {}},
        ])

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await find_unavailable_entities_tool.ainvoke({})

        assert "no unavailable" in result.lower() or "all" in result.lower()


class TestDiagnoseEntityTool:
    """Tests for diagnose_entity tool."""

    @pytest.mark.asyncio
    async def test_returns_entity_deep_dive(self):
        """Test deep-dive diagnosis of a single entity."""
        from src.tools.diagnostic_tools import diagnose_entity

        mock_mcp = MagicMock()
        mock_mcp.get_entity = AsyncMock(return_value={
            "entity_id": "sensor.broken",
            "state": "unavailable",
            "attributes": {"friendly_name": "Broken Sensor", "device_class": "temperature"},
            "last_changed": "2026-02-06T08:00:00Z",
        })
        mock_mcp.get_history = AsyncMock(return_value={
            "states": [
                {"state": "22.5", "last_changed": "2026-02-06T06:00:00Z"},
                {"state": "unavailable", "last_changed": "2026-02-06T08:00:00Z"},
            ],
            "count": 2,
        })
        mock_mcp.get_error_log = AsyncMock(return_value="")

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await diagnose_entity.ainvoke({"entity_id": "sensor.broken"})

        assert "sensor.broken" in result
        assert "unavailable" in result.lower()

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        """Test when entity doesn't exist."""
        from src.tools.diagnostic_tools import diagnose_entity

        mock_mcp = MagicMock()
        mock_mcp.get_entity = AsyncMock(return_value=None)

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await diagnose_entity.ainvoke({"entity_id": "sensor.nonexistent"})

        assert "not found" in result.lower()


class TestCheckIntegrationHealthTool:
    """Tests for check_integration_health tool."""

    @pytest.mark.asyncio
    async def test_returns_health_report(self):
        """Test integration health report."""
        from src.tools.diagnostic_tools import check_integration_health

        mock_mcp = MagicMock()
        mock_mcp.list_config_entries = AsyncMock(return_value=[
            {"entry_id": "abc", "domain": "zha", "title": "ZHA",
             "state": "loaded", "disabled_by": None, "reason": None},
            {"entry_id": "def", "domain": "nest", "title": "Nest",
             "state": "setup_error", "disabled_by": None, "reason": "auth_expired"},
        ])

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await check_integration_health.ainvoke({})

        assert "nest" in result.lower()
        assert "setup_error" in result.lower() or "unhealthy" in result.lower()

    @pytest.mark.asyncio
    async def test_all_healthy(self):
        """Test when all integrations are healthy."""
        from src.tools.diagnostic_tools import check_integration_health

        mock_mcp = MagicMock()
        mock_mcp.list_config_entries = AsyncMock(return_value=[
            {"entry_id": "abc", "domain": "zha", "title": "ZHA",
             "state": "loaded", "disabled_by": None, "reason": None},
        ])

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await check_integration_health.ainvoke({})

        assert "healthy" in result.lower() or "no issues" in result.lower()


class TestValidateConfigTool:
    """Tests for validate_config tool."""

    @pytest.mark.asyncio
    async def test_valid_config(self):
        """Test valid config check."""
        from src.tools.diagnostic_tools import validate_config

        mock_mcp = MagicMock()
        mock_mcp.check_config = AsyncMock(return_value={"result": "valid"})

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await validate_config.ainvoke({})

        assert "valid" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_config(self):
        """Test invalid config check."""
        from src.tools.diagnostic_tools import validate_config

        mock_mcp = MagicMock()
        mock_mcp.check_config = AsyncMock(return_value={
            "result": "invalid",
            "errors": "Integration error: bad config",
        })

        with patch("src.tools.diagnostic_tools.get_ha_client", return_value=mock_mcp):
            result = await validate_config.ainvoke({})

        assert "invalid" in result.lower() or "error" in result.lower()


class TestGetDiagnosticTools:
    """Tests for get_diagnostic_tools registry function."""

    def test_returns_all_tools(self):
        """Test that get_diagnostic_tools returns all 5 tools."""
        from src.tools.diagnostic_tools import get_diagnostic_tools

        tools = get_diagnostic_tools()

        assert len(tools) == 5
        tool_names = {t.name for t in tools}
        assert "analyze_error_log" in tool_names
        assert "find_unavailable_entities" in tool_names
        assert "diagnose_entity" in tool_names
        assert "check_integration_health" in tool_names
        assert "validate_config" in tool_names
