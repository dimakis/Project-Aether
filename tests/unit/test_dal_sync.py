"""Unit tests for DiscoverySyncService.

Tests the sync orchestration logic for syncing Home Assistant entities,
areas, devices, automations, scripts, and scenes into PostgreSQL.

Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dal.sync import DiscoverySyncService, run_discovery
from src.storage.entities import DiscoverySession, DiscoveryStatus


@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    client = MagicMock()
    client.list_entities = AsyncMock()
    return client


@pytest.fixture
def sync_service(mock_session, mock_mcp_client):
    """Create DiscoverySyncService with mocked dependencies."""
    service = DiscoverySyncService(mock_session, mock_mcp_client)
    # Mock registry repos so run_discovery tests don't hit real DB
    service.automation_repo = MagicMock()
    service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
    service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
    service.automation_repo.delete = AsyncMock(return_value=True)
    service.script_repo = MagicMock()
    service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
    service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
    service.script_repo.delete = AsyncMock(return_value=True)
    service.scene_repo = MagicMock()
    service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
    service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())
    service.scene_repo.delete = AsyncMock(return_value=True)
    return service


@pytest.fixture
def sample_entities():
    """Create sample parsed entities for testing."""
    from src.mcp.parsers import ParsedEntity

    return [
        ParsedEntity(
            entity_id="light.living_room",
            domain="light",
            name="Living Room Light",
            state="off",
            attributes={"brightness": 0, "friendly_name": "Living Room Light"},
            area_id="living_room",
            device_id="device_1",
            device_class=None,
            unit_of_measurement=None,
            supported_features=44,
        ),
        ParsedEntity(
            entity_id="sensor.temperature",
            domain="sensor",
            name="Temperature Sensor",
            state="22.5",
            attributes={"unit_of_measurement": "°C", "device_class": "temperature"},
            area_id="living_room",
            device_id="device_1",
            device_class="temperature",
            unit_of_measurement="°C",
            supported_features=0,
        ),
        ParsedEntity(
            entity_id="automation.morning_routine",
            domain="automation",
            name="Morning Routine",
            state="on",
            attributes={},
            area_id=None,
            device_id=None,
            device_class=None,
            unit_of_measurement=None,
            supported_features=0,
        ),
        ParsedEntity(
            entity_id="script.turn_on_lights",
            domain="script",
            name="Turn On Lights",
            state="off",
            attributes={},
            area_id=None,
            device_id=None,
            device_class=None,
            unit_of_measurement=None,
            supported_features=0,
        ),
        ParsedEntity(
            entity_id="scene.evening",
            domain="scene",
            name="Evening Scene",
            state="scening",
            attributes={},
            area_id=None,
            device_id=None,
            device_class=None,
            unit_of_measurement=None,
            supported_features=0,
        ),
    ]


@pytest.fixture
def mock_repositories(mock_session):
    """Create mock repositories."""
    entity_repo = MagicMock()
    entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
    entity_repo.upsert = AsyncMock()
    entity_repo.delete = AsyncMock()
    entity_repo.get_domain_counts = AsyncMock(return_value={"light": 1, "sensor": 1})

    device_repo = MagicMock()
    device_repo.upsert = AsyncMock()

    area_repo = MagicMock()
    area_repo.upsert = AsyncMock()

    return {
        "entity_repo": entity_repo,
        "device_repo": device_repo,
        "area_repo": area_repo,
    }


class TestDiscoverySyncServiceInit:
    """Tests for DiscoverySyncService initialization."""

    @pytest.mark.unit
    def test_init(self, mock_session, mock_mcp_client):
        """Test service initialization."""
        service = DiscoverySyncService(mock_session, mock_mcp_client)

        assert service.session == mock_session
        assert service.mcp == mock_mcp_client
        assert service.entity_repo is not None
        assert service.device_repo is not None
        assert service.area_repo is not None


class TestRunDiscoveryFullSync:
    """Tests for successful full sync scenarios."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_successful_full_sync(
        self, sync_service, mock_session, mock_mcp_client, sample_entities
    ):
        """Test successful full sync with entities, areas, and devices."""
        # Setup MCP client response
        raw_entities = [
            {
                "entity_id": "light.living_room",
                "state": "off",
                "name": "Living Room Light",
                "area_id": "living_room",
                "device_id": "device_1",
                "attributes": {"brightness": 0},
            },
            {
                "entity_id": "sensor.temperature",
                "state": "22.5",
                "name": "Temperature Sensor",
                "area_id": "living_room",
                "device_id": "device_1",
                "attributes": {"unit_of_measurement": "°C", "device_class": "temperature"},
            },
        ]
        mock_mcp_client.list_entities.return_value = raw_entities

        # Mock repositories
        mock_area = MagicMock()
        mock_area.id = str(uuid4())
        sync_service.area_repo.upsert = AsyncMock(return_value=(mock_area, True))

        mock_device = MagicMock()
        mock_device.id = str(uuid4())
        sync_service.device_repo.upsert = AsyncMock(return_value=(mock_device, True))

        mock_entity = MagicMock()
        sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
        sync_service.entity_repo.upsert = AsyncMock(return_value=(mock_entity, True))
        sync_service.entity_repo.get_domain_counts = AsyncMock(
            return_value={"light": 1, "sensor": 1}
        )

        # Mock workarounds
        with patch("src.dal.sync.infer_areas_from_entities") as mock_infer_areas, patch(
            "src.dal.sync.infer_devices_from_entities"
        ) as mock_infer_devices, patch("src.dal.sync.parse_entity_list") as mock_parse:
            mock_infer_areas.return_value = {
                "living_room": {"ha_area_id": "living_room", "name": "Living Room"}
            }
            mock_infer_devices.return_value = {
                "device_1": {
                    "ha_device_id": "device_1",
                    "name": "Device 1",
                    "area_id": "living_room",
                }
            }
            mock_parse.return_value = sample_entities[:2]

            # Run discovery
            result = await sync_service.run_discovery(triggered_by="manual")

            # Verify session was created
            assert isinstance(result, DiscoverySession)
            assert result.status == DiscoveryStatus.COMPLETED
            assert result.entities_found == 2
            assert result.areas_found == 1
            assert result.devices_found == 1
            assert result.entities_added == 2
            assert result.entities_updated == 0
            assert result.entities_removed == 0
            assert result.domain_counts == {"light": 1, "sensor": 1}

            # Verify MCP was called
            mock_mcp_client.list_entities.assert_called_once_with(detailed=True)

            # Verify repositories were called
            assert sync_service.area_repo.upsert.call_count == 1
            assert sync_service.device_repo.upsert.call_count == 1
            assert sync_service.entity_repo.upsert.call_count == 2

            # Verify session was committed
            mock_session.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_with_mlflow_run_id(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test discovery with MLflow run ID."""
        mock_mcp_client.list_entities.return_value = []

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=[]):
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={})

            result = await sync_service.run_discovery(
                triggered_by="scheduled", mlflow_run_id="run-123"
            )

            assert result.mlflow_run_id == "run-123"
            assert result.triggered_by == "scheduled"


class TestRunDiscoveryEmptyData:
    """Tests for sync with empty or minimal data."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_empty_ha_response(
        self, sync_service, mock_mcp_client
    ):
        """Test sync when HA returns no entities."""
        mock_mcp_client.list_entities.return_value = []

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=[]):
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={})

            result = await sync_service.run_discovery()

            assert result.entities_found == 0
            assert result.areas_found == 0
            assert result.devices_found == 0
            assert result.entities_added == 0
            assert result.entities_updated == 0
            assert result.entities_removed == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_partial_data_missing_fields(
        self, sync_service, mock_mcp_client
    ):
        """Test sync with entities missing some fields."""
        raw_entities = [
            {
                "entity_id": "light.unknown",
                "state": "off",
                # Missing name, area_id, device_id
                "attributes": {},
            }
        ]
        mock_mcp_client.list_entities.return_value = raw_entities

        from src.mcp.parsers import ParsedEntity

        parsed_entities = [
            ParsedEntity(
                entity_id="light.unknown",
                domain="light",
                name="light.unknown",  # Fallback name
                state="off",
                attributes={},
                area_id=None,
                device_id=None,
                device_class=None,
                unit_of_measurement=None,
                supported_features=0,
            )
        ]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=parsed_entities):
            mock_entity = MagicMock()
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(mock_entity, True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"light": 1})

            result = await sync_service.run_discovery()

            assert result.entities_found == 1
            # Should still sync successfully even with missing fields
            sync_service.entity_repo.upsert.assert_called_once()


