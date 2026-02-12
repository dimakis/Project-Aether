"""Unit tests for HA automations module.

Tests AutomationMixin methods with mocked _request.
"""

from unittest.mock import AsyncMock

import pytest

from src.ha.automations import AutomationMixin
from src.ha.base import HAClientError


class MockHAClient(AutomationMixin):
    """Mock HA client that inherits AutomationMixin for testing."""

    def __init__(self):
        self._request = AsyncMock()
        self.list_entities = AsyncMock()


@pytest.fixture
def ha_client():
    """Create a mock HA client."""
    return MockHAClient()


class TestListAutomations:
    """Tests for list_automations."""

    @pytest.mark.asyncio
    async def test_list_automations_success(self, ha_client):
        """Test successful automation listing."""
        entities = [
            {
                "entity_id": "automation.motion_lights",
                "state": "on",
                "name": "Motion Lights",
                "attributes": {
                    "id": "motion_lights",
                    "friendly_name": "Motion Lights",
                    "last_triggered": "2024-01-01T00:00:00",
                    "mode": "single",
                },
            },
            {
                "entity_id": "automation.night_mode",
                "state": "off",
                "name": "Night Mode",
                "attributes": {
                    "id": "night_mode",
                    "friendly_name": "Night Mode",
                    "mode": "restart",
                },
            },
        ]
        ha_client.list_entities.return_value = entities

        result = await ha_client.list_automations()

        assert len(result) == 2
        assert result[0]["id"] == "motion_lights"
        assert result[0]["entity_id"] == "automation.motion_lights"
        assert result[0]["state"] == "on"
        assert result[0]["alias"] == "Motion Lights"
        assert result[0]["last_triggered"] == "2024-01-01T00:00:00"
        assert result[0]["mode"] == "single"
        assert result[1]["mode"] == "restart"
        ha_client.list_entities.assert_called_once_with(domain="automation", detailed=True)

    @pytest.mark.asyncio
    async def test_list_automations_empty(self, ha_client):
        """Test empty automation list."""
        ha_client.list_entities.return_value = []

        result = await ha_client.list_automations()

        assert result == []


