"""End-to-end tests for entity discovery flow.

Tests full discovery workflow with mocked Home Assistant.
Constitution: Reliability & Quality - E2E workflow validation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_ha_entities():
    """Create realistic mock HA entity data."""
    return [
        {
            "entity_id": "light.living_room_main",
            "state": "on",
            "name": "Living Room Main Light",
            "area_id": "living_room",
            "device_id": "device_hue_001",
            "attributes": {
                "brightness": 200,
                "color_mode": "brightness",
                "supported_features": 44,
                "friendly_name": "Living Room Main Light",
            },
        },
        {
            "entity_id": "light.living_room_accent",
            "state": "off",
            "name": "Living Room Accent Light",
            "area_id": "living_room",
            "device_id": "device_hue_001",
            "attributes": {
                "brightness": 0,
                "supported_features": 44,
            },
        },
        {
            "entity_id": "sensor.living_room_temperature",
            "state": "22.5",
            "name": "Living Room Temperature",
            "area_id": "living_room",
            "device_id": "device_temp_001",
            "attributes": {
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
            },
        },
        {
            "entity_id": "switch.kitchen_outlet",
            "state": "on",
            "name": "Kitchen Outlet",
            "area_id": "kitchen",
            "device_id": "device_switch_001",
            "attributes": {
                "supported_features": 0,
            },
        },
        {
            "entity_id": "binary_sensor.front_door",
            "state": "off",
            "name": "Front Door",
            "area_id": "entrance",
            "device_id": "device_door_001",
            "attributes": {
                "device_class": "door",
            },
        },
    ]


@pytest.fixture
def mock_ha_client(mock_ha_entities):
    """Create mock HA client with realistic responses."""
    client = MagicMock()

    client.list_entities = AsyncMock(return_value=mock_ha_entities)
    client.get_entity = AsyncMock(
        side_effect=lambda entity_id: next(
            (e for e in mock_ha_entities if e["entity_id"] == entity_id),
            None,
        )
    )
    client.list_automations = AsyncMock(return_value=[])
    client.system_overview = AsyncMock(
        return_value={
            "total_entities": len(mock_ha_entities),
            "domains": {
                "light": {"count": 2},
                "sensor": {"count": 1},
                "switch": {"count": 1},
                "binary_sensor": {"count": 1},
            },
        }
    )

    return client


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDiscoveryE2E:
    """End-to-end tests for discovery flow."""

    async def test_discovery_finds_all_entities(self, mock_ha_client, mock_ha_entities):
        """Test that discovery finds all entities from HA."""
        from src.ha.parsers import parse_entity_list

        # Parse entities like discovery would
        entities = parse_entity_list(mock_ha_entities)

        assert len(entities) == 5
        assert any(e.entity_id == "light.living_room_main" for e in entities)
        assert any(e.domain == "sensor" for e in entities)

    async def test_discovery_extracts_areas(self, mock_ha_client, mock_ha_entities):
        """Test that discovery extracts unique areas."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import infer_areas_from_entities

        entities = parse_entity_list(mock_ha_entities)
        areas = infer_areas_from_entities(entities)

        assert len(areas) == 3  # living_room, kitchen, entrance
        assert "living_room" in areas
        assert "kitchen" in areas
        assert "entrance" in areas

    async def test_discovery_extracts_devices(self, mock_ha_client, mock_ha_entities):
        """Test that discovery extracts unique devices."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import infer_devices_from_entities

        entities = parse_entity_list(mock_ha_entities)
        devices = infer_devices_from_entities(entities)

        assert len(devices) == 4  # 4 unique device_ids
        assert "device_hue_001" in devices
        assert "device_temp_001" in devices

    async def test_discovery_associates_entities_with_areas(
        self, mock_ha_client, mock_ha_entities
    ):
        """Test that entities are associated with correct areas."""
        from src.ha.parsers import parse_entity_list

        entities = parse_entity_list(mock_ha_entities)

        living_room_entities = [e for e in entities if e.area_id == "living_room"]
        kitchen_entities = [e for e in entities if e.area_id == "kitchen"]

        assert len(living_room_entities) == 3  # 2 lights + 1 sensor
        assert len(kitchen_entities) == 1  # 1 switch

    async def test_discovery_extracts_metadata(self, mock_ha_client, mock_ha_entities):
        """Test that discovery extracts entity metadata."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import extract_entity_metadata

        entities = parse_entity_list(mock_ha_entities)

        # Find temperature sensor
        temp_sensor = next(
            e for e in entities if e.entity_id == "sensor.living_room_temperature"
        )
        metadata = extract_entity_metadata(temp_sensor)

        assert metadata["device_class"] == "temperature"
        assert metadata["unit_of_measurement"] == "°C"
        assert metadata["state_class"] == "measurement"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDiscoveryWithDatabase:
    """E2E tests that would use a real database (skipped without testcontainers)."""

    @pytest.mark.skip(reason="Requires testcontainers setup")
    async def test_full_discovery_workflow(self, mock_ha_client):
        """Test complete discovery workflow with database."""
        # This test would:
        # 1. Start with empty database
        # 2. Run discovery
        # 3. Verify entities are persisted
        # 4. Run discovery again
        # 5. Verify entities are updated (not duplicated)
        pass

    @pytest.mark.skip(reason="Requires testcontainers setup")
    async def test_discovery_handles_removed_entities(self, mock_ha_client):
        """Test that discovery removes entities no longer in HA."""
        pass


@pytest.mark.e2e
class TestDiscoveryStatistics:
    """Tests for discovery statistics."""

    def test_discovery_counts_domains(self, mock_ha_entities):
        """Test that discovery correctly counts entities per domain."""
        from src.ha.parsers import parse_entity_list

        entities = parse_entity_list(mock_ha_entities)
        domain_counts = {}

        for entity in entities:
            domain_counts[entity.domain] = domain_counts.get(entity.domain, 0) + 1

        assert domain_counts["light"] == 2
        assert domain_counts["sensor"] == 1
        assert domain_counts["switch"] == 1
        assert domain_counts["binary_sensor"] == 1

    def test_discovery_state_distribution(self, mock_ha_entities):
        """Test state distribution statistics."""
        from src.ha.parsers import parse_entity_list

        entities = parse_entity_list(mock_ha_entities)
        state_counts = {}

        for entity in entities:
            state = entity.state
            state_counts[state] = state_counts.get(state, 0) + 1

        assert state_counts.get("on", 0) == 2  # 1 light + 1 switch
        assert state_counts.get("off", 0) == 2  # 1 light + 1 binary_sensor
