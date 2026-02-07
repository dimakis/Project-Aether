"""Unit tests for MCP client automation methods.

Tests the new REST API-based automation CRUD operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCreateAutomation:
    """Tests for MCPClient.create_automation."""

    @pytest.mark.asyncio
    async def test_create_automation_success(self):
        """Test successful automation creation."""
        from src.mcp.client import MCPClient, MCPClientConfig

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        # Mock the _request method
        client._request = AsyncMock(return_value={})

        result = await client.create_automation(
            automation_id="test_motion_lights",
            alias="Motion Lights",
            trigger=[{"platform": "state", "entity_id": "binary_sensor.motion"}],
            action=[{"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}],
            description="Turn on lights when motion detected",
            mode="single",
        )

        assert result["success"] is True
        assert result["automation_id"] == "test_motion_lights"
        assert result["entity_id"] == "automation.test_motion_lights"
        assert result["method"] == "rest_api"

        # Verify the request was made correctly
        client._request.assert_called_once()
        call_args = client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/automation/config/test_motion_lights" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_automation_with_conditions(self):
        """Test automation creation with conditions."""
        from src.mcp.client import MCPClient, MCPClientConfig

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        client._request = AsyncMock(return_value={})

        result = await client.create_automation(
            automation_id="night_motion_lights",
            alias="Night Motion Lights",
            trigger=[{"platform": "state", "entity_id": "binary_sensor.motion"}],
            action=[{"service": "light.turn_on", "target": {"entity_id": "light.hallway"}}],
            condition=[{"condition": "sun", "after": "sunset", "before": "sunrise"}],
            mode="restart",
        )

        assert result["success"] is True
        
        # Verify conditions were included
        call_json = client._request.call_args[1]["json"]
        assert "condition" in call_json
        assert call_json["mode"] == "restart"

    @pytest.mark.asyncio
    async def test_create_automation_failure(self):
        """Test automation creation failure handling."""
        from src.mcp.client import MCPClient, MCPClientConfig, MCPError

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        client._request = AsyncMock(side_effect=MCPError("Connection failed", "create_automation"))

        result = await client.create_automation(
            automation_id="test_automation",
            alias="Test",
            trigger=[{"platform": "time", "at": "06:00:00"}],
            action=[{"service": "light.turn_on", "target": {"entity_id": "light.bedroom"}}],
        )

        assert result["success"] is False
        assert "error" in result
        assert result["method"] == "rest_api"


class TestDeleteAutomation:
    """Tests for MCPClient.delete_automation."""

    @pytest.mark.asyncio
    async def test_delete_automation_success(self):
        """Test successful automation deletion."""
        from src.mcp.client import MCPClient, MCPClientConfig

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        client._request = AsyncMock(return_value={})

        result = await client.delete_automation("test_automation")

        assert result["success"] is True
        assert result["automation_id"] == "test_automation"
        
        client._request.assert_called_once()
        call_args = client._request.call_args
        assert call_args[0][0] == "DELETE"

    @pytest.mark.asyncio
    async def test_delete_automation_not_found(self):
        """Test deleting non-existent automation."""
        from src.mcp.client import MCPClient, MCPClientConfig, MCPError

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        client._request = AsyncMock(side_effect=MCPError("Not found", "delete_automation"))

        result = await client.delete_automation("nonexistent")

        assert result["success"] is False


class TestGetAutomationConfig:
    """Tests for MCPClient.get_automation_config."""

    @pytest.mark.asyncio
    async def test_get_automation_config_found(self):
        """Test getting existing automation config."""
        from src.mcp.client import MCPClient, MCPClientConfig

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        expected_config = {
            "id": "motion_lights",
            "alias": "Motion Lights",
            "trigger": [{"platform": "state", "entity_id": "binary_sensor.motion"}],
            "action": [{"service": "light.turn_on"}],
        }
        client._request = AsyncMock(return_value=expected_config)

        result = await client.get_automation_config("motion_lights")

        assert result == expected_config
        assert result["alias"] == "Motion Lights"

    @pytest.mark.asyncio
    async def test_get_automation_config_not_found(self):
        """Test getting non-existent automation config."""
        from src.mcp.client import MCPClient, MCPClientConfig

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        client._request = AsyncMock(return_value=None)

        result = await client.get_automation_config("nonexistent")

        assert result is None


class TestListAutomationConfigs:
    """Tests for MCPClient.list_automation_configs."""

    @pytest.mark.asyncio
    async def test_list_automation_configs(self):
        """Test listing all automation configs."""
        from src.mcp.client import MCPClient, MCPClientConfig

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        expected = [
            {"id": "auto_1", "alias": "Automation 1"},
            {"id": "auto_2", "alias": "Automation 2"},
        ]
        client._request = AsyncMock(return_value=expected)

        result = await client.list_automation_configs()

        assert len(result) == 2
        assert result[0]["id"] == "auto_1"

    @pytest.mark.asyncio
    async def test_list_automation_configs_empty(self):
        """Test listing when no automations exist."""
        from src.mcp.client import MCPClient, MCPClientConfig

        client = MCPClient(MCPClientConfig(
            ha_url="http://localhost:8123",
            ha_token="test-token",
        ))

        client._request = AsyncMock(return_value=None)

        result = await client.list_automation_configs()

        assert result == []