class TestRunDiscoveryUpsertBehavior:
    """Tests for upsert behavior (create vs update)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_creates_new_entities(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that new entities are created."""
        mock_mcp_client.list_entities.return_value = [{"entity_id": "light.new"}]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:1]):
            mock_entity = MagicMock()
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(mock_entity, True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"light": 1})

            result = await sync_service.run_discovery()

            assert result.entities_added == 1
            assert result.entities_updated == 0
            sync_service.entity_repo.upsert.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_updates_existing_entities(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that existing entities are updated."""
        mock_mcp_client.list_entities.return_value = [{"entity_id": "light.living_room"}]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:1]):
            mock_entity = MagicMock()
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(
                return_value={"light.living_room"}
            )
            sync_service.entity_repo.upsert = AsyncMock(return_value=(mock_entity, False))
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"light": 1})

            result = await sync_service.run_discovery()

            assert result.entities_added == 0
            assert result.entities_updated == 1
            sync_service.entity_repo.upsert.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_mixed_create_and_update(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test sync with mix of new and existing entities."""
        mock_mcp_client.list_entities.return_value = [
            {"entity_id": "light.existing"},
            {"entity_id": "light.new"},
        ]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:2]):
            mock_entity = MagicMock()
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(
                return_value={"light.existing"}
            )

            # First call returns existing (False), second returns new (True)
            sync_service.entity_repo.upsert = AsyncMock(
                side_effect=[
                    (mock_entity, False),  # Existing entity
                    (mock_entity, True),  # New entity
                ]
            )
            sync_service.entity_repo.get_domain_counts = AsyncMock(
                return_value={"light": 2}
            )

            result = await sync_service.run_discovery()

            assert result.entities_added == 1
            assert result.entities_updated == 1
            assert sync_service.entity_repo.upsert.call_count == 2


