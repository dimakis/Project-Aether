"""Unit tests for automation YAML generation and validation.

T095: Tests for YAML generation validation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml


class TestAutomationDeployer:
    """Test AutomationDeployer YAML generation."""

    @pytest.fixture
    def deployer(self):
        """Create deployer instance."""
        from src.ha.automation_deploy import AutomationDeployer

        return AutomationDeployer()

    def test_generate_simple_automation(self, deployer):
        """Test generating a simple automation YAML."""
        yaml_content = deployer.generate_automation_yaml(
            name="Morning Lights",
            trigger={"platform": "time", "at": "07:00:00"},
            actions={"service": "light.turn_on", "target": {"entity_id": "light.bedroom"}},
        )

        # Parse and verify
        data = yaml.safe_load(yaml_content)
        assert data["alias"] == "Morning Lights"
        assert data["trigger"][0]["platform"] == "time"
        assert data["action"][0]["service"] == "light.turn_on"
        assert data["mode"] == "single"

    def test_generate_automation_with_conditions(self, deployer):
        """Test generating automation with conditions."""
        yaml_content = deployer.generate_automation_yaml(
            name="Motion Lights",
            trigger={"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"},
            actions={"service": "light.turn_on", "target": {"entity_id": "light.living_room"}},
            conditions={"condition": "time", "after": "18:00:00", "before": "23:00:00"},
        )

        data = yaml.safe_load(yaml_content)
        assert "condition" in data
        assert data["condition"][0]["condition"] == "time"

    def test_generate_automation_with_description(self, deployer):
        """Test generating automation with description."""
        yaml_content = deployer.generate_automation_yaml(
            name="Test Automation",
            description="This is a test automation for lights",
            trigger={"platform": "time", "at": "08:00:00"},
            actions={"service": "light.turn_on"},
        )

        data = yaml.safe_load(yaml_content)
        assert data["description"] == "This is a test automation for lights"

    def test_generate_automation_with_metadata(self, deployer):
        """Test generating automation with metadata comments."""
        yaml_content = deployer.generate_automation_yaml(
            name="Test",
            trigger={"platform": "time", "at": "08:00"},
            actions={"service": "light.turn_on"},
            metadata={"proposal_id": "abc123", "created_by": "architect"},
        )

        assert "# Project Aether Automation" in yaml_content
        assert "proposal_id: abc123" in yaml_content
        assert "created_by: architect" in yaml_content

    def test_generate_automation_id(self, deployer):
        """Test automation ID generation."""
        # With proposal ID
        auto_id = deployer.generate_automation_id("Test Automation", "abc-def-123")
        assert auto_id.startswith("aether_")
        assert "test_automation" in auto_id

        # Without proposal ID (uses timestamp)
        auto_id_no_prop = deployer.generate_automation_id("Test Automation")
        assert auto_id_no_prop.startswith("aether_test_automation_")

    def test_generate_automation_id_sanitizes_name(self, deployer):
        """Test that automation ID sanitizes special characters."""
        auto_id = deployer.generate_automation_id("Turn on Living Room Lights!", "123")
        assert " " not in auto_id
        assert "!" not in auto_id
        assert auto_id.islower() or auto_id.replace("_", "").isalnum()


class TestYAMLValidation:
    """Test YAML validation."""

    @pytest.fixture
    def deployer(self):
        """Create deployer instance."""
        from src.ha.automation_deploy import AutomationDeployer

        return AutomationDeployer()

    def test_validate_valid_automation(self, deployer):
        """Test validating a correct automation YAML."""
        yaml_content = """
alias: Test Automation
trigger:
  - platform: time
    at: "08:00:00"
action:
  - service: light.turn_on
mode: single
"""
        is_valid, errors = deployer.validate_automation_yaml(yaml_content)
        assert is_valid
        assert len(errors) == 0

    def test_validate_missing_trigger(self, deployer):
        """Test validation catches missing trigger."""
        yaml_content = """
alias: Test Automation
action:
  - service: light.turn_on
"""
        is_valid, errors = deployer.validate_automation_yaml(yaml_content)
        assert not is_valid
        assert any("trigger" in e.lower() for e in errors)

    def test_validate_missing_action(self, deployer):
        """Test validation catches missing action."""
        yaml_content = """
alias: Test Automation
trigger:
  - platform: time
    at: "08:00:00"
"""
        is_valid, errors = deployer.validate_automation_yaml(yaml_content)
        assert not is_valid
        assert any("action" in e.lower() for e in errors)

    def test_validate_invalid_mode(self, deployer):
        """Test validation catches invalid mode."""
        yaml_content = """
alias: Test
trigger:
  - platform: time
    at: "08:00"
action:
  - service: light.turn_on
