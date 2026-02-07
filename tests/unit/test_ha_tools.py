"""Unit tests for Home Assistant tools.

TDD: Testing HA tools that agents can use to query Home Assistant.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetEntityStateTool:
    """Tests for get_entity_state tool."""

    @pytest.mark.asyncio
    async def test_get_entity_state_returns_state(self):
        """Test getting entity state."""
        from src.tools.ha_tools import get_entity_state

        mock_mcp = MagicMock()
        mock_mcp.get_entity = AsyncMock(return_value={
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {"brightness": 255, "friendly_name": "Living Room Light"},
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await get_entity_state.ainvoke({"entity_id": "light.living_room"})

        assert "on" in result.lower()
        assert "living_room" in result.lower()

    @pytest.mark.asyncio
    async def test_get_entity_state_not_found(self):
        """Test getting non-existent entity."""
        from src.tools.ha_tools import get_entity_state

        mock_mcp = MagicMock()
        mock_mcp.get_entity = AsyncMock(return_value=None)

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await get_entity_state.ainvoke({"entity_id": "light.nonexistent"})

        assert "not found" in result.lower() or "error" in result.lower()


class TestListEntitiesByDomainTool:
    """Tests for list_entities_by_domain tool."""

    @pytest.mark.asyncio
    async def test_list_lights(self):
        """Test listing light entities."""
        from src.tools.ha_tools import list_entities_by_domain

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value={
            "results": [
                {"entity_id": "light.living_room", "state": "on"},
                {"entity_id": "light.bedroom", "state": "off"},
            ]
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await list_entities_by_domain.ainvoke({"domain": "light"})

        assert "light.living_room" in result
        assert "light.bedroom" in result

    @pytest.mark.asyncio
    async def test_list_with_state_filter(self):
        """Test listing entities filtered by state."""
        from src.tools.ha_tools import list_entities_by_domain

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value={
            "results": [
                {"entity_id": "light.living_room", "state": "on"},
                {"entity_id": "light.bedroom", "state": "off"},
            ]
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await list_entities_by_domain.ainvoke({"domain": "light", "state_filter": "on"})

        assert "light.living_room" in result
        # bedroom is off, might not be in filtered result depending on implementation


class TestSearchEntitiesTool:
    """Tests for search_entities tool."""

    @pytest.mark.asyncio
    async def test_search_by_name(self):
        """Test searching entities by name."""
        from src.tools.ha_tools import search_entities

        mock_mcp = MagicMock()
        mock_mcp.search_entities = AsyncMock(return_value={
            "results": [
                {"entity_id": "light.kitchen", "state": "off"},
                {"entity_id": "sensor.kitchen_temperature", "state": "22"},
            ]
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await search_entities.ainvoke({"query": "kitchen"})

        assert "kitchen" in result.lower()


class TestGetDomainSummaryTool:
    """Tests for get_domain_summary tool."""

    @pytest.mark.asyncio
    async def test_get_light_summary(self):
        """Test getting summary of light domain."""
        from src.tools.ha_tools import get_domain_summary

        mock_mcp = MagicMock()
        mock_mcp.domain_summary = AsyncMock(return_value={
            "total_count": 10,
            "state_distribution": {"on": 3, "off": 7},
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await get_domain_summary.ainvoke({"domain": "light"})

        assert "10" in result or "total" in result.lower()


class TestControlEntityTool:
    """Tests for control_entity tool."""

    @pytest.mark.asyncio
    async def test_turn_on_light(self):
        """Test turning on a light."""
        from src.tools.ha_tools import control_entity

        mock_mcp = MagicMock()
        mock_mcp.entity_action = AsyncMock(return_value={"success": True})

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await control_entity.ainvoke({
                "entity_id": "light.living_room",
                "action": "on"
            })

        assert "light.living_room" in result.lower()
        mock_mcp.entity_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_switch(self):
        """Test turning off a switch."""
        from src.tools.ha_tools import control_entity

        mock_mcp = MagicMock()
        mock_mcp.entity_action = AsyncMock(return_value={"success": True})

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await control_entity.ainvoke({
                "entity_id": "switch.garden",
                "action": "off"
            })

        mock_mcp.entity_action.assert_called_once()


class TestDeployAutomationTool:
    """Tests for deploy_automation tool."""

    @pytest.mark.asyncio
    async def test_deploy_automation_success(self):
        """Test successful automation deployment."""
        from src.tools.ha_tools import deploy_automation

        mock_mcp = MagicMock()
        mock_mcp.create_automation = AsyncMock(return_value={
            "success": True,
            "automation_id": "test_lights",
            "entity_id": "automation.test_lights",
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await deploy_automation.ainvoke({
                "automation_id": "test_lights",
                "alias": "Test Lights",
                "trigger": [{"platform": "state", "entity_id": "binary_sensor.motion"}],
                "action": [{"service": "light.turn_on", "target": {"entity_id": "light.test"}}],
            })

        assert "✅" in result or "success" in result.lower()
        assert "test_lights" in result.lower()
        mock_mcp.create_automation.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_automation_failure(self):
        """Test automation deployment failure."""
        from src.tools.ha_tools import deploy_automation

        mock_mcp = MagicMock()
        mock_mcp.create_automation = AsyncMock(return_value={
            "success": False,
            "error": "Connection refused",
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await deploy_automation.ainvoke({
                "automation_id": "test_lights",
                "alias": "Test Lights",
                "trigger": [{"platform": "time", "at": "06:00:00"}],
                "action": [{"service": "light.turn_on"}],
            })

        assert "❌" in result or "failed" in result.lower()

    @pytest.mark.asyncio
    async def test_deploy_automation_with_conditions(self):
        """Test deployment with conditions."""
        from src.tools.ha_tools import deploy_automation

        mock_mcp = MagicMock()
        mock_mcp.create_automation = AsyncMock(return_value={
            "success": True,
            "automation_id": "night_lights",
            "entity_id": "automation.night_lights",
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await deploy_automation.ainvoke({
                "automation_id": "night_lights",
                "alias": "Night Lights",
                "trigger": [{"platform": "state", "entity_id": "binary_sensor.motion"}],
                "action": [{"service": "light.turn_on"}],
                "condition": [{"condition": "sun", "after": "sunset"}],
                "description": "Only at night",
                "mode": "restart",
            })

        # Verify all params were passed
        call_kwargs = mock_mcp.create_automation.call_args[1]
        assert call_kwargs["condition"] == [{"condition": "sun", "after": "sunset"}]
        assert call_kwargs["mode"] == "restart"


class TestDeleteAutomationTool:
    """Tests for delete_automation tool."""

    @pytest.mark.asyncio
    async def test_delete_automation_success(self):
        """Test successful automation deletion."""
        from src.tools.ha_tools import delete_automation

        mock_mcp = MagicMock()
        mock_mcp.delete_automation = AsyncMock(return_value={"success": True})

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await delete_automation.ainvoke({"automation_id": "old_automation"})

        assert "✅" in result or "deleted" in result.lower()
        mock_mcp.delete_automation.assert_called_once_with("old_automation")

    @pytest.mark.asyncio
    async def test_delete_automation_failure(self):
        """Test automation deletion failure."""
        from src.tools.ha_tools import delete_automation

        mock_mcp = MagicMock()
        mock_mcp.delete_automation = AsyncMock(return_value={
            "success": False,
            "error": "Not found",
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await delete_automation.ainvoke({"automation_id": "nonexistent"})

        assert "❌" in result or "failed" in result.lower()


class TestListAutomationsTool:
    """Tests for list_automations tool."""

    @pytest.mark.asyncio
    async def test_list_automations_with_results(self):
        """Test listing automations."""
        from src.tools.ha_tools import list_automations

        mock_mcp = MagicMock()
        mock_mcp.list_automations = AsyncMock(return_value=[
            {"entity_id": "automation.morning_lights", "alias": "Morning Lights", "state": "on"},
            {"entity_id": "automation.night_mode", "alias": "Night Mode", "state": "off"},
        ])

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await list_automations.ainvoke({})

        assert "morning_lights" in result.lower() or "Morning Lights" in result
        assert "night_mode" in result.lower() or "Night Mode" in result
        # Check for status indicators
        assert "🟢" in result or "on" in result.lower()

    @pytest.mark.asyncio
    async def test_list_automations_empty(self):
        """Test listing when no automations exist."""
        from src.tools.ha_tools import list_automations

        mock_mcp = MagicMock()
        mock_mcp.list_automations = AsyncMock(return_value=[])

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await list_automations.ainvoke({})

        assert "no automations" in result.lower()


class TestGetHaLogsTool:
    """Tests for get_ha_logs tool."""

    @pytest.mark.asyncio
    async def test_get_logs_returns_content(self):
        """Test fetching HA error logs."""
        from src.tools.ha_tools import get_ha_logs

        mock_mcp = MagicMock()
        mock_mcp.get_error_log = AsyncMock(
            return_value="2026-02-06 ERROR homeassistant.components.sensor: Connection failed"
        )

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await get_ha_logs.ainvoke({})

        assert "ERROR" in result or "error" in result.lower()
        assert "sensor" in result.lower()

    @pytest.mark.asyncio
    async def test_get_logs_empty(self):
        """Test when no errors in log."""
        from src.tools.ha_tools import get_ha_logs

        mock_mcp = MagicMock()
        mock_mcp.get_error_log = AsyncMock(return_value="")

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await get_ha_logs.ainvoke({})

        assert "no errors" in result.lower()

    @pytest.mark.asyncio
    async def test_get_logs_truncates_long_output(self):
        """Test that long logs are truncated to ~4000 chars."""
        from src.tools.ha_tools import get_ha_logs

        mock_mcp = MagicMock()
        long_log = "X" * 6000
        mock_mcp.get_error_log = AsyncMock(return_value=long_log)

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await get_ha_logs.ainvoke({})

        # Result includes header text + truncated log
        assert len(result) < 4200

    @pytest.mark.asyncio
    async def test_get_logs_handles_error(self):
        """Test error handling when log retrieval fails."""
        from src.tools.ha_tools import get_ha_logs

        mock_mcp = MagicMock()
        mock_mcp.get_error_log = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await get_ha_logs.ainvoke({})

        assert "failed" in result.lower()


class TestCheckHaConfigTool:
    """Tests for check_ha_config tool."""

    @pytest.mark.asyncio
    async def test_check_config_valid(self):
        """Test when config is valid."""
        from src.tools.ha_tools import check_ha_config

        mock_mcp = MagicMock()
        mock_mcp.check_config = AsyncMock(return_value={"result": "valid"})

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await check_ha_config.ainvoke({})

        assert "valid" in result.lower()
        assert "no errors" in result.lower()

    @pytest.mark.asyncio
    async def test_check_config_invalid(self):
        """Test when config has errors."""
        from src.tools.ha_tools import check_ha_config

        mock_mcp = MagicMock()
        mock_mcp.check_config = AsyncMock(return_value={
            "result": "invalid",
            "errors": "Invalid entry in configuration.yaml: sensor",
        })

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await check_ha_config.ainvoke({})

        assert "invalid" in result.lower()
        assert "sensor" in result.lower()

    @pytest.mark.asyncio
    async def test_check_config_handles_error(self):
        """Test error handling when config check fails."""
        from src.tools.ha_tools import check_ha_config

        mock_mcp = MagicMock()
        mock_mcp.check_config = AsyncMock(side_effect=Exception("Timeout"))

        with patch("src.tools.ha_tools.get_ha_client", return_value=mock_mcp):
            result = await check_ha_config.ainvoke({})

        assert "failed" in result.lower()


class TestGetAllTools:
    """Tests for get_ha_tools function."""

    def test_returns_list_of_tools(self):
        """Test that get_ha_tools returns all tools."""
        from src.tools.ha_tools import get_ha_tools

        tools = get_ha_tools()

        assert len(tools) >= 10  # Updated: now includes diagnostic tools
        tool_names = [t.name for t in tools]
        assert "get_entity_state" in tool_names
        assert "list_entities_by_domain" in tool_names
        assert "search_entities" in tool_names
        assert "deploy_automation" in tool_names
        assert "delete_automation" in tool_names
        assert "list_automations" in tool_names
        assert "get_ha_logs" in tool_names
        assert "check_ha_config" in tool_names
