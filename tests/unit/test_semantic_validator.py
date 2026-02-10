"""Unit tests for SemanticValidator and semantic rules.

T221, T222: SemanticValidator core + entity_exists, service_valid,
domain_consistent, area_exists rules.
Feature 27: YAML Semantic Validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml


@pytest.fixture
def mock_ha_client() -> MagicMock:
    """Mock HA client for registry cache."""
    client = MagicMock()

    client.list_entities = AsyncMock(
        return_value=[
            {"entity_id": "light.living_room"},
            {"entity_id": "light.bedroom"},
            {"entity_id": "switch.fan"},
            {"entity_id": "sensor.temperature"},
            {"entity_id": "binary_sensor.motion"},
            {"entity_id": "person.john"},
            {"entity_id": "input_boolean.vacation"},
        ]
    )

    client.list_services = AsyncMock(
        return_value=[
            {
                "domain": "light",
                "services": {
                    "turn_on": {"fields": {"brightness": {}, "color_temp": {}}},
                    "turn_off": {"fields": {}},
                },
            },
            {
                "domain": "switch",
                "services": {
                    "turn_on": {"fields": {}},
                    "turn_off": {"fields": {}},
                },
            },
            {
                "domain": "homeassistant",
                "services": {
                    "restart": {"fields": {}},
                    "turn_on": {"fields": {}},
                    "turn_off": {"fields": {}},
                    "toggle": {"fields": {}},
                },
            },
        ]
    )

    client.get_area_registry = AsyncMock(
        return_value=[
            {"area_id": "living_room", "name": "Living Room"},
            {"area_id": "bedroom", "name": "Bedroom"},
        ]
    )

    return client


@pytest.fixture
def cache(mock_ha_client: MagicMock):
    """Create a registry cache from the mock client."""
    from src.schema.ha.registry_cache import HARegistryCache

    return HARegistryCache(ha_client=mock_ha_client)


# =============================================================================
# SEMANTIC VALIDATOR CORE
# =============================================================================


class TestSemanticValidator:
    """Test the SemanticValidator orchestrator."""

    @pytest.mark.asyncio
    async def test_validate_valid_automation(self, cache) -> None:
        """Semantically valid automation produces no errors."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Motion Lights
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
mode: single
""")
        result = await validator.validate(data, schema_name="ha.automation")
        assert result.valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_catches_nonexistent_entity(self, cache) -> None:
        """Detects entity_id that doesn't exist in HA."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Bad Entity
trigger:
  - platform: state
    entity_id: light.nonexistent
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
""")
        result = await validator.validate(data, schema_name="ha.automation")
        assert result.valid is False
        assert any("light.nonexistent" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_catches_nonexistent_service(self, cache) -> None:
        """Detects service that doesn't exist in HA."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Bad Service
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.nonexistent_service
    target:
      entity_id: light.living_room
""")
        result = await validator.validate(data, schema_name="ha.automation")
        assert result.valid is False
        assert any("light.nonexistent_service" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_catches_nonexistent_action_target_entity(self, cache) -> None:
        """Detects target entity_id in action that doesn't exist."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Bad Target
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.ghost_light
""")
        result = await validator.validate(data, schema_name="ha.automation")
        assert result.valid is False
        assert any("light.ghost_light" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_catches_nonexistent_area(self, cache) -> None:
        """Detects area_id in target that doesn't exist."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Bad Area
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      area_id: nonexistent_room
""")
        result = await validator.validate(data, schema_name="ha.automation")
        assert result.valid is False
        assert any("nonexistent_room" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_catches_domain_mismatch(self, cache) -> None:
        """Detects entity domain that doesn't match service domain."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Domain Mismatch
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: switch.fan
""")
        result = await validator.validate(data, schema_name="ha.automation")
        # domain mismatch should produce a warning, not a hard error
        assert any("switch.fan" in w.message and "light" in w.message for w in result.warnings)

    @pytest.mark.asyncio
    async def test_domain_agnostic_services_no_warning(self, cache) -> None:
        """homeassistant.* services should NOT warn about domain mismatch.

        Services like homeassistant.turn_on are designed to target any domain.
        """
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Domain Agnostic
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: homeassistant.turn_on
    target:
      entity_id: light.living_room
""")
        result = await validator.validate(data, schema_name="ha.automation")
        # No domain mismatch warning for homeassistant.turn_on targeting light.*
        assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_multiple_errors(self, cache) -> None:
        """Collects multiple semantic errors in one pass."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Multi Error
trigger:
  - platform: state
    entity_id: fake.entity
    to: "on"
action:
  - service: fake.service
    target:
      entity_id: also.fake
""")
        result = await validator.validate(data, schema_name="ha.automation")
        assert result.valid is False
        assert len(result.errors) >= 2  # at least entity + service errors

    @pytest.mark.asyncio
    async def test_valid_with_condition_entities(self, cache) -> None:
        """Entities in conditions are also checked."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Condition Check
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
condition:
  - condition: state
    entity_id: input_boolean.vacation
    state: "off"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
""")
        result = await validator.validate(data, schema_name="ha.automation")
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_catches_bad_condition_entity(self, cache) -> None:
        """Bad entity in condition is caught."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)

        data = yaml.safe_load("""\
