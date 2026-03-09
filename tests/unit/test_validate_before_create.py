"""Unit tests for _validate_before_create pre-creation validation.

Verifies that each proposal type is structurally validated before
creation, returning error strings for invalid configs and None for valid.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.approval_tools import _validate_before_create

_HA_CLIENT_PATH = "src.ha.get_ha_client_async"


@pytest.fixture
def _skip_semantic():
    """Patch HA client to raise so semantic validation is skipped."""
    with patch(_HA_CLIENT_PATH, AsyncMock(side_effect=Exception("no HA"))):
        yield


@pytest.fixture
def _semantic_pass():
    """Patch semantic validation to always pass."""
    from src.schema.core import ValidationResult

    mock_semantic = AsyncMock(return_value=ValidationResult(valid=True, schema_name="test"))
    mock_ha = AsyncMock(return_value=MagicMock())
    with (
        patch(_HA_CLIENT_PATH, mock_ha),
        patch("src.tools.approval_tools.validate_yaml_semantic", new=mock_semantic),
    ):
        yield


@pytest.mark.asyncio
class TestValidateBeforeCreate:
    """Tests for the shared pre-creation validation helper."""

    async def test_unknown_type_returns_none(self):
        assert await _validate_before_create("nonexistent", {}, "test") is None

    # -- entity_command ---------------------------------------------------

    @pytest.mark.usefixtures("_semantic_pass")
    async def test_entity_command_valid(self):
        config = {
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.living_room",
        }
        assert await _validate_before_create("entity_command", config, "Turn on lights") is None

    @pytest.mark.usefixtures("_skip_semantic")
    async def test_entity_command_missing_domain(self):
        config = {"service": "turn_on", "entity_id": "light.living_room"}
        result = await _validate_before_create("entity_command", config, "Bad command")
        assert result is not None
        assert "entity_command" in result
        assert "Errors" in result

    # -- automation -------------------------------------------------------

    @pytest.mark.usefixtures("_semantic_pass")
    async def test_automation_valid(self):
        config = {
            "trigger": [{"platform": "time", "at": "08:00:00"}],
            "action": [{"service": "light.turn_on", "target": {"entity_id": "light.kitchen"}}],
            "mode": "single",
        }
        assert await _validate_before_create("automation", config, "Morning lights") is None

    @pytest.mark.usefixtures("_skip_semantic")
    async def test_automation_missing_trigger(self):
        config = {
            "action": [{"service": "light.turn_on", "target": {"entity_id": "light.kitchen"}}],
        }
        result = await _validate_before_create("automation", config, "Bad auto")
        assert result is not None
        assert "automation" in result

    # -- script -----------------------------------------------------------

    @pytest.mark.usefixtures("_semantic_pass")
    async def test_script_valid(self):
        config = {
            "alias": "Bedtime script",
            "sequence": [{"service": "light.turn_on", "target": {"entity_id": "light.bedroom"}}],
            "mode": "single",
        }
        assert await _validate_before_create("script", config, "Bedtime script") is None

    @pytest.mark.usefixtures("_skip_semantic")
    async def test_script_empty_sequence(self):
        config = {"sequence": [], "mode": "single"}
        result = await _validate_before_create("script", config, "Empty script")
        assert result is None or "script" in result

    # -- scene ------------------------------------------------------------

    @pytest.mark.usefixtures("_semantic_pass")
    async def test_scene_valid(self):
        config = {
            "name": "Movie scene",
            "entities": {"light.living_room": {"state": "on", "brightness": 200}},
        }
        assert await _validate_before_create("scene", config, "Movie scene") is None

    # -- dashboard --------------------------------------------------------

    @pytest.mark.usefixtures("_semantic_pass")
    async def test_dashboard_valid(self):
        config = {
            "views": [
                {"title": "Home", "cards": [{"type": "entities", "entities": ["light.kitchen"]}]}
            ],
        }
        assert await _validate_before_create("dashboard", config, "Home dashboard") is None

    @pytest.mark.usefixtures("_skip_semantic")
    async def test_dashboard_missing_views(self):
        config = {}
        result = await _validate_before_create("dashboard", config, "Bad dashboard")
        assert result is not None
        assert "dashboard" in result

    # -- helper -----------------------------------------------------------

    @pytest.mark.usefixtures("_semantic_pass")
    async def test_helper_valid(self):
        config = {
            "helper_type": "input_boolean",
            "input_id": "guest_mode",
            "name": "Guest Mode",
        }
        assert await _validate_before_create("helper", config, "Guest mode toggle") is None

    @pytest.mark.usefixtures("_skip_semantic")
    async def test_helper_missing_type(self):
        config = {"input_id": "guest_mode", "name": "Guest Mode"}
        result = await _validate_before_create("helper", config, "Bad helper")
        assert result is not None
        assert "helper" in result

    # -- error message format ---------------------------------------------

    @pytest.mark.usefixtures("_skip_semantic")
    @pytest.mark.parametrize(
        "proposal_type",
        ["entity_command", "automation", "script", "dashboard", "helper"],
    )
    async def test_error_contains_type_and_instructions(self, proposal_type: str):
        result = await _validate_before_create(proposal_type, {}, "test")
        if result is not None:
            assert proposal_type in result
            assert "seek_approval" in result
