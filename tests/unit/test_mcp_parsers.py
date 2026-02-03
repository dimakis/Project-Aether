"""Unit tests for MCP response parsers.

Tests parsing of MCP responses into domain objects.
Constitution: Reliability & Quality - comprehensive parsing tests.
"""

import pytest

from src.mcp.parsers import (
    parse_entity_list,
    parse_single_entity,
    ParsedEntity,
)


class TestParseEntityList:
    """Tests for parse_entity_list function."""

    def test_parse_empty_list(self):
        """Test parsing empty entity list."""
        result = parse_entity_list([])
        assert result == []

    def test_parse_single_entity(self):
        """Test parsing single entity in list."""
        raw = [
            {
                "entity_id": "light.living_room",
                "state": "off",
                "name": "Living Room",
            }
        ]

        result = parse_entity_list(raw)

        assert len(result) == 1
        assert result[0].entity_id == "light.living_room"
        assert result[0].state == "off"
        assert result[0].name == "Living Room"
        assert result[0].domain == "light"

    def test_parse_multiple_entities(self):
        """Test parsing multiple entities."""
        raw = [
            {
                "entity_id": "light.living_room",
                "state": "off",
                "name": "Living Room",
            },
            {
                "entity_id": "switch.kitchen",
                "state": "on",
                "name": "Kitchen Switch",
            },
            {
                "entity_id": "sensor.temperature",
                "state": "22.5",
                "name": "Temperature",
            },
        ]

        result = parse_entity_list(raw)

        assert len(result) == 3
        assert result[0].domain == "light"
        assert result[1].domain == "switch"
        assert result[2].domain == "sensor"

    def test_parse_entity_with_area(self):
        """Test parsing entity with area_id."""
        raw = [
            {
                "entity_id": "light.bedroom",
                "state": "on",
                "name": "Bedroom Light",
                "area_id": "bedroom",
            }
        ]

        result = parse_entity_list(raw)

        assert result[0].area_id == "bedroom"

    def test_parse_entity_with_device(self):
        """Test parsing entity with device_id."""
        raw = [
            {
                "entity_id": "light.hue",
                "state": "off",
                "name": "Hue Light",
                "device_id": "device_abc123",
            }
        ]

        result = parse_entity_list(raw)

        assert result[0].device_id == "device_abc123"

    def test_parse_entity_with_attributes(self):
        """Test parsing entity with attributes."""
        raw = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "name": "Living Room",
                "attributes": {
                    "brightness": 255,
                    "color_mode": "brightness",
                    "friendly_name": "Living Room Light",
                },
            }
        ]

        result = parse_entity_list(raw)

        assert result[0].attributes is not None
        assert result[0].attributes["brightness"] == 255

    def test_parse_extracts_domain_from_entity_id(self):
        """Test domain extraction from entity_id."""
        raw = [
            {"entity_id": "binary_sensor.motion", "state": "off", "name": "Motion"},
            {"entity_id": "climate.living_room", "state": "heat", "name": "HVAC"},
            {"entity_id": "cover.garage", "state": "closed", "name": "Garage Door"},
        ]

        result = parse_entity_list(raw)

        assert result[0].domain == "binary_sensor"
        assert result[1].domain == "climate"
        assert result[2].domain == "cover"

    def test_parse_handles_missing_name(self):
        """Test parsing entity without name field."""
        raw = [
            {
                "entity_id": "light.test",
                "state": "off",
            }
        ]

        result = parse_entity_list(raw)

        # Should use entity_id as fallback name
        assert result[0].name == "light.test" or result[0].name == "test"

    def test_parse_handles_null_state(self):
        """Test parsing entity with null state."""
        raw = [
            {
                "entity_id": "sensor.unavailable",
                "state": None,
                "name": "Unavailable Sensor",
            }
        ]

        result = parse_entity_list(raw)

        assert result[0].state is None or result[0].state == "unknown"


class TestParseSingleEntity:
    """Tests for parse_single_entity function."""

    def test_parse_full_entity(self):
        """Test parsing entity with all fields."""
        raw = {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {
                "brightness": 200,
                "friendly_name": "Living Room",
                "supported_features": 44,
                "device_class": None,
            },
            "area_id": "living_room",
            "device_id": "device_123",
        }

        result = parse_single_entity(raw)

        assert isinstance(result, ParsedEntity)
        assert result.entity_id == "light.living_room"
        assert result.state == "on"
        assert result.domain == "light"
        assert result.area_id == "living_room"
        assert result.device_id == "device_123"

    def test_parse_minimal_entity(self):
        """Test parsing entity with minimal fields."""
        raw = {
            "entity_id": "switch.test",
            "state": "off",
        }

        result = parse_single_entity(raw)

        assert result.entity_id == "switch.test"
        assert result.state == "off"
        assert result.domain == "switch"
        assert result.area_id is None
        assert result.device_id is None


class TestParsedEntity:
    """Tests for ParsedEntity dataclass."""

    def test_parsed_entity_creation(self):
        """Test creating ParsedEntity directly."""
        entity = ParsedEntity(
            entity_id="light.test",
            domain="light",
            name="Test Light",
            state="off",
        )

        assert entity.entity_id == "light.test"
        assert entity.domain == "light"
        assert entity.name == "Test Light"
        assert entity.state == "off"
        assert entity.area_id is None
        assert entity.device_id is None
        assert entity.attributes is None

    def test_parsed_entity_with_all_fields(self):
        """Test creating ParsedEntity with all fields."""
        entity = ParsedEntity(
            entity_id="sensor.temp",
            domain="sensor",
            name="Temperature",
            state="22.5",
            area_id="living_room",
            device_id="device_123",
            attributes={"unit_of_measurement": "°C"},
        )

        assert entity.area_id == "living_room"
        assert entity.device_id == "device_123"
        assert entity.attributes["unit_of_measurement"] == "°C"