class TestRunDiscoveryStaleEntityRemoval:
    """Tests for removal of stale entities."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_removes_stale_entities(
        self, sync_service, mock_mcp_client
    ):
        """Test that entities no longer in HA are removed from DB."""
        mock_mcp_client.list_entities.return_value = []

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=[]):
            # DB has entities that are no longer in HA
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(
                return_value={"light.old_entity", "sensor.old_sensor"}
            )
            sync_service.entity_repo.delete = AsyncMock(return_value=True)
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={})

            result = await sync_service.run_discovery()

            assert result.entities_removed == 2
            assert sync_service.entity_repo.delete.call_count == 2
            sync_service.entity_repo.delete.assert_any_call("light.old_entity")
            sync_service.entity_repo.delete.assert_any_call("sensor.old_sensor")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_no_stale_entities(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test sync when no stale entities exist."""
        mock_mcp_client.list_entities.return_value = [{"entity_id": "light.living_room"}]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:1]):
            mock_entity = MagicMock()
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(
                return_value={"light.living_room"}
            )
            sync_service.entity_repo.upsert = AsyncMock(return_value=(mock_entity, False))
            sync_service.entity_repo.delete = AsyncMock()
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"light": 1})

            result = await sync_service.run_discovery()

            assert result.entities_removed == 0
            sync_service.entity_repo.delete.assert_not_called()


class TestRunDiscoveryErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_mcp_client_failure(
        self, sync_service, mock_mcp_client
    ):
        """Test handling of MCP client failure."""
        mock_mcp_client.list_entities.side_effect = Exception("MCP connection failed")

        with pytest.raises(Exception, match="MCP connection failed"):
            await sync_service.run_discovery()

        # Verify session was marked as failed
        sync_service.session.add.assert_called_once()
        added_session = sync_service.session.add.call_args[0][0]
        assert isinstance(added_session, DiscoverySession)
        assert added_session.status == DiscoveryStatus.FAILED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_repository_failure(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test handling of repository operation failure."""
        mock_mcp_client.list_entities.return_value = [{"entity_id": "light.test"}]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:1]):
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(side_effect=Exception("Database error"))

            with pytest.raises(Exception, match="Database error"):
                await sync_service.run_discovery()


class TestRunDiscoveryAreaInference:
    """Tests for area inference from entity data."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_infers_areas_from_entities(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that areas are inferred from entity area_id attributes."""
        mock_mcp_client.list_entities.return_value = [
            {"entity_id": "light.living_room", "area_id": "living_room"},
            {"entity_id": "light.bedroom", "area_id": "bedroom"},
        ]

        inferred_areas = {
            "living_room": {
                "ha_area_id": "living_room",
                "name": "Living Room",
                "floor_id": None,
                "icon": None,
            },
            "bedroom": {
                "ha_area_id": "bedroom",
                "name": "Bedroom",
                "floor_id": None,
                "icon": None,
            },
        }

        with patch(
            "src.dal.sync.infer_areas_from_entities", return_value=inferred_areas
        ) as mock_infer, patch("src.dal.sync.infer_devices_from_entities", return_value={}), patch(
            "src.dal.sync.parse_entity_list", return_value=sample_entities[:2]
        ):
            mock_area = MagicMock()
            mock_area.id = str(uuid4())
            sync_service.area_repo.upsert = AsyncMock(return_value=(mock_area, True))
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"light": 2})

            result = await sync_service.run_discovery()

            # Verify areas were inferred
            mock_infer.assert_called_once()
            assert result.areas_found == 2
            assert sync_service.area_repo.upsert.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_areas_with_mapping(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that area_id mapping is used for entity area_id."""
        mock_mcp_client.list_entities.return_value = [
            {"entity_id": "light.living_room", "area_id": "living_room"}
        ]

        inferred_areas = {
            "living_room": {
                "ha_area_id": "living_room",
                "name": "Living Room",
            }
        }

        with patch("src.dal.sync.infer_areas_from_entities", return_value=inferred_areas), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:1]):
            mock_area = MagicMock()
            mock_area.id = "internal-area-id-123"
            sync_service.area_repo.upsert = AsyncMock(return_value=(mock_area, True))
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"light": 1})

            await sync_service.run_discovery()

            # Verify entity upsert was called with mapped area_id
            call_args = sync_service.entity_repo.upsert.call_args[0][0]
            assert call_args["area_id"] == "internal-area-id-123"


class TestRunDiscoveryDeviceInference:
    """Tests for device inference from entity data."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_infers_devices_from_entities(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that devices are inferred from entity device_id attributes."""
        mock_mcp_client.list_entities.return_value = [
            {"entity_id": "light.device1_light", "device_id": "device_1"},
            {"entity_id": "sensor.device1_temp", "device_id": "device_1"},
        ]

        inferred_devices = {
            "device_1": {
                "ha_device_id": "device_1",
                "name": "Device 1",
                "area_id": "living_room",
                "manufacturer": None,
                "model": None,
                "sw_version": None,
            }
        }

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value=inferred_devices
        ) as mock_infer, patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:2]):
            mock_device = MagicMock()
            mock_device.id = str(uuid4())
            sync_service.device_repo.upsert = AsyncMock(return_value=(mock_device, True))
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(
                return_value={"light": 1, "sensor": 1}
            )

            result = await sync_service.run_discovery()

            # Verify devices were inferred
            mock_infer.assert_called_once()
            assert result.devices_found == 1
            assert sync_service.device_repo.upsert.call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_devices_with_area_mapping(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that device area_id is mapped using area_id_mapping."""
        mock_mcp_client.list_entities.return_value = [
            {"entity_id": "light.test", "device_id": "device_1", "area_id": "living_room"}
        ]

        inferred_areas = {
            "living_room": {
                "ha_area_id": "living_room",
                "name": "Living Room",
            }
        }
        inferred_devices = {
            "device_1": {
                "ha_device_id": "device_1",
                "name": "Device 1",
                "area_id": "living_room",  # HA area_id
            }
        }

        with patch("src.dal.sync.infer_areas_from_entities", return_value=inferred_areas), patch(
            "src.dal.sync.infer_devices_from_entities", return_value=inferred_devices
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:1]):
            mock_area = MagicMock()
            mock_area.id = "internal-area-id-123"
            sync_service.area_repo.upsert = AsyncMock(return_value=(mock_area, True))

            mock_device = MagicMock()
            mock_device.id = "internal-device-id-456"
            sync_service.device_repo.upsert = AsyncMock(return_value=(mock_device, True))

            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"light": 1})

            await sync_service.run_discovery()

            # Verify device upsert was called with mapped area_id
            device_call_args = sync_service.device_repo.upsert.call_args[0][0]
            assert device_call_args["area_id"] == "internal-area-id-123"


class TestRunDiscoveryAutomationScriptScene:
    """Tests for automation, script, and scene entity sync."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_counts_automations(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that automation entities are counted."""
        mock_mcp_client.list_entities.return_value = [
            {"entity_id": "automation.test1"},
            {"entity_id": "automation.test2"},
        ]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[2:3]):
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(
                return_value={"automation": 2}
            )

            result = await sync_service.run_discovery()

            assert result.automations_found == 1  # Only one in sample_entities[2:3]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_counts_scripts(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that script entities are counted."""
        mock_mcp_client.list_entities.return_value = [{"entity_id": "script.test"}]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[3:4]):
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"script": 1})

            result = await sync_service.run_discovery()

            assert result.scripts_found == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_counts_scenes(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that scene entities are counted."""
        mock_mcp_client.list_entities.return_value = [{"entity_id": "scene.test"}]

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[4:5]):
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={"scene": 1})

            result = await sync_service.run_discovery()

            assert result.scenes_found == 1


class TestRunDiscoveryStatistics:
    """Tests for sync statistics tracking."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_tracks_all_statistics(
        self, sync_service, mock_mcp_client, sample_entities
    ):
        """Test that all statistics are tracked correctly."""
        mock_mcp_client.list_entities.return_value = [
            {"entity_id": "light.new"},
            {"entity_id": "light.existing"},
        ]

        inferred_areas = {
            "living_room": {"ha_area_id": "living_room", "name": "Living Room"}
        }
        inferred_devices = {
            "device_1": {"ha_device_id": "device_1", "name": "Device 1"}
        }

        with patch("src.dal.sync.infer_areas_from_entities", return_value=inferred_areas), patch(
            "src.dal.sync.infer_devices_from_entities", return_value=inferred_devices
        ), patch("src.dal.sync.parse_entity_list", return_value=sample_entities[:2]):
            mock_area = MagicMock()
            mock_area.id = str(uuid4())
            sync_service.area_repo.upsert = AsyncMock(return_value=(mock_area, True))

            mock_device = MagicMock()
            mock_device.id = str(uuid4())
            sync_service.device_repo.upsert = AsyncMock(return_value=(mock_device, True))

            sync_service.entity_repo.get_all_entity_ids = AsyncMock(
                return_value={"light.living_room"}
            )
            sync_service.entity_repo.upsert = AsyncMock(
                side_effect=[
                    (MagicMock(), False),  # Existing (living_room)
                    (MagicMock(), True),  # New (sensor)
                ]
            )
            sync_service.entity_repo.get_domain_counts = AsyncMock(
                return_value={"light": 2, "sensor": 1}
            )

            result = await sync_service.run_discovery()

            # Verify all statistics
            assert result.entities_found == 2
            assert result.entities_added == 1
            assert result.entities_updated == 1
            assert result.entities_removed == 0
            assert result.areas_found == 1
            assert result.areas_added == 1
            assert result.devices_found == 1
            assert result.devices_added == 1
            assert result.domain_counts == {"light": 2, "sensor": 1}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_records_mcp_gaps(
        self, sync_service, mock_mcp_client
    ):
        """Test that MCP gaps are recorded in discovery session."""
        mock_mcp_client.list_entities.return_value = []

        with patch("src.dal.sync.infer_areas_from_entities", return_value={}), patch(
            "src.dal.sync.infer_devices_from_entities", return_value={}
        ), patch("src.dal.sync.parse_entity_list", return_value=[]):
            sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
            sync_service.entity_repo.get_domain_counts = AsyncMock(return_value={})

            result = await sync_service.run_discovery()

            assert result.mcp_gaps_encountered is not None
            assert result.mcp_gaps_encountered["floors_not_available"] is True
            assert result.mcp_gaps_encountered["labels_not_available"] is True
            assert result.mcp_gaps_encountered["device_details_not_available"] is True


