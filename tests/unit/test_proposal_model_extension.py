"""Unit tests for the ProposalType and service_call model extension.

Tests backward compatibility, new fields, and YAML generation
for all proposal types.
"""

import pytest

from src.storage.entities.automation_proposal import (
    AutomationProposal,
    ProposalStatus,
    ProposalType,
)


class TestProposalType:
    """Tests for the ProposalType enum."""

    def test_automation_is_default(self):
        """ProposalType.AUTOMATION is the default value."""
        assert ProposalType.AUTOMATION.value == "automation"

    def test_all_types_defined(self):
        """All expected proposal types are defined."""
        types = {t.value for t in ProposalType}
        assert types == {"automation", "entity_command", "script", "scene", "dashboard", "helper"}

    def test_type_from_string(self):
        """ProposalType can be created from string values."""
        assert ProposalType("automation") == ProposalType.AUTOMATION
        assert ProposalType("entity_command") == ProposalType.ENTITY_COMMAND
        assert ProposalType("script") == ProposalType.SCRIPT
        assert ProposalType("scene") == ProposalType.SCENE
        assert ProposalType("dashboard") == ProposalType.DASHBOARD

    def test_invalid_type_raises(self):
        """Invalid proposal type string raises ValueError."""
        with pytest.raises(ValueError):
            ProposalType("invalid")


class TestProposalModelExtension:
    """Tests for new fields on AutomationProposal."""

    def _make_proposal(self, **kwargs) -> AutomationProposal:
        """Create a proposal with defaults for required fields."""
        defaults = {
            "id": "test-id",
            "name": "Test Proposal",
            "trigger": {},
            "actions": {},
            "mode": "single",
            "status": ProposalStatus.DRAFT,
            "proposal_type": "automation",
        }
        defaults.update(kwargs)
        return AutomationProposal(**defaults)

    def test_default_proposal_type_is_automation(self):
        """New proposals default to automation type."""
        p = self._make_proposal()
        assert p.proposal_type == "automation"

    def test_entity_command_type(self):
        """Entity command proposals store the type correctly."""
        p = self._make_proposal(
            proposal_type="entity_command",
            service_call={
                "domain": "light",
                "service": "turn_on",
                "entity_id": "light.living_room",
            },
        )
        assert p.proposal_type == "entity_command"
        assert p.service_call["domain"] == "light"
        assert p.service_call["entity_id"] == "light.living_room"

    def test_service_call_is_nullable(self):
        """service_call is None for automation proposals."""
        p = self._make_proposal()
        assert p.service_call is None

    def test_service_call_with_data(self):
        """service_call can include additional data."""
        sc = {
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.living_room",
            "data": {"brightness": 128, "color_temp": 300},
        }
        p = self._make_proposal(
            proposal_type=ProposalType.ENTITY_COMMAND.value,
            service_call=sc,
        )
        assert p.service_call["data"]["brightness"] == 128

    def test_state_transitions_work_for_all_types(self):
        """State machine transitions work for all proposal types."""
        for ptype in ProposalType:
            p = self._make_proposal(proposal_type=ptype.value)
            assert p.status == ProposalStatus.DRAFT

            p.propose()
            assert p.status == ProposalStatus.PROPOSED

            p.approve("user")
            assert p.status == ProposalStatus.APPROVED

            p.deploy("ha_id_123")
            assert p.status == ProposalStatus.DEPLOYED

            p.rollback()
            assert p.status == ProposalStatus.ROLLED_BACK