class TestCreateAutomation:
    """Tests for create_automation."""

    @pytest.mark.asyncio
    async def test_create_automation_success(self, ha_client):
        """Test successful automation creation."""
        ha_client._request.return_value = {}

        trigger = [{"platform": "state", "entity_id": "binary_sensor.motion"}]
        action = [{"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}]

        result = await ha_client.create_automation(
            automation_id="test_motion_lights",
            alias="Test Motion Lights",
            trigger=trigger,
            action=action,
        )

        assert result["success"] is True
        assert result["automation_id"] == "test_motion_lights"
        assert result["entity_id"] == "automation.test_motion_lights"
        assert result["method"] == "rest_api"
        assert "config" in result
        ha_client._request.assert_called_once()
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/automation/config/test_motion_lights" in call_args[0][1]
        assert call_args[1]["json"]["id"] == "test_motion_lights"
        assert call_args[1]["json"]["alias"] == "Test Motion Lights"
        assert call_args[1]["json"]["trigger"] == trigger
        assert call_args[1]["json"]["action"] == action

    @pytest.mark.asyncio
    async def test_create_automation_with_conditions(self, ha_client):
        """Test automation creation with conditions."""
        ha_client._request.return_value = {}

        trigger = [{"platform": "state", "entity_id": "binary_sensor.motion"}]
        action = [{"service": "light.turn_on"}]
        condition = [{"condition": "state", "entity_id": "light.living_room", "state": "off"}]

        result = await ha_client.create_automation(
            automation_id="test_auto",
            alias="Test",
            trigger=trigger,
            action=action,
            condition=condition,
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["condition"] == condition

    @pytest.mark.asyncio
    async def test_create_automation_with_description(self, ha_client):
        """Test automation creation with description."""
        ha_client._request.return_value = {}

        result = await ha_client.create_automation(
            automation_id="test_auto",
            alias="Test",
            trigger=[],
            action=[],
            description="Test description",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_create_automation_with_mode(self, ha_client):
        """Test automation creation with custom mode."""
        ha_client._request.return_value = {}

        result = await ha_client.create_automation(
            automation_id="test_auto",
            alias="Test",
            trigger=[],
            action=[],
            mode="restart",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["mode"] == "restart"

    @pytest.mark.asyncio
    async def test_create_automation_error(self, ha_client):
        """Test automation creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_automation")

        result = await ha_client.create_automation(
            automation_id="test_auto",
            alias="Test",
            trigger=[],
            action=[],
        )

        assert result["success"] is False
        assert result["automation_id"] == "test_auto"
        assert "error" in result
        assert result["method"] == "rest_api"


class TestGetAutomationConfig:
    """Tests for get_automation_config."""

    @pytest.mark.asyncio
    async def test_get_automation_config_success(self, ha_client):
        """Test successful automation config retrieval."""
        config = {
            "id": "test_auto",
            "alias": "Test Automation",
            "trigger": [{"platform": "state"}],
            "action": [{"service": "light.turn_on"}],
        }
        ha_client._request.return_value = config

        result = await ha_client.get_automation_config("test_auto")

        assert result == config
        ha_client._request.assert_called_once_with(
            "GET",
            "/api/config/automation/config/test_auto",
        )

    @pytest.mark.asyncio
    async def test_get_automation_config_not_found(self, ha_client):
        """Test automation config not found."""
        ha_client._request.return_value = None

        result = await ha_client.get_automation_config("nonexistent")

        assert result is None


class TestGetScriptConfig:
    """Tests for get_script_config."""

    @pytest.mark.asyncio
    async def test_get_script_config_success(self, ha_client):
        """Test successful script config retrieval."""
        config = {
            "alias": "Test Script",
            "sequence": [{"service": "light.turn_on"}],
            "mode": "single",
        }
        ha_client._request.return_value = config

        result = await ha_client.get_script_config("test_script")

        assert result == config
        ha_client._request.assert_called_once_with(
            "GET",
            "/api/config/script/config/test_script",
        )

    @pytest.mark.asyncio
    async def test_get_script_config_not_found(self, ha_client):
        """Test script config not found."""
        ha_client._request.return_value = None

        result = await ha_client.get_script_config("nonexistent")

        assert result is None


class TestDeleteAutomation:
    """Tests for delete_automation."""

    @pytest.mark.asyncio
    async def test_delete_automation_success(self, ha_client):
        """Test successful automation deletion."""
        ha_client._request.return_value = {}

        result = await ha_client.delete_automation("test_auto")

        assert result["success"] is True
        assert result["automation_id"] == "test_auto"
        ha_client._request.assert_called_once_with(
            "DELETE",
            "/api/config/automation/config/test_auto",
        )

    @pytest.mark.asyncio
    async def test_delete_automation_error(self, ha_client):
        """Test automation deletion error handling."""
        ha_client._request.side_effect = HAClientError("Not found", "delete_automation")

        result = await ha_client.delete_automation("nonexistent")

        assert result["success"] is False
        assert result["automation_id"] == "nonexistent"
        assert "error" in result


class TestListAutomationConfigs:
    """Tests for list_automation_configs."""

    @pytest.mark.asyncio
    async def test_list_automation_configs_success(self, ha_client):
        """Test successful automation configs listing."""
        configs = [
            {"id": "auto1", "alias": "Auto 1"},
            {"id": "auto2", "alias": "Auto 2"},
        ]
        ha_client._request.return_value = configs

        result = await ha_client.list_automation_configs()

        assert len(result) == 2
        assert result[0]["id"] == "auto1"
        ha_client._request.assert_called_once_with("GET", "/api/config/automation/config")

    @pytest.mark.asyncio
    async def test_list_automation_configs_empty(self, ha_client):
        """Test empty automation configs list."""
        ha_client._request.return_value = None

        result = await ha_client.list_automation_configs()

        assert result == []


class TestCreateScript:
    """Tests for create_script."""

    @pytest.mark.asyncio
    async def test_create_script_success(self, ha_client):
        """Test successful script creation."""
        ha_client._request.return_value = {}

        sequence = [{"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}]

        result = await ha_client.create_script(
            script_id="test_script",
            alias="Test Script",
            sequence=sequence,
        )

        assert result["success"] is True
        assert result["script_id"] == "test_script"
        assert result["entity_id"] == "script.test_script"
        ha_client._request.assert_called_once()
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/script/config/test_script" in call_args[0][1]
        assert call_args[1]["json"]["alias"] == "Test Script"
        assert call_args[1]["json"]["sequence"] == sequence

    @pytest.mark.asyncio
    async def test_create_script_with_description(self, ha_client):
        """Test script creation with description."""
        ha_client._request.return_value = {}

        result = await ha_client.create_script(
            script_id="test_script",
            alias="Test",
            sequence=[],
            description="Test description",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_create_script_with_icon(self, ha_client):
        """Test script creation with icon."""
        ha_client._request.return_value = {}

        result = await ha_client.create_script(
            script_id="test_script",
            alias="Test",
            sequence=[],
            icon="mdi:lightbulb",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["icon"] == "mdi:lightbulb"

    @pytest.mark.asyncio
    async def test_create_script_with_mode(self, ha_client):
        """Test script creation with custom mode."""
        ha_client._request.return_value = {}

        result = await ha_client.create_script(
            script_id="test_script",
            alias="Test",
            sequence=[],
            mode="restart",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["mode"] == "restart"

    @pytest.mark.asyncio
    async def test_create_script_error(self, ha_client):
        """Test script creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_script")

        result = await ha_client.create_script(
            script_id="test_script",
            alias="Test",
            sequence=[],
        )

        assert result["success"] is False
        assert result["script_id"] == "test_script"
        assert "error" in result


class TestDeleteScript:
    """Tests for delete_script."""

    @pytest.mark.asyncio
    async def test_delete_script_success(self, ha_client):
        """Test successful script deletion."""
        ha_client._request.return_value = {}

        result = await ha_client.delete_script("test_script")

        assert result["success"] is True
        assert result["script_id"] == "test_script"
        ha_client._request.assert_called_once_with(
            "DELETE",
            "/api/config/script/config/test_script",
        )

    @pytest.mark.asyncio
    async def test_delete_script_error(self, ha_client):
        """Test script deletion error handling."""
        ha_client._request.side_effect = HAClientError("Not found", "delete_script")

        result = await ha_client.delete_script("nonexistent")

        assert result["success"] is False
        assert result["script_id"] == "nonexistent"
        assert "error" in result


class TestCreateScene:
    """Tests for create_scene."""

    @pytest.mark.asyncio
    async def test_create_scene_success(self, ha_client):
        """Test successful scene creation."""
        ha_client._request.return_value = {}

        entities = {
            "light.living_room": {"state": "on", "brightness": 255},
            "light.bedroom": {"state": "off"},
        }

        result = await ha_client.create_scene(
            scene_id="test_scene",
            name="Test Scene",
            entities=entities,
        )

        assert result["success"] is True
        assert result["scene_id"] == "test_scene"
        assert result["entity_id"] == "scene.test_scene"
        ha_client._request.assert_called_once()
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/scene/config/test_scene" in call_args[0][1]
        assert call_args[1]["json"]["id"] == "test_scene"
        assert call_args[1]["json"]["name"] == "Test Scene"
        assert call_args[1]["json"]["entities"] == entities

    @pytest.mark.asyncio
    async def test_create_scene_with_icon(self, ha_client):
        """Test scene creation with icon."""
        ha_client._request.return_value = {}

        result = await ha_client.create_scene(
            scene_id="test_scene",
            name="Test",
            entities={},
            icon="mdi:palette",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["icon"] == "mdi:palette"

    @pytest.mark.asyncio
    async def test_create_scene_error(self, ha_client):
        """Test scene creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_scene")

        result = await ha_client.create_scene(
            scene_id="test_scene",
            name="Test",
            entities={},
        )

        assert result["success"] is False
        assert result["scene_id"] == "test_scene"
        assert "error" in result


class TestDeleteScene:
    """Tests for delete_scene."""

    @pytest.mark.asyncio
    async def test_delete_scene_success(self, ha_client):
        """Test successful scene deletion."""
        ha_client._request.return_value = {}

        result = await ha_client.delete_scene("test_scene")

        assert result["success"] is True
        assert result["scene_id"] == "test_scene"
        ha_client._request.assert_called_once_with(
            "DELETE",
            "/api/config/scene/config/test_scene",
        )

    @pytest.mark.asyncio
    async def test_delete_scene_error(self, ha_client):
        """Test scene deletion error handling."""
        ha_client._request.side_effect = HAClientError("Not found", "delete_scene")

        result = await ha_client.delete_scene("nonexistent")

        assert result["success"] is False
        assert result["scene_id"] == "nonexistent"
        assert "error" in result