alias: Bad Condition
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
condition:
  - condition: state
    entity_id: input_boolean.nonexistent
    state: "off"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
""")
        result = await validator.validate(data, schema_name="ha.automation")
        assert result.valid is False
        assert any("input_boolean.nonexistent" in e.message for e in result.errors)


# =============================================================================
# validate_yaml_semantic() TOP-LEVEL API TESTS
# =============================================================================


class TestValidateYamlSemantic:
    """Test the top-level validate_yaml_semantic() function."""

    @pytest.mark.asyncio
    async def test_valid_yaml_semantic(self, cache) -> None:
        """Valid YAML passes both structural and semantic validation."""
        from src.schema.core import validate_yaml_semantic

        yaml_str = """\
alias: Good Automation
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
"""
        result = await validate_yaml_semantic(yaml_str, "ha.automation", cache=cache)
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_structural_failure_short_circuits(self, cache) -> None:
        """Structurally invalid YAML is returned before semantic check."""
        from src.schema.core import validate_yaml_semantic

        yaml_str = "{ invalid yaml: ["
        result = await validate_yaml_semantic(yaml_str, "ha.automation", cache=cache)
        assert result.valid is False
        assert any("syntax" in e.message.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_semantic_failure(self, cache) -> None:
        """Structurally valid but semantically invalid YAML."""
        from src.schema.core import validate_yaml_semantic

        yaml_str = """\
alias: Semantic Fail
trigger:
  - platform: state
    entity_id: light.ghost
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
"""
        result = await validate_yaml_semantic(yaml_str, "ha.automation", cache=cache)
        assert result.valid is False
        assert any("light.ghost" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_with_ha_client(self, mock_ha_client) -> None:
        """Can pass ha_client instead of pre-built cache."""
        from src.schema.core import validate_yaml_semantic

        yaml_str = """\
alias: Client Test
trigger:
  - platform: state
    entity_id: light.living_room
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.bedroom
"""
        result = await validate_yaml_semantic(yaml_str, "ha.automation", ha_client=mock_ha_client)
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_raises_without_client_or_cache(self) -> None:
        """Raises ValueError if neither ha_client nor cache provided."""
        from src.schema.core import validate_yaml_semantic

        yaml_str = """\
alias: No Client
trigger:
  - platform: state
    entity_id: light.x
    to: "on"
action:
  - service: light.turn_on
"""
        with pytest.raises(ValueError, match="ha_client or cache"):
            await validate_yaml_semantic(yaml_str, "ha.automation")

    @pytest.mark.asyncio
    async def test_semantic_with_2024_syntax(self, cache) -> None:
        """Semantic validation works with HA 2024.1+ syntax."""
        from src.schema.core import validate_yaml_semantic

        yaml_str = """\
alias: Modern Automation
triggers:
  - trigger: state
    entity_id: binary_sensor.motion
    to: "on"
actions:
  - action: light.turn_on
    target:
      entity_id: light.living_room
"""
        result = await validate_yaml_semantic(yaml_str, "ha.automation", cache=cache)
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_semantic_catches_bad_entity_in_2024_syntax(self, cache) -> None:
        """Semantic validation catches bad entities in HA 2024.1+ syntax."""
        from src.schema.core import validate_yaml_semantic

        yaml_str = """\
triggers:
  - trigger: state
    entity_id: light.nonexistent
    to: "on"
actions:
  - action: light.turn_on
    target:
      entity_id: light.living_room
"""
        result = await validate_yaml_semantic(yaml_str, "ha.automation", cache=cache)
        assert result.valid is False
        assert any("light.nonexistent" in e.message for e in result.errors)