class TestRunDiscoveryConvenienceFunction:
    """Tests for the convenience run_discovery function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_convenience_function_with_client(
        self, mock_session, mock_mcp_client
    ):
        """Test convenience function with provided MCP client."""
        with patch("src.dal.sync.DiscoverySyncService") as mock_service_class:
            mock_service = MagicMock()
            mock_discovery = MagicMock()
            mock_service.run_discovery = AsyncMock(return_value=mock_discovery)
            mock_service_class.return_value = mock_service

            result = await run_discovery(mock_session, mock_mcp_client, triggered_by="test")

            assert result == mock_discovery
            mock_service_class.assert_called_once_with(mock_session, mock_mcp_client)
            mock_service.run_discovery.assert_called_once_with(triggered_by="test")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_discovery_convenience_function_without_client(
        self, mock_session
    ):
        """Test convenience function creates MCP client if not provided."""
        mock_mcp_client = MagicMock()
        with patch("src.mcp.get_mcp_client", return_value=mock_mcp_client), patch(
            "src.dal.sync.DiscoverySyncService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_discovery = MagicMock()
            mock_service.run_discovery = AsyncMock(return_value=mock_discovery)
            mock_service_class.return_value = mock_service

            result = await run_discovery(mock_session, triggered_by="test")

            assert result == mock_discovery
            mock_service_class.assert_called_once_with(mock_session, mock_mcp_client)


class TestSyncAreas:
    """Tests for _sync_areas private method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_areas_creates_mapping(self, sync_service):
        """Test that _sync_areas returns correct mapping."""
        inferred_areas = {
            "living_room": {
                "ha_area_id": "living_room",
                "name": "Living Room",
                "floor_id": None,
                "icon": "mdi:sofa",
            },
            "bedroom": {
                "ha_area_id": "bedroom",
                "name": "Bedroom",
                "floor_id": None,
                "icon": None,
            },
        }

        mock_area1 = MagicMock()
        mock_area1.id = "id-1"
        mock_area2 = MagicMock()
        mock_area2.id = "id-2"

        sync_service.area_repo.upsert = AsyncMock(
            side_effect=[
                (mock_area1, True),
                (mock_area2, True),
            ]
        )

        mapping = await sync_service._sync_areas(inferred_areas)

        assert mapping == {"living_room": "id-1", "bedroom": "id-2"}
        assert sync_service.area_repo.upsert.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetch_areas_uses_ha_registry_api(self, sync_service):
        """Test that _fetch_areas tries the direct HA REST API first."""
        sync_service.mcp.get_area_registry = AsyncMock(return_value=[
            {
                "area_id": "living_room",
                "name": "Living Room",
                "floor_id": "ground_floor",
                "icon": "mdi:sofa",
                "picture": None,
            },
        ])

        areas = await sync_service._fetch_areas([])

        # Should use HA REST API data, not inferred from entities
        assert len(areas) == 1
        assert areas["living_room"]["name"] == "Living Room"
        assert areas["living_room"]["floor_id"] == "ground_floor"
        assert areas["living_room"]["icon"] == "mdi:sofa"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetch_areas_falls_back_to_inference(self, sync_service):
        """Test that _fetch_areas falls back to entity inference when HA API fails."""
        sync_service.mcp.get_area_registry = AsyncMock(return_value=[])

        # Pass entities with area_id attributes
        from src.mcp.workarounds import ParsedEntity

        entities = [
            ParsedEntity(
                entity_id="light.living_room",
                name="Living Room Light",
                state="on",
                domain="light",
                area_id="living_room",
                attributes={},
            ),
        ]

        areas = await sync_service._fetch_areas(entities)

        assert "living_room" in areas
        assert areas["living_room"]["name"] == "Living Room"


