"""Unit tests for DeveloperAgent deployment via AutomationDeployer.

Tests that _deploy_via_ha correctly delegates to AutomationDeployer
for real HA REST API deployment instead of returning manual instructions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.developer import DeveloperAgent


@pytest.mark.asyncio
class TestDeveloperDeployViaMCP:
    """Tests for DeveloperAgent._deploy_via_ha using AutomationDeployer."""

    async def test_deploy_calls_automation_deployer(self):
        """_deploy_via_ha should delegate to AutomationDeployer.deploy_automation."""
        mock_mcp = MagicMock()
        agent = DeveloperAgent(ha_client=mock_mcp)

        expected_result = {
            "success": True,
            "method": "rest_api",
            "automation_id": "aether_test",
            "entity_id": "automation.aether_test",
            "note": "Automation created via HA REST API. Active immediately.",
        }

        with patch("src.agents.developer.AutomationDeployer") as MockDeployer:
            mock_deployer_instance = MagicMock()
            mock_deployer_instance.deploy_automation = AsyncMock(return_value=expected_result)
            MockDeployer.return_value = mock_deployer_instance

            result = await agent._deploy_via_ha(
                "aether_test", "alias: Test\ntrigger: []\naction: []"
            )

            MockDeployer.assert_called_once_with(mock_mcp)
            mock_deployer_instance.deploy_automation.assert_called_once_with(
                "alias: Test\ntrigger: []\naction: []",
                "aether_test",
            )
            assert result["success"] is True
            assert result["method"] == "rest_api"

    async def test_deploy_returns_manual_on_failure(self):
        """When AutomationDeployer fails REST API, it falls back to manual."""
        mock_mcp = MagicMock()
        agent = DeveloperAgent(ha_client=mock_mcp)

        fallback_result = {
            "success": False,
            "method": "manual",
            "error": "Connection refused",
            "instructions": "To deploy this automation manually:\n...",
        }

        with patch("src.agents.developer.AutomationDeployer") as MockDeployer:
            mock_deployer_instance = MagicMock()
            mock_deployer_instance.deploy_automation = AsyncMock(return_value=fallback_result)
            MockDeployer.return_value = mock_deployer_instance

            result = await agent._deploy_via_ha(
                "aether_test", "alias: Test\ntrigger: []\naction: []"
            )

            assert result["success"] is False
            assert result["method"] == "manual"
            assert "instructions" in result

    async def test_deploy_passes_correct_arguments(self):
        """Verify correct yaml_content and automation_id are passed."""
        mock_mcp = MagicMock()
        agent = DeveloperAgent(ha_client=mock_mcp)

        yaml_content = """alias: Sunset lights
trigger:
  - platform: sun
    event: sunset
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
"""

        with patch("src.agents.developer.AutomationDeployer") as MockDeployer:
            mock_deployer_instance = MagicMock()
            mock_deployer_instance.deploy_automation = AsyncMock(
                return_value={"success": True, "method": "rest_api"}
            )
            MockDeployer.return_value = mock_deployer_instance

            await agent._deploy_via_ha("aether_sunset_12345678", yaml_content)

            call_args = mock_deployer_instance.deploy_automation.call_args
            assert call_args[0][0] == yaml_content
            assert call_args[0][1] == "aether_sunset_12345678"

    async def test_deploy_no_longer_returns_manual_stub(self):
        """Ensure the old stub behavior (always manual) is gone."""
        mock_mcp = MagicMock()
        agent = DeveloperAgent(ha_client=mock_mcp)

        with patch("src.agents.developer.AutomationDeployer") as MockDeployer:
            mock_deployer_instance = MagicMock()
            mock_deployer_instance.deploy_automation = AsyncMock(
                return_value={"success": True, "method": "rest_api"}
            )
            MockDeployer.return_value = mock_deployer_instance

            result = await agent._deploy_via_ha("test_id", "alias: Test\ntrigger: []\naction: []")

            # Should NOT be the old hardcoded manual response
            assert result.get("method") != "manual" or result.get("success") is not None
            # AutomationDeployer was actually called
            mock_deployer_instance.deploy_automation.assert_called_once()
