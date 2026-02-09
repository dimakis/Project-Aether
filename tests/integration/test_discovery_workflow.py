"""Integration tests for LangGraph discovery workflow.

Tests the discovery workflow with mocked HA client.
Constitution: Reliability & Quality - workflow integration testing.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_workflow_entities():
    """Create mock entities for workflow testing."""
    return [
        {
            "entity_id": "light.bedroom_ceiling",
            "state": "off",
            "name": "Bedroom Ceiling Light",
            "domain": "light",
            "area_id": "bedroom",
            "device_id": "device_light_001",
            "attributes": {
                "brightness": 0,
                "supported_features": 44,
                "color_mode": "brightness",
            },
        },
        {
            "entity_id": "sensor.bedroom_temperature",
            "state": "21.5",
            "name": "Bedroom Temperature",
            "domain": "sensor",
            "area_id": "bedroom",
            "device_id": "device_sensor_001",
            "attributes": {
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
            },
        },
        {
            "entity_id": "automation.morning_lights",
            "state": "on",
            "name": "Morning Lights",
            "domain": "automation",
            "attributes": {
                "mode": "single",
                "last_triggered": "2026-02-03T07:00:00Z",
            },
        },
        {
            "entity_id": "script.goodnight",
            "state": "off",
            "name": "Goodnight Routine",
            "domain": "script",
            "attributes": {
                "mode": "single",
                "icon": "mdi:sleep",
            },
        },
    ]


@pytest.fixture
def mock_workflow_ha_client(mock_workflow_entities):
    """Create mock HA client for workflow testing."""
    client = MagicMock()

    # Configure async methods
    client.list_entities = AsyncMock(return_value=mock_workflow_entities)
    client.system_overview = AsyncMock(
        return_value={
            "total_entities": len(mock_workflow_entities),
            "domains": {
                "light": {"count": 1},
                "sensor": {"count": 1},
                "automation": {"count": 1},
                "script": {"count": 1},
            },
        }
    )
    client.connect = AsyncMock()

    return client


@pytest.mark.integration
@pytest.mark.asyncio
class TestDiscoveryWorkflow:
    """Integration tests for the discovery workflow."""

    async def test_workflow_parses_entities(self, mock_workflow_ha_client, mock_workflow_entities):
        """Test that workflow correctly parses MCP entity responses."""
        from src.ha.parsers import parse_entity_list

        # Simulate what workflow does
        raw_entities = await mock_workflow_ha_client.list_entities(detailed=True)
        parsed = parse_entity_list(raw_entities)

        assert len(parsed) == 4
        assert any(e.entity_id == "light.bedroom_ceiling" for e in parsed)
        assert any(e.domain == "automation" for e in parsed)

    async def test_workflow_infers_areas(self, mock_workflow_ha_client, mock_workflow_entities):
        """Test that workflow infers areas from entities."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import infer_areas_from_entities

        raw_entities = await mock_workflow_ha_client.list_entities(detailed=True)
        parsed = parse_entity_list(raw_entities)
        areas = infer_areas_from_entities(parsed)

        assert "bedroom" in areas
        # Name is title-cased when inferred from area_id
        assert areas["bedroom"]["name"].lower() == "bedroom"

    async def test_workflow_infers_devices(self, mock_workflow_ha_client, mock_workflow_entities):
        """Test that workflow infers devices from entities."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import infer_devices_from_entities

        raw_entities = await mock_workflow_ha_client.list_entities(detailed=True)
        parsed = parse_entity_list(raw_entities)
        devices = infer_devices_from_entities(parsed)

        assert "device_light_001" in devices
        assert "device_sensor_001" in devices
        # Automations/scripts don't have devices
        assert len(devices) == 2

    async def test_workflow_extracts_metadata(
        self, mock_workflow_ha_client, mock_workflow_entities
    ):
        """Test that workflow extracts entity metadata correctly."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import extract_entity_metadata

        raw_entities = await mock_workflow_ha_client.list_entities(detailed=True)
        parsed = parse_entity_list(raw_entities)

        # Find temperature sensor
        temp = next(e for e in parsed if e.entity_id == "sensor.bedroom_temperature")
        metadata = extract_entity_metadata(temp)

        assert metadata["device_class"] == "temperature"
        assert metadata["unit_of_measurement"] == "°C"
        assert metadata["state_class"] == "measurement"

    async def test_workflow_counts_domains(self, mock_workflow_ha_client, mock_workflow_entities):
        """Test that workflow correctly counts entities per domain."""
        from src.ha.parsers import parse_entity_list

        raw_entities = await mock_workflow_ha_client.list_entities(detailed=True)
        parsed = parse_entity_list(raw_entities)

        domain_counts = {}
        for entity in parsed:
            domain_counts[entity.domain] = domain_counts.get(entity.domain, 0) + 1

        assert domain_counts["light"] == 1
        assert domain_counts["sensor"] == 1
        assert domain_counts["automation"] == 1
        assert domain_counts["script"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
class TestDiscoverySyncService:
    """Integration tests for DiscoverySyncService."""

    @pytest.mark.requires_postgres
    async def test_sync_service_creates_session(self, integration_session, mock_workflow_ha_client):
        """Test that sync service creates a discovery session."""
        from src.dal.sync import DiscoverySyncService

        service = DiscoverySyncService(integration_session, mock_workflow_ha_client)
        session = await service.run_discovery(triggered_by="test")

        assert session.id is not None
        assert session.status.value == "completed"
        assert session.triggered_by == "test"

    @pytest.mark.requires_postgres
    async def test_sync_service_counts_entities(
        self, integration_session, mock_workflow_ha_client, mock_workflow_entities
    ):
        """Test that sync service correctly counts discovered entities."""
        from src.dal.sync import DiscoverySyncService

        service = DiscoverySyncService(integration_session, mock_workflow_ha_client)
        session = await service.run_discovery()

        assert session.entities_found == len(mock_workflow_entities)
        assert session.entities_added == len(mock_workflow_entities)

    @pytest.mark.requires_postgres
    async def test_sync_service_tracks_areas(self, integration_session, mock_workflow_ha_client):
        """Test that sync service tracks discovered areas."""
        from src.dal.sync import DiscoverySyncService

        service = DiscoverySyncService(integration_session, mock_workflow_ha_client)
        session = await service.run_discovery()

        # Only "bedroom" has area_id in mock data
        assert session.areas_found == 1

    @pytest.mark.requires_postgres
    async def test_sync_service_tracks_devices(self, integration_session, mock_workflow_ha_client):
        """Test that sync service tracks discovered devices."""
        from src.dal.sync import DiscoverySyncService

        service = DiscoverySyncService(integration_session, mock_workflow_ha_client)
        session = await service.run_discovery()

        # Two devices in mock data
        assert session.devices_found == 2

    @pytest.mark.requires_postgres
    async def test_sync_service_records_mcp_gaps(
        self, integration_session, mock_workflow_ha_client
    ):
        """Test that sync service records MCP capability gaps."""
        from src.dal.sync import DiscoverySyncService

        service = DiscoverySyncService(integration_session, mock_workflow_ha_client)
        session = await service.run_discovery()

        assert session.mcp_gaps_encountered is not None
        assert "floors_not_available" in session.mcp_gaps_encountered

    @pytest.mark.requires_postgres
    async def test_sync_service_idempotent(
        self, integration_session, mock_workflow_ha_client, mock_workflow_entities
    ):
        """Test that running sync twice doesn't duplicate entities."""
        from src.dal.sync import DiscoverySyncService

        service = DiscoverySyncService(integration_session, mock_workflow_ha_client)

        # First run
        session1 = await service.run_discovery()
        assert session1.entities_added == len(mock_workflow_entities)

        # Commit to persist
        await integration_session.commit()

        # Second run should update, not add
        session2 = await service.run_discovery()
        assert session2.entities_updated == len(mock_workflow_entities)
        assert session2.entities_added == 0


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowEdgeCases:
    """Test edge cases in the discovery workflow."""

    async def test_workflow_handles_empty_response(self):
        """Test workflow handles empty entity list."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import infer_areas_from_entities, infer_devices_from_entities

        parsed = parse_entity_list([])
        areas = infer_areas_from_entities(parsed)
        devices = infer_devices_from_entities(parsed)

        assert len(parsed) == 0
        assert len(areas) == 0
        assert len(devices) == 0

    async def test_workflow_handles_entities_without_areas(self):
        """Test workflow handles entities without area_id."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import infer_areas_from_entities

        entities = [
            {"entity_id": "sun.sun", "state": "above_horizon", "name": "Sun"},
            {"entity_id": "weather.home", "state": "sunny", "name": "Weather"},
        ]

        parsed = parse_entity_list(entities)
        areas = infer_areas_from_entities(parsed)

        assert len(parsed) == 2
        assert len(areas) == 0

    async def test_workflow_handles_entities_without_devices(self):
        """Test workflow handles entities without device_id."""
        from src.ha.parsers import parse_entity_list
        from src.ha.workarounds import infer_devices_from_entities

        entities = [
            {"entity_id": "input_boolean.test", "state": "off", "name": "Test"},
        ]

        parsed = parse_entity_list(entities)
        devices = infer_devices_from_entities(parsed)

        assert len(parsed) == 1
        assert len(devices) == 0

    async def test_workflow_handles_special_states(self):
        """Test workflow handles special entity states."""
        from src.ha.parsers import parse_entity_list

        entities = [
            {"entity_id": "sensor.unavailable", "state": "unavailable", "name": "Unavailable"},
            {"entity_id": "sensor.unknown", "state": "unknown", "name": "Unknown"},
            {"entity_id": "sensor.none", "state": None, "name": "None State"},
        ]

        parsed = parse_entity_list(entities)

        assert len(parsed) == 3
        assert parsed[0].state == "unavailable"
        assert parsed[1].state == "unknown"
        # None state should be handled gracefully
        assert parsed[2].state is None or parsed[2].state == "unknown"


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowDomainFiltering:
    """Test domain filtering in workflow."""

    async def test_filter_automation_entities(
        self, mock_workflow_ha_client, mock_workflow_entities
    ):
        """Test filtering automation entities from discovery results."""
        from src.ha.parsers import parse_entity_list

        raw_entities = await mock_workflow_ha_client.list_entities(detailed=True)
        parsed = parse_entity_list(raw_entities)

        automations = [e for e in parsed if e.domain == "automation"]

        assert len(automations) == 1
        assert automations[0].entity_id == "automation.morning_lights"

    async def test_filter_script_entities(self, mock_workflow_ha_client, mock_workflow_entities):
        """Test filtering script entities from discovery results."""
        from src.ha.parsers import parse_entity_list

        raw_entities = await mock_workflow_ha_client.list_entities(detailed=True)
        parsed = parse_entity_list(raw_entities)

        scripts = [e for e in parsed if e.domain == "script"]

        assert len(scripts) == 1
        assert scripts[0].entity_id == "script.goodnight"

    async def test_automation_mode_extraction(
        self, mock_workflow_ha_client, mock_workflow_entities
    ):
        """Test extracting automation mode from attributes."""
        from src.ha.parsers import parse_entity_list

        raw_entities = await mock_workflow_ha_client.list_entities(detailed=True)
        parsed = parse_entity_list(raw_entities)

        automation = next(e for e in parsed if e.domain == "automation")

        assert automation.attributes.get("mode") == "single"