class TestSyncDevices:
    """Tests for _sync_devices private method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_devices_creates_mapping(self, sync_service):
        """Test that _sync_devices returns correct mapping."""
        inferred_devices = {
            "device_1": {
                "ha_device_id": "device_1",
                "name": "Device 1",
                "area_id": "living_room",
                "manufacturer": "Test Corp",
                "model": "Model X",
                "sw_version": "1.0.0",
            }
        }
        area_id_mapping = {"living_room": "internal-area-id"}

        mock_device = MagicMock()
        mock_device.id = "device-internal-id"

        sync_service.device_repo.upsert = AsyncMock(return_value=(mock_device, True))

        mapping = await sync_service._sync_devices(inferred_devices, area_id_mapping)

        assert mapping == {"device_1": "device-internal-id"}
        assert sync_service.device_repo.upsert.call_count == 1

        # Verify area_id was mapped
        call_args = sync_service.device_repo.upsert.call_args[0][0]
        assert call_args["area_id"] == "internal-area-id"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_devices_without_area(self, sync_service):
        """Test device sync when device has no area."""
        inferred_devices = {
            "device_1": {
                "ha_device_id": "device_1",
                "name": "Device 1",
                "area_id": None,
            }
        }

        mock_device = MagicMock()
        mock_device.id = "device-internal-id"
        sync_service.device_repo.upsert = AsyncMock(return_value=(mock_device, True))

        mapping = await sync_service._sync_devices(inferred_devices, {})

        call_args = sync_service.device_repo.upsert.call_args[0][0]
        assert call_args["area_id"] is None


class TestSyncEntities:
    """Tests for _sync_entities private method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_entities_returns_stats(self, sync_service, sample_entities):
        """Test that _sync_entities returns correct statistics."""
        area_id_mapping = {"living_room": "internal-area-id"}
        device_id_mapping = {"device_1": "internal-device-id"}

        sync_service.entity_repo.get_all_entity_ids = AsyncMock(
            return_value={"light.existing"}
        )
        sync_service.entity_repo.upsert = AsyncMock(
            side_effect=[
                (MagicMock(), True),  # New entity
                (MagicMock(), False),  # Updated entity
            ]
        )
        sync_service.entity_repo.delete = AsyncMock(return_value=True)

        stats = await sync_service._sync_entities(
            sample_entities[:2], area_id_mapping, device_id_mapping
        )

        assert stats["added"] == 1
        assert stats["updated"] == 1
        assert stats["removed"] == 1  # light.existing was removed
        assert sync_service.entity_repo.upsert.call_count == 2
        sync_service.entity_repo.delete.assert_called_once_with("light.existing")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_entities_maps_foreign_keys(self, sync_service, sample_entities):
        """Test that entity foreign keys are mapped correctly."""
        area_id_mapping = {"living_room": "internal-area-id"}
        device_id_mapping = {"device_1": "internal-device-id"}

        sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
        sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))

        await sync_service._sync_entities(
            sample_entities[:1], area_id_mapping, device_id_mapping
        )

        call_args = sync_service.entity_repo.upsert.call_args[0][0]
        assert call_args["area_id"] == "internal-area-id"
        assert call_args["device_id"] == "internal-device-id"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_entities_with_missing_foreign_keys(
        self, sync_service, sample_entities
    ):
        """Test entity sync when area_id or device_id are missing."""
        from src.mcp.parsers import ParsedEntity

        entity_no_fks = ParsedEntity(
            entity_id="light.standalone",
            domain="light",
            name="Standalone Light",
            state="off",
            attributes={},
            area_id=None,
            device_id=None,
            device_class=None,
            unit_of_measurement=None,
            supported_features=0,
        )

        sync_service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
        sync_service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))

        await sync_service._sync_entities([entity_no_fks], {}, {})

        call_args = sync_service.entity_repo.upsert.call_args[0][0]
        assert call_args["area_id"] is None
        assert call_args["device_id"] is None