mode: invalid_mode
"""
        is_valid, errors = deployer.validate_automation_yaml(yaml_content)
        assert not is_valid
        assert any("mode" in e.lower() for e in errors)

    def test_validate_invalid_yaml(self, deployer):
        """Test validation catches invalid YAML syntax."""
        yaml_content = "{ invalid yaml: ["
        is_valid, errors = deployer.validate_automation_yaml(yaml_content)
        assert not is_valid
        assert any("invalid yaml" in e.lower() for e in errors)


class TestYAMLHelpers:
    """Test YAML helper functions."""

    def test_build_state_trigger(self):
        """Test state trigger builder."""
        from src.ha.automation_deploy import build_state_trigger

        trigger = build_state_trigger(
            entity_id="light.living_room",
            to_state="on",
            from_state="off",
            for_duration="00:00:30",
        )

        assert trigger["platform"] == "state"
        assert trigger["entity_id"] == "light.living_room"
        assert trigger["to"] == "on"
        assert trigger["from"] == "off"
        assert trigger["for"] == "00:00:30"

    def test_build_time_trigger(self):
        """Test time trigger builder."""
        from src.ha.automation_deploy import build_time_trigger

        trigger = build_time_trigger("08:00:00")

        assert trigger["platform"] == "time"
        assert trigger["at"] == "08:00:00"

    def test_build_sun_trigger(self):
        """Test sun trigger builder."""
        from src.ha.automation_deploy import build_sun_trigger

        trigger = build_sun_trigger(event="sunset", offset="-00:30:00")

        assert trigger["platform"] == "sun"
        assert trigger["event"] == "sunset"
        assert trigger["offset"] == "-00:30:00"

    def test_build_service_action(self):
        """Test service action builder."""
        from src.ha.automation_deploy import build_service_action

        action = build_service_action(
            domain="light",
            service="turn_on",
            target={"entity_id": "light.bedroom"},
            data={"brightness": 255},
        )

        assert action["service"] == "light.turn_on"
        assert action["target"]["entity_id"] == "light.bedroom"
        assert action["data"]["brightness"] == 255

    def test_build_delay_action(self):
        """Test delay action builder."""
        from src.ha.automation_deploy import build_delay_action

        action = build_delay_action("00:00:30")
        assert action["delay"] == "00:00:30"

    def test_build_condition(self):
        """Test condition builder."""
        from src.ha.automation_deploy import build_condition

        condition = build_condition(
            "time",
            after="18:00:00",
            before="23:00:00",
        )

        assert condition["condition"] == "time"
        assert condition["after"] == "18:00:00"
        assert condition["before"] == "23:00:00"


class TestAutomationDeployerRestAPI:
    """Test AutomationDeployer REST API deployment."""

    @pytest.fixture
    def deployer_with_mock_mcp(self):
        """Create deployer with mocked HA client."""
        from src.ha.automation_deploy import AutomationDeployer

        deployer = AutomationDeployer()
        deployer._ha_client = MagicMock()
        return deployer

    @pytest.mark.asyncio
    async def test_deploy_via_rest_api_success(self, deployer_with_mock_mcp):
        """Test successful deployment via REST API."""
        deployer = deployer_with_mock_mcp
        deployer._ha_client.create_automation = AsyncMock(return_value={
            "success": True,
            "automation_id": "test_automation",
            "entity_id": "automation.test_automation",
        })

        yaml_content = """
alias: Test Automation
trigger:
  - platform: time
    at: "08:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.bedroom
mode: single
"""
        result = await deployer.deploy_automation(yaml_content, "test_automation")

        assert result["success"] is True
        assert result["method"] == "rest_api"
        assert result["entity_id"] == "automation.test_automation"
        deployer._ha_client.create_automation.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_falls_back_to_manual_on_failure(self, deployer_with_mock_mcp):
        """Test fallback to manual instructions when REST API fails."""
        deployer = deployer_with_mock_mcp
        deployer._ha_client.create_automation = AsyncMock(return_value={
            "success": False,
            "error": "Connection refused",
        })

        yaml_content = """
alias: Test
trigger:
  - platform: time
    at: "08:00"
action:
  - service: light.turn_on
"""
        result = await deployer.deploy_automation(yaml_content, "test_auto")

        assert result["success"] is False
        assert result["method"] == "manual"
        assert "instructions" in result

    @pytest.mark.asyncio
    async def test_deploy_validates_yaml_first(self, deployer_with_mock_mcp):
        """Test that YAML is validated before deployment attempt."""
        deployer = deployer_with_mock_mcp

        invalid_yaml = """
alias: Test
# Missing trigger and action!
"""
        result = await deployer.deploy_automation(invalid_yaml, "test_auto")

        assert result["success"] is False
        assert result["method"] == "validation_failed"
        # Should not have called MCP at all
        deployer._ha_client.create_automation.assert_not_called()

    @pytest.mark.asyncio
    async def test_deploy_saves_yaml_backup(self, deployer_with_mock_mcp, tmp_path):
        """Test that YAML is saved as backup when output_dir provided."""
        deployer = deployer_with_mock_mcp
        deployer._ha_client.create_automation = AsyncMock(return_value={
            "success": True,
            "automation_id": "backup_test",
            "entity_id": "automation.backup_test",
        })

        yaml_content = """
alias: Backup Test
trigger:
  - platform: time
    at: "08:00"
action:
  - service: light.turn_on
"""
        result = await deployer.deploy_automation(
            yaml_content, 
            "backup_test",
            output_dir=tmp_path,
        )

        assert result["success"] is True
        assert "yaml_file" in result
        
        # Verify file was created
        yaml_file = tmp_path / "backup_test.yaml"
        assert yaml_file.exists()
