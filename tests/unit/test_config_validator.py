"""Unit tests for configuration validator.

TDD: Tests written FIRST to define the API contract for
ConfigCheckResult, run_config_check, parse_config_errors,
and validate_automation_yaml.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.diagnostics.config_validator import (
    ConfigCheckResult,
    parse_config_errors,
    run_config_check,
    validate_automation_yaml,
)


class TestRunConfigCheck:
    """Tests for run_config_check."""

    @pytest.mark.asyncio
    async def test_valid_config(self):
        """Test config check returns valid result."""
        ha = MagicMock()
        ha.check_config = AsyncMock(return_value={"result": "valid"})

        result = await run_config_check(ha)

        assert isinstance(result, ConfigCheckResult)
        assert result.result == "valid"
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_invalid_config_with_errors(self):
        """Test config check with errors."""
        ha = MagicMock()
        ha.check_config = AsyncMock(return_value={
            "result": "invalid",
            "errors": "Integration error: sensor - Invalid config",
        })

        result = await run_config_check(ha)

        assert result.result == "invalid"
        assert len(result.errors) >= 1

    @pytest.mark.asyncio
    async def test_handles_mcp_error(self):
        """Test handling when MCP check_config fails."""
        ha = MagicMock()
        ha.check_config = AsyncMock(return_value={
            "result": "error",
            "error": "Connection failed",
        })

        result = await run_config_check(ha)

        assert result.result == "error"


class TestParseConfigErrors:
    """Tests for parse_config_errors."""

    def test_parses_error_string(self):
        """Test parsing an error string into structured result."""
        raw = {
            "result": "invalid",
            "errors": "Integration error: sensor - Invalid config for 'scan_interval': expected int, got str\nIntegration error: automation - line 45: invalid trigger type 'stat'",
        }

        result = parse_config_errors(raw)

        assert isinstance(result, ConfigCheckResult)
        assert result.result == "invalid"
        assert len(result.errors) >= 2

    def test_parses_valid_result(self):
        """Test parsing a valid config result."""
        raw = {"result": "valid"}

        result = parse_config_errors(raw)

        assert result.result == "valid"
        assert result.errors == []

    def test_handles_missing_errors_field(self):
        """Test handling when errors field is missing."""
        raw = {"result": "unknown"}

        result = parse_config_errors(raw)

        assert result.result == "unknown"
        assert result.errors == []


class TestValidateAutomationYaml:
    """Tests for validate_automation_yaml."""

    def test_valid_automation(self):
        """Test that valid automation YAML passes validation."""
        yaml_str = """
alias: Motion Lights
trigger:
  - platform: state
    entity_id: binary_sensor.motion
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
"""
        errors = validate_automation_yaml(yaml_str)
        assert errors == []

    def test_missing_trigger(self):
        """Test that missing trigger is caught."""
        yaml_str = """
alias: No Trigger
action:
  - service: light.turn_on
"""
        errors = validate_automation_yaml(yaml_str)
        assert any("trigger" in e.lower() for e in errors)

    def test_missing_action(self):
        """Test that missing action is caught."""
        yaml_str = """
alias: No Action
trigger:
  - platform: state
    entity_id: binary_sensor.motion
"""
        errors = validate_automation_yaml(yaml_str)
        assert any("action" in e.lower() for e in errors)

    def test_missing_alias(self):
        """Test that missing alias is caught."""
        yaml_str = """
trigger:
  - platform: state
    entity_id: binary_sensor.motion
action:
  - service: light.turn_on
"""
        errors = validate_automation_yaml(yaml_str)
        assert any("alias" in e.lower() for e in errors)

    def test_invalid_yaml(self):
        """Test that invalid YAML syntax is caught."""
        yaml_str = "this: is: not: valid: yaml: {{"
        errors = validate_automation_yaml(yaml_str)
        assert len(errors) >= 1

    def test_non_dict_yaml(self):
        """Test that non-dict YAML is rejected."""
        yaml_str = "- just a list item"
        errors = validate_automation_yaml(yaml_str)
        assert len(errors) >= 1
