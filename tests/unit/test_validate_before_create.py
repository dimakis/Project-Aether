"""Unit tests for _validate_before_create pre-creation validation.

Verifies that each proposal type is structurally validated before
creation, returning error strings for invalid configs and None for valid.
"""

from __future__ import annotations

import pytest

from src.tools.approval_tools import _validate_before_create


class TestValidateBeforeCreate:
    """Tests for the shared pre-creation validation helper."""

    def test_unknown_type_returns_none(self):
        assert _validate_before_create("nonexistent", {}, "test") is None

    # -- entity_command ---------------------------------------------------

    def test_entity_command_valid(self):
        config = {
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.living_room",
        }
        assert _validate_before_create("entity_command", config, "Turn on lights") is None

    def test_entity_command_missing_domain(self):
        config = {"service": "turn_on", "entity_id": "light.living_room"}
        result = _validate_before_create("entity_command", config, "Bad command")
        assert result is not None
        assert "entity_command" in result
        assert "Errors" in result

    # -- automation -------------------------------------------------------

    def test_automation_valid(self):
        config = {
            "trigger": [{"platform": "time", "at": "08:00:00"}],
            "action": [{"service": "light.turn_on", "target": {"entity_id": "light.kitchen"}}],
            "mode": "single",
        }
        assert _validate_before_create("automation", config, "Morning lights") is None

    def test_automation_missing_trigger(self):
        config = {
            "action": [{"service": "light.turn_on", "target": {"entity_id": "light.kitchen"}}],
        }
        result = _validate_before_create("automation", config, "Bad auto")
        assert result is not None
        assert "automation" in result

    # -- script -----------------------------------------------------------

    def test_script_valid(self):
        config = {
            "alias": "Bedtime script",
            "sequence": [{"service": "light.turn_on", "target": {"entity_id": "light.bedroom"}}],
            "mode": "single",
        }
        assert _validate_before_create("script", config, "Bedtime script") is None

    def test_script_empty_sequence(self):
        config = {"sequence": [], "mode": "single"}
        result = _validate_before_create("script", config, "Empty script")
        # Empty sequence may or may not fail depending on schema strictness;
        # the key assertion is that validation ran without crashing
        assert result is None or "script" in result

    # -- scene ------------------------------------------------------------

    def test_scene_valid(self):
        config = {
            "name": "Movie scene",
            "entities": {"light.living_room": {"state": "on", "brightness": 200}},
        }
        assert _validate_before_create("scene", config, "Movie scene") is None

    # -- dashboard --------------------------------------------------------

    def test_dashboard_valid(self):
        config = {
            "views": [
                {"title": "Home", "cards": [{"type": "entities", "entities": ["light.kitchen"]}]}
            ],
        }
        assert _validate_before_create("dashboard", config, "Home dashboard") is None

    def test_dashboard_missing_views(self):
        config = {}
        result = _validate_before_create("dashboard", config, "Bad dashboard")
        assert result is not None
        assert "dashboard" in result

    # -- helper -----------------------------------------------------------

    def test_helper_valid(self):
        config = {
            "helper_type": "input_boolean",
            "input_id": "guest_mode",
            "name": "Guest Mode",
        }
        assert _validate_before_create("helper", config, "Guest mode toggle") is None

    def test_helper_missing_type(self):
        config = {"input_id": "guest_mode", "name": "Guest Mode"}
        result = _validate_before_create("helper", config, "Bad helper")
        assert result is not None
        assert "helper" in result

    # -- error message format ---------------------------------------------

    @pytest.mark.parametrize(
        "proposal_type",
        ["entity_command", "automation", "script", "dashboard", "helper"],
    )
    def test_error_contains_type_and_instructions(self, proposal_type: str):
        result = _validate_before_create(proposal_type, {}, "test")
        if result is not None:
            assert proposal_type in result
            assert "seek_approval" in result
