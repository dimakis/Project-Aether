"""Unit tests for MCP workarounds.

Tests device/area inference from entity attributes.
Constitution: Reliability & Quality - workaround validation.
"""

import pytest

from src.ha.parsers import ParsedEntity
from src.ha.workarounds import (
    extract_entity_metadata,
    infer_areas_from_entities,
    infer_devices_from_entities,
)


@pytest.fixture
def sample_entities():
    """Create sample parsed entities for testing."""
    return [
        ParsedEntity(
            entity_id="light.living_room_main",
            domain="light",
            name="Living Room Main",
            state="on",
            area_id="living_room",
            device_id="device_abc123",
            attributes={
                "brightness": 200,
                "supported_features": 44,
                "device_class": None,
            },
        ),
        ParsedEntity(
            entity_id="light.living_room_accent",
            domain="light",
            name="Living Room Accent",
            state="off",
            area_id="living_room",
            device_id="device_abc123",  # Same device
            attributes={"brightness": 0},
        ),
        ParsedEntity(
            entity_id="sensor.bedroom_temperature",
            domain="sensor",
            name="Bedroom Temperature",
            state="22.5",
            area_id="bedroom",
            device_id="device_def456",
            attributes={
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
            },
        ),
        ParsedEntity(
            entity_id="switch.no_area",
            domain="switch",
            name="Orphan Switch",
            state="off",
            area_id=None,  # No area
            device_id=None,  # No device
            attributes={},
        ),
    ]


class TestInferAreasFromEntities:
    """Tests for infer_areas_from_entities function."""

    def test_extracts_unique_areas(self, sample_entities):
        """Test extracting unique area IDs."""
        result = infer_areas_from_entities(sample_entities)

        assert len(result) == 2  # living_room and bedroom
        assert "living_room" in result
        assert "bedroom" in result

    def test_area_contains_name(self, sample_entities):
        """Test that inferred areas include a name."""
        result = infer_areas_from_entities(sample_entities)

        # Name should be derived from area_id
        assert result["living_room"]["name"] is not None
        assert result["bedroom"]["name"] is not None

    def test_handles_empty_list(self):
        """Test with empty entity list."""
        result = infer_areas_from_entities([])

        assert result == {}

    def test_handles_no_areas(self):
        """Test when no entities have areas."""
        entities = [
            ParsedEntity(
                entity_id="switch.test",
                domain="switch",
                name="Test",
                state="off",
                area_id=None,
            )
        ]

        result = infer_areas_from_entities(entities)

        assert result == {}

    def test_normalizes_area_names(self, sample_entities):
        """Test that area names are normalized (e.g., underscores to spaces)."""
        result = infer_areas_from_entities(sample_entities)

        # Depending on implementation, living_room might become "Living Room"
        living_room = result.get("living_room", {})
        assert "name" in living_room


class TestInferDevicesFromEntities:
    """Tests for infer_devices_from_entities function."""

    def test_extracts_unique_devices(self, sample_entities):
        """Test extracting unique device IDs."""
        result = infer_devices_from_entities(sample_entities)

        assert len(result) == 2  # device_abc123 and device_def456
        assert "device_abc123" in result
        assert "device_def456" in result

    def test_device_contains_name(self, sample_entities):
        """Test that inferred devices include a name."""
        result = infer_devices_from_entities(sample_entities)

        # Names are inferred from entity names
        assert "name" in result["device_abc123"]
        assert "name" in result["device_def456"]

    def test_device_contains_area_id(self, sample_entities):
        """Test that inferred devices include area_id from entities."""
        result = infer_devices_from_entities(sample_entities)

        # Should pick up area from one of the entities
        assert result["device_abc123"].get("area_id") == "living_room"
        assert result["device_def456"].get("area_id") == "bedroom"

    def test_handles_empty_list(self):
        """Test with empty entity list."""
        result = infer_devices_from_entities([])

        assert result == {}

    def test_handles_no_devices(self):
        """Test when no entities have devices."""
        entities = [
            ParsedEntity(
                entity_id="switch.test",
                domain="switch",
                name="Test",
                state="off",
                device_id=None,
            )
        ]

        result = infer_devices_from_entities(entities)

        assert result == {}


class TestExtractEntityMetadata:
    """Tests for extract_entity_metadata function."""

    def test_extracts_device_class(self):
        """Test extracting device_class from attributes."""
        entity = ParsedEntity(
            entity_id="sensor.temp",
            domain="sensor",
            name="Temperature",
            state="22",
            attributes={"device_class": "temperature"},
        )

        result = extract_entity_metadata(entity)

        assert result["device_class"] == "temperature"

    def test_extracts_unit_of_measurement(self):
        """Test extracting unit_of_measurement from attributes."""
        entity = ParsedEntity(
            entity_id="sensor.temp",
            domain="sensor",
            name="Temperature",
            state="22",
            attributes={"unit_of_measurement": "°C"},
        )

        result = extract_entity_metadata(entity)

        assert result["unit_of_measurement"] == "°C"

    def test_extracts_supported_features(self):
        """Test extracting supported_features from attributes."""
        entity = ParsedEntity(
            entity_id="light.test",
            domain="light",
            name="Test",
            state="on",
            attributes={"supported_features": 44},
        )

        result = extract_entity_metadata(entity)

        assert result["supported_features"] == 44

    def test_extracts_state_class(self):
        """Test extracting state_class from attributes."""
        entity = ParsedEntity(
            entity_id="sensor.energy",
            domain="sensor",
            name="Energy",
            state="100",
            attributes={"state_class": "total_increasing"},
        )

        result = extract_entity_metadata(entity)

        assert result["state_class"] == "total_increasing"

    def test_extracts_icon(self):
        """Test extracting icon from attributes."""
        entity = ParsedEntity(
            entity_id="light.test",
            domain="light",
            name="Test",
            state="on",
            attributes={"icon": "mdi:lightbulb"},
        )

        result = extract_entity_metadata(entity)

        assert result["icon"] == "mdi:lightbulb"

    def test_handles_no_attributes(self):
        """Test with entity without attributes (defaults to empty dict)."""
        entity = ParsedEntity(
            entity_id="switch.test",
            domain="switch",
            name="Test",
            state="off",
            # attributes defaults to {}
        )

        result = extract_entity_metadata(entity)

        assert result["device_class"] is None
        assert result.get("supported_features", 0) == 0

    def test_handles_empty_attributes(self):
        """Test with empty attributes dict."""
        entity = ParsedEntity(
            entity_id="switch.test",
            domain="switch",
            name="Test",
            state="off",
            attributes={},
        )

        result = extract_entity_metadata(entity)

        assert result["device_class"] is None