class TestSyncAutomationEntities:
    """Tests for _sync_automation_entities populating ha_automations, scripts, scenes."""

    @pytest.fixture
    def registry_entities(self):
        """Create sample entities with realistic attributes for registry sync."""
        from src.mcp.parsers import ParsedEntity

        return [
            ParsedEntity(
                entity_id="automation.morning_routine",
                domain="automation",
                name="Morning Routine",
                state="on",
                attributes={
                    "id": "morning_routine",
                    "friendly_name": "Morning Routine",
                    "last_triggered": "2026-02-07T08:00:00+00:00",
                    "mode": "single",
                },
                area_id=None,
                device_id=None,
                device_class=None,
                unit_of_measurement=None,
                supported_features=0,
            ),
            ParsedEntity(
                entity_id="automation.night_mode",
                domain="automation",
                name="Night Mode",
                state="off",
                attributes={
                    "id": "night_mode",
                    "friendly_name": "Night Mode",
                    "last_triggered": None,
                    "mode": "restart",
                },
                area_id=None,
                device_id=None,
                device_class=None,
                unit_of_measurement=None,
                supported_features=0,
            ),
            ParsedEntity(
                entity_id="script.turn_on_lights",
                domain="script",
                name="Turn On Lights",
                state="off",
                attributes={
                    "friendly_name": "Turn On Lights",
                    "last_triggered": "2026-02-06T18:30:00+00:00",
                    "mode": "single",
                    "icon": "mdi:lightbulb",
                },
                area_id=None,
                device_id=None,
                device_class=None,
                unit_of_measurement=None,
                supported_features=0,
            ),
            ParsedEntity(
                entity_id="scene.evening",
                domain="scene",
                name="Evening Scene",
                state="scening",
                attributes={
                    "friendly_name": "Evening Scene",
                    "icon": "mdi:weather-night",
                },
                area_id=None,
                device_id=None,
                device_class=None,
                unit_of_measurement=None,
                supported_features=0,
            ),
            # Non-registry entity (should be ignored)
            ParsedEntity(
                entity_id="light.living_room",
                domain="light",
                name="Living Room Light",
                state="off",
                attributes={},
                area_id=None,
                device_id=None,
                device_class=None,
                unit_of_measurement=None,
                supported_features=0,
            ),
        ]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upserts_automations(self, sync_service, registry_entities):
        """Test that automation entities are upserted into ha_automations table."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        stats = await sync_service._sync_automation_entities(registry_entities)

        assert sync_service.automation_repo.upsert.call_count == 2
        # Check first automation upsert data
        first_call = sync_service.automation_repo.upsert.call_args_list[0][0][0]
        assert first_call["ha_automation_id"] == "morning_routine"
        assert first_call["entity_id"] == "automation.morning_routine"
        assert first_call["alias"] == "Morning Routine"
        assert first_call["state"] == "on"
        assert first_call["mode"] == "single"
        assert first_call["last_triggered"] == "2026-02-07T08:00:00+00:00"
        assert stats["automations_synced"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upserts_scripts(self, sync_service, registry_entities):
        """Test that script entities are upserted into scripts table."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        stats = await sync_service._sync_automation_entities(registry_entities)

        assert sync_service.script_repo.upsert.call_count == 1
        script_call = sync_service.script_repo.upsert.call_args_list[0][0][0]
        assert script_call["entity_id"] == "script.turn_on_lights"
        assert script_call["alias"] == "Turn On Lights"
        assert script_call["state"] == "off"
        assert script_call["mode"] == "single"
        assert script_call["icon"] == "mdi:lightbulb"
        assert script_call["last_triggered"] == "2026-02-06T18:30:00+00:00"
        assert stats["scripts_synced"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upserts_scenes(self, sync_service, registry_entities):
        """Test that scene entities are upserted into scenes table."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        stats = await sync_service._sync_automation_entities(registry_entities)

        assert sync_service.scene_repo.upsert.call_count == 1
        scene_call = sync_service.scene_repo.upsert.call_args_list[0][0][0]
        assert scene_call["entity_id"] == "scene.evening"
        assert scene_call["name"] == "Evening Scene"
        assert scene_call["icon"] == "mdi:weather-night"
        assert stats["scenes_synced"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_removes_stale_automations(self, sync_service, registry_entities):
        """Test that automations no longer in HA are removed."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        # DB has an extra automation that's no longer in HA
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(
            return_value={"morning_routine", "night_mode", "deleted_one"}
        )
        sync_service.automation_repo.delete = AsyncMock(return_value=True)
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        sync_service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        await sync_service._sync_automation_entities(registry_entities)

        sync_service.automation_repo.delete.assert_called_once_with("deleted_one")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_removes_stale_scripts(self, sync_service, registry_entities):
        """Test that scripts no longer in HA are removed."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        sync_service.script_repo.get_all_ha_ids = AsyncMock(
            return_value={"script.turn_on_lights", "script.old_one"}
        )
        sync_service.script_repo.delete = AsyncMock(return_value=True)
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        await sync_service._sync_automation_entities(registry_entities)

        sync_service.script_repo.delete.assert_called_once_with("script.old_one")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_removes_stale_scenes(self, sync_service, registry_entities):
        """Test that scenes no longer in HA are removed."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        sync_service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(
            return_value={"scene.evening", "scene.deleted"}
        )
        sync_service.scene_repo.delete = AsyncMock(return_value=True)

        await sync_service._sync_automation_entities(registry_entities)

        sync_service.scene_repo.delete.assert_called_once_with("scene.deleted")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_entities_returns_zero_stats(self, sync_service):
        """Test that empty entity list returns zero stats without error."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        stats = await sync_service._sync_automation_entities([])

        assert stats["automations_synced"] == 0
        assert stats["scripts_synced"] == 0
        assert stats["scenes_synced"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ignores_non_registry_domains(self, sync_service, registry_entities):
        """Test that non-registry entities (lights, sensors) are ignored."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        stats = await sync_service._sync_automation_entities(registry_entities)

        # 5 entities total but only 4 are registry (2 auto + 1 script + 1 scene)
        total = stats["automations_synced"] + stats["scripts_synced"] + stats["scenes_synced"]
        assert total == 4

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_stats_dict(self, sync_service, registry_entities):
        """Test that return value has expected keys."""
        sync_service.automation_repo = MagicMock()
        sync_service.automation_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.script_repo = MagicMock()
        sync_service.script_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        sync_service.scene_repo = MagicMock()
        sync_service.scene_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        sync_service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        stats = await sync_service._sync_automation_entities(registry_entities)

        assert "automations_synced" in stats
        assert "scripts_synced" in stats
        assert "scenes_synced" in stats