class TestProposalYamlGeneration:
    """Tests for to_ha_yaml_dict with different proposal types."""

    def _make_proposal(self, **kwargs) -> AutomationProposal:
        """Create a proposal with defaults for required fields."""
        defaults = {
            "id": "test-id",
            "name": "Test",
            "trigger": {},
            "actions": {},
            "mode": "single",
            "status": ProposalStatus.DRAFT,
            "proposal_type": ProposalType.AUTOMATION,
        }
        defaults.update(kwargs)
        return AutomationProposal(**defaults)

    def test_automation_yaml(self):
        """Automation proposals generate standard HA automation YAML."""
        p = self._make_proposal(
            name="Sunset Lights",
            trigger={"platform": "sun", "event": "sunset"},
            actions=[{"service": "light.turn_on"}],
            description="Turn on at sunset",
        )
        result = p.to_ha_yaml_dict()
        assert result["alias"] == "Sunset Lights"
        assert "trigger" in result
        assert "action" in result
        assert result["description"] == "Turn on at sunset"

    def test_entity_command_yaml(self):
        """Entity command proposals generate service call YAML."""
        p = self._make_proposal(
            proposal_type=ProposalType.ENTITY_COMMAND.value,
            service_call={
                "domain": "light",
                "service": "turn_on",
                "entity_id": "light.living_room",
                "data": {"brightness": 255},
            },
            description="Turn on living room lights at full brightness",
        )
        result = p.to_ha_yaml_dict()
        assert result["service"] == "light.turn_on"
        assert result["target"]["entity_id"] == "light.living_room"
        assert result["data"]["brightness"] == 255

    def test_entity_command_yaml_no_data(self):
        """Entity command without extra data still generates valid YAML."""
        p = self._make_proposal(
            proposal_type=ProposalType.ENTITY_COMMAND.value,
            service_call={
                "domain": "switch",
                "service": "toggle",
                "entity_id": "switch.garage",
            },
        )
        result = p.to_ha_yaml_dict()
        assert result["service"] == "switch.toggle"
        assert result["target"]["entity_id"] == "switch.garage"
        assert "data" not in result

    def test_script_yaml(self):
        """Script proposals generate HA script YAML."""
        p = self._make_proposal(
            proposal_type=ProposalType.SCRIPT.value,
            name="Movie Mode",
            actions=[
                {"service": "light.turn_on", "data": {"brightness": 50}},
                {"service": "media_player.turn_on"},
            ],
            description="Set up movie mode",
        )
        result = p.to_ha_yaml_dict()
        assert result["alias"] == "Movie Mode"
        assert "sequence" in result
        assert len(result["sequence"]) == 2
        assert result["description"] == "Set up movie mode"

    def test_scene_yaml(self):
        """Scene proposals generate HA scene YAML."""
        entities = {
            "light.living_room": {"state": "on", "brightness": 128},
            "light.bedroom": {"state": "off"},
        }
        p = self._make_proposal(
            proposal_type=ProposalType.SCENE.value,
            name="Cozy Evening",
            actions=entities,
        )
        result = p.to_ha_yaml_dict()
        assert result["name"] == "Cozy Evening"
        assert "entities" in result
        assert result["entities"]["light.living_room"]["brightness"] == 128

    def test_backward_compat_default_type(self):
        """Proposals without explicit type default to automation format."""
        p = self._make_proposal(
            name="Legacy Automation",
            trigger={"platform": "state"},
            actions=[{"service": "notify.mobile_app"}],
        )
        result = p.to_ha_yaml_dict()
        assert "alias" in result
        assert "trigger" in result
        assert "action" in result

    def test_dashboard_type(self):
        """Dashboard proposals store the type correctly."""
        p = self._make_proposal(
            proposal_type=ProposalType.DASHBOARD.value,
            name="Modern Home Dashboard",
        )
        assert p.proposal_type == "dashboard"
        assert p.proposal_type_enum == ProposalType.DASHBOARD

    def test_dashboard_config_field(self):
        """Dashboard proposals store Lovelace config in dashboard_config."""
        config = {"views": [{"title": "Home", "cards": [{"type": "weather-forecast"}]}]}
        p = self._make_proposal(
            proposal_type=ProposalType.DASHBOARD.value,
            name="Weather Dashboard",
            dashboard_config=config,
        )
        assert p.dashboard_config == config
        assert p.dashboard_config["views"][0]["title"] == "Home"

    def test_dashboard_config_default_none(self):
        """dashboard_config defaults to None for non-dashboard proposals."""
        p = self._make_proposal()
        assert p.dashboard_config is None

    def test_dashboard_yaml_dict(self):
        """Dashboard proposals return the raw Lovelace config from to_ha_yaml_dict."""
        config = {"views": [{"title": "Home"}]}
        p = self._make_proposal(
            proposal_type=ProposalType.DASHBOARD.value,
            name="Test Dashboard",
            dashboard_config=config,
            service_call={"url_path": "my-dash"},
        )
        result = p.to_ha_yaml_dict()
        assert result == config

    def test_dashboard_yaml_dict_empty_config(self):
        """Dashboard proposal with no config returns empty dict."""
        p = self._make_proposal(
            proposal_type=ProposalType.DASHBOARD.value,
            name="Empty Dashboard",
        )
        result = p.to_ha_yaml_dict()
        assert result == {}
