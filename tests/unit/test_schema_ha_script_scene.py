"""Unit tests for HA script and scene schemas.

T206: Tests for HAScript and HAScene.
Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

# =============================================================================
# SCRIPT TESTS
# =============================================================================


class TestHAScript:
    """Test HA script schema."""

    def test_minimal_script(self) -> None:
        from src.schema.ha.script import HAScript

        s = HAScript(
            alias="Morning Routine",
            sequence=[{"service": "light.turn_on", "target": {"entity_id": "light.bedroom"}}],
        )
        assert s.alias == "Morning Routine"
        assert s.mode.value == "single"

    def test_script_with_fields(self) -> None:
        from src.schema.ha.script import HAScript

        s = HAScript(
            alias="Set Brightness",
            sequence=[{"service": "light.turn_on", "data": {"brightness": "{{ level }}"}}],
            fields={
                "level": {
                    "description": "Brightness level",
                    "example": 128,
                    "selector": {"number": {"min": 0, "max": 255}},
                },
            },
        )
        assert "level" in s.fields

    def test_script_all_modes(self) -> None:
        from src.schema.ha.script import HAScript

        for mode in ["single", "restart", "queued", "parallel"]:
            s = HAScript(
                alias="Test",
                sequence=[{"service": "light.turn_on"}],
                mode=mode,
            )
            assert s.mode.value == mode

    def test_script_missing_sequence(self) -> None:
        from src.schema.ha.script import HAScript

        with pytest.raises(ValidationError, match="sequence"):
            HAScript(alias="Test")

    def test_script_missing_alias(self) -> None:
        from src.schema.ha.script import HAScript

        with pytest.raises(ValidationError, match="alias"):
            HAScript(sequence=[{"service": "light.turn_on"}])

    def test_script_yaml_roundtrip(self) -> None:
        from src.schema.core import SchemaRegistry
        from src.schema.ha.script import HAScript

        registry = SchemaRegistry()
        registry.register("ha.script", HAScript)

        yaml_str = """\
alias: Good Night
description: Turn off all lights and lock doors
sequence:
  - service: light.turn_off
    target:
      entity_id: all
  - service: lock.lock
    target:
      entity_id: all
  - delay: "00:00:05"
mode: single
"""
        data = yaml.safe_load(yaml_str)
        result = registry.validate("ha.script", data)
        assert result.valid is True, f"Errors: {result.errors}"


# =============================================================================
# SCENE TESTS
# =============================================================================


class TestHAScene:
    """Test HA scene schema."""

    def test_minimal_scene(self) -> None:
        from src.schema.ha.scene import HAScene

        s = HAScene(
            name="Movie Night",
            entities={
                "light.living_room": {"state": "on", "brightness": 50},
                "media_player.tv": "on",
            },
        )
        assert s.name == "Movie Night"
        assert len(s.entities) == 2

    def test_scene_with_id(self) -> None:
        from src.schema.ha.scene import HAScene

        s = HAScene(
            id="movie_night",
            name="Movie Night",
            entities={"light.living_room": "on"},
        )
        assert s.id == "movie_night"

    def test_scene_with_icon(self) -> None:
        from src.schema.ha.scene import HAScene

        s = HAScene(
            name="Party",
            icon="mdi:party-popper",
            entities={"light.living_room": {"state": "on", "rgb_color": [255, 0, 0]}},
        )
        assert s.icon == "mdi:party-popper"

    def test_scene_missing_name(self) -> None:
        from src.schema.ha.scene import HAScene

        with pytest.raises(ValidationError, match="name"):
            HAScene(entities={"light.living_room": "on"})

    def test_scene_missing_entities(self) -> None:
        from src.schema.ha.scene import HAScene

        with pytest.raises(ValidationError, match="entities"):
            HAScene(name="Test")

    def test_scene_yaml_roundtrip(self) -> None:
        from src.schema.core import SchemaRegistry
        from src.schema.ha.scene import HAScene

        registry = SchemaRegistry()
        registry.register("ha.scene", HAScene)

        yaml_str = """\
name: Bedtime
icon: mdi:bed
entities:
  light.bedroom:
    state: "on"
    brightness: 30
  light.living_room: "off"
  switch.tv: "off"
"""
        data = yaml.safe_load(yaml_str)
        result = registry.validate("ha.scene", data)
        assert result.valid is True, f"Errors: {result.errors}"