class TestRunRegistrySync:
    """Tests for the standalone run_registry_sync convenience function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetches_entities_and_syncs_registry(self):
        """Test that run_registry_sync fetches entities and delegates to sync."""
        from src.dal.sync import run_registry_sync

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value=[
            {"entity_id": "automation.test", "state": "on", "name": "Test"},
            {"entity_id": "script.test", "state": "off", "name": "Test Script"},
        ])

        with patch("src.dal.sync.parse_entity_list") as mock_parse, \
             patch.object(DiscoverySyncService, "_sync_automation_entities", new_callable=AsyncMock) as mock_sync:
            mock_parse.return_value = [MagicMock(domain="automation"), MagicMock(domain="script")]
            mock_sync.return_value = {
                "automations_synced": 1,
                "scripts_synced": 1,
                "scenes_synced": 0,
            }

            result = await run_registry_sync(session=mock_session, mcp_client=mock_mcp)

        assert result["automations_synced"] == 1
        assert result["scripts_synced"] == 1
        assert result["scenes_synced"] == 0
        assert "duration_seconds" in result
        mock_mcp.list_entities.assert_called_once_with(detailed=True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_mcp_client_if_none(self):
        """Test that run_registry_sync creates MCP client when not provided."""
        from src.dal.sync import run_registry_sync

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value=[])

        with patch("src.mcp.get_mcp_client", return_value=mock_mcp) as mock_get_mcp, \
             patch("src.dal.sync.parse_entity_list", return_value=[]), \
             patch.object(DiscoverySyncService, "_sync_automation_entities", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                "automations_synced": 0,
                "scripts_synced": 0,
                "scenes_synced": 0,
            }

            await run_registry_sync(session=mock_session)

        mock_get_mcp.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_propagates_mcp_errors(self):
        """Test that MCP errors propagate to caller."""
        from src.dal.sync import run_registry_sync

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(side_effect=Exception("MCP connection failed"))

        with pytest.raises(Exception, match="MCP connection failed"):
            await run_registry_sync(session=mock_session, mcp_client=mock_mcp)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_duration_is_positive(self):
        """Test that duration_seconds is a positive number."""
        from src.dal.sync import run_registry_sync

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value=[])

        with patch("src.dal.sync.parse_entity_list", return_value=[]), \
             patch.object(DiscoverySyncService, "_sync_automation_entities", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                "automations_synced": 0,
                "scripts_synced": 0,
                "scenes_synced": 0,
            }

            result = await run_registry_sync(session=mock_session, mcp_client=mock_mcp)

        assert result["duration_seconds"] >= 0
