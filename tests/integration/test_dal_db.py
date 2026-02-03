"""Integration tests for DAL against real PostgreSQL.

Uses testcontainers to spin up a real PostgreSQL instance.
Constitution: Reliability & Quality - test with real database.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.dal.areas import AreaRepository
from src.dal.devices import DeviceRepository
from src.dal.entities import EntityRepository


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
class TestEntityRepositoryDB:
    """Integration tests for EntityRepository with real PostgreSQL."""

    async def test_create_entity(self, integration_session: AsyncSession):
        """Test creating an entity in real database."""
        repo = EntityRepository(integration_session)

        entity = await repo.create({
            "entity_id": "light.test_light",
            "domain": "light",
            "name": "Test Light",
            "state": "off",
            "attributes": {"brightness": 0},
        })

        assert entity.id is not None
        assert entity.entity_id == "light.test_light"
        assert entity.domain == "light"
        assert entity.state == "off"

    async def test_get_entity_by_id(self, integration_session: AsyncSession):
        """Test retrieving entity by ID."""
        repo = EntityRepository(integration_session)

        # Create entity
        created = await repo.create({
            "entity_id": "sensor.temperature",
            "domain": "sensor",
            "name": "Temperature Sensor",
            "state": "22.5",
            "attributes": {"unit_of_measurement": "°C"},
        })

        # Retrieve by ID
        found = await repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.entity_id == "sensor.temperature"

    async def test_get_entity_by_entity_id(self, integration_session: AsyncSession):
        """Test retrieving entity by HA entity_id."""
        repo = EntityRepository(integration_session)

        await repo.create({
            "entity_id": "switch.kitchen",
            "domain": "switch",
            "name": "Kitchen Switch",
            "state": "on",
        })

        found = await repo.get_by_entity_id("switch.kitchen")

        assert found is not None
        assert found.name == "Kitchen Switch"
        assert found.state == "on"

    async def test_list_entities_with_domain_filter(self, integration_session: AsyncSession):
        """Test listing entities filtered by domain."""
        repo = EntityRepository(integration_session)

        # Create entities in different domains
        await repo.create({"entity_id": "light.one", "domain": "light", "name": "Light 1", "state": "off"})
        await repo.create({"entity_id": "light.two", "domain": "light", "name": "Light 2", "state": "on"})
        await repo.create({"entity_id": "switch.one", "domain": "switch", "name": "Switch 1", "state": "off"})

        # List only lights
        lights = await repo.list_all(domain="light")

        assert len(lights) == 2
        assert all(e.domain == "light" for e in lights)

    async def test_upsert_creates_new_entity(self, integration_session: AsyncSession):
        """Test upsert creates entity when it doesn't exist."""
        repo = EntityRepository(integration_session)

        entity, created = await repo.upsert({
            "entity_id": "binary_sensor.door",
            "domain": "binary_sensor",
            "name": "Front Door",
            "state": "closed",
        })

        assert created is True
        assert entity.entity_id == "binary_sensor.door"

    async def test_upsert_updates_existing_entity(self, integration_session: AsyncSession):
        """Test upsert updates entity when it exists."""
        repo = EntityRepository(integration_session)

        # Create initial
        await repo.create({
            "entity_id": "light.upsert_test",
            "domain": "light",
            "name": "Test",
            "state": "off",
        })

        # Upsert with new state
        entity, created = await repo.upsert({
            "entity_id": "light.upsert_test",
            "domain": "light",
            "name": "Updated Name",
            "state": "on",
        })

        assert created is False
        assert entity.name == "Updated Name"
        assert entity.state == "on"

    async def test_delete_entity(self, integration_session: AsyncSession):
        """Test deleting an entity."""
        repo = EntityRepository(integration_session)

        # Create entity
        await repo.create({
            "entity_id": "light.to_delete",
            "domain": "light",
            "name": "Delete Me",
            "state": "off",
        })

        # Verify it exists
        found = await repo.get_by_entity_id("light.to_delete")
        assert found is not None

        # Delete
        deleted = await repo.delete("light.to_delete")
        assert deleted is True

        # Verify it's gone
        found = await repo.get_by_entity_id("light.to_delete")
        assert found is None

    async def test_count_entities(self, integration_session: AsyncSession):
        """Test counting entities."""
        repo = EntityRepository(integration_session)

        # Create several entities
        for i in range(5):
            await repo.create({
                "entity_id": f"sensor.count_test_{i}",
                "domain": "sensor",
                "name": f"Sensor {i}",
                "state": str(i),
            })

        count = await repo.count(domain="sensor")
        assert count == 5

    async def test_get_domain_counts(self, integration_session: AsyncSession):
        """Test getting entity counts per domain."""
        repo = EntityRepository(integration_session)

        # Create entities in different domains
        await repo.create({"entity_id": "light.a", "domain": "light", "name": "L", "state": "off"})
        await repo.create({"entity_id": "light.b", "domain": "light", "name": "L", "state": "off"})
        await repo.create({"entity_id": "sensor.a", "domain": "sensor", "name": "S", "state": "0"})
        await repo.create({"entity_id": "switch.a", "domain": "switch", "name": "W", "state": "off"})

        counts = await repo.get_domain_counts()

        assert counts["light"] == 2
        assert counts["sensor"] == 1
        assert counts["switch"] == 1

    async def test_get_all_entity_ids(self, integration_session: AsyncSession):
        """Test getting all entity IDs."""
        repo = EntityRepository(integration_session)

        await repo.create({"entity_id": "light.first", "domain": "light", "name": "F", "state": "off"})
        await repo.create({"entity_id": "light.second", "domain": "light", "name": "S", "state": "on"})

        ids = await repo.get_all_entity_ids()

        assert "light.first" in ids
        assert "light.second" in ids


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
class TestAreaRepositoryDB:
    """Integration tests for AreaRepository with real PostgreSQL."""

    async def test_create_area(self, integration_session: AsyncSession):
        """Test creating an area."""
        repo = AreaRepository(integration_session)

        area = await repo.create({
            "ha_area_id": "living_room",
            "name": "Living Room",
        })

        assert area.id is not None
        assert area.ha_area_id == "living_room"
        assert area.name == "Living Room"

    async def test_get_by_ha_area_id(self, integration_session: AsyncSession):
        """Test finding area by HA area ID."""
        repo = AreaRepository(integration_session)

        await repo.create({
            "ha_area_id": "kitchen",
            "name": "Kitchen",
        })

        found = await repo.get_by_ha_area_id("kitchen")

        assert found is not None
        assert found.name == "Kitchen"

    async def test_upsert_area(self, integration_session: AsyncSession):
        """Test upsert for areas."""
        repo = AreaRepository(integration_session)

        # Create via upsert
        area1, created1 = await repo.upsert({
            "ha_area_id": "bedroom",
            "name": "Bedroom",
        })
        assert created1 is True

        # Update via upsert
        area2, created2 = await repo.upsert({
            "ha_area_id": "bedroom",
            "name": "Master Bedroom",
        })
        assert created2 is False
        assert area2.name == "Master Bedroom"

    async def test_list_areas(self, integration_session: AsyncSession):
        """Test listing all areas."""
        repo = AreaRepository(integration_session)

        await repo.create({"ha_area_id": "room1", "name": "Room 1"})
        await repo.create({"ha_area_id": "room2", "name": "Room 2"})
        await repo.create({"ha_area_id": "room3", "name": "Room 3"})

        areas = await repo.list_all()

        assert len(areas) == 3


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
class TestDeviceRepositoryDB:
    """Integration tests for DeviceRepository with real PostgreSQL."""

    async def test_create_device(self, integration_session: AsyncSession):
        """Test creating a device."""
        repo = DeviceRepository(integration_session)

        device = await repo.create({
            "ha_device_id": "device_001",
            "name": "Philips Hue",
            "manufacturer": "Philips",
            "model": "Hue Bridge",
        })

        assert device.id is not None
        assert device.ha_device_id == "device_001"
        assert device.manufacturer == "Philips"

    async def test_get_by_ha_device_id(self, integration_session: AsyncSession):
        """Test finding device by HA device ID."""
        repo = DeviceRepository(integration_session)

        await repo.create({
            "ha_device_id": "device_unique",
            "name": "Test Device",
        })

        found = await repo.get_by_ha_device_id("device_unique")

        assert found is not None
        assert found.name == "Test Device"

    async def test_device_with_area(self, integration_session: AsyncSession):
        """Test creating device associated with an area."""
        area_repo = AreaRepository(integration_session)
        device_repo = DeviceRepository(integration_session)

        # Create area first
        area = await area_repo.create({
            "ha_area_id": "garage",
            "name": "Garage",
        })

        # Create device in that area
        device = await device_repo.create({
            "ha_device_id": "garage_opener",
            "name": "Garage Door Opener",
            "area_id": area.id,
        })

        assert device.area_id == area.id


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
class TestCrossRepositoryOperations:
    """Integration tests for operations across multiple repositories."""

    async def test_entity_with_area_and_device(self, integration_session: AsyncSession):
        """Test creating entity with both area and device relationships."""
        area_repo = AreaRepository(integration_session)
        device_repo = DeviceRepository(integration_session)
        entity_repo = EntityRepository(integration_session)

        # Create area
        area = await area_repo.create({
            "ha_area_id": "office",
            "name": "Office",
        })

        # Create device
        device = await device_repo.create({
            "ha_device_id": "smart_bulb",
            "name": "Smart Bulb",
            "area_id": area.id,
        })

        # Create entity associated with both
        entity = await entity_repo.create({
            "entity_id": "light.office_smart_bulb",
            "domain": "light",
            "name": "Office Smart Bulb",
            "state": "off",
            "area_id": area.id,
            "device_id": device.id,
        })

        assert entity.area_id == area.id
        assert entity.device_id == device.id

    async def test_multiple_entities_same_device(self, integration_session: AsyncSession):
        """Test multiple entities belonging to the same device."""
        device_repo = DeviceRepository(integration_session)
        entity_repo = EntityRepository(integration_session)

        # Create device
        device = await device_repo.create({
            "ha_device_id": "multi_sensor",
            "name": "Multi Sensor",
        })

        # Create multiple entities for same device
        await entity_repo.create({
            "entity_id": "sensor.temp",
            "domain": "sensor",
            "name": "Temperature",
            "state": "22",
            "device_id": device.id,
        })
        await entity_repo.create({
            "entity_id": "sensor.humidity",
            "domain": "sensor",
            "name": "Humidity",
            "state": "45",
            "device_id": device.id,
        })
        await entity_repo.create({
            "entity_id": "binary_sensor.motion",
            "domain": "binary_sensor",
            "name": "Motion",
            "state": "off",
            "device_id": device.id,
        })

        # List entities for this device
        all_entities = await entity_repo.list_all()
        device_entities = [e for e in all_entities if e.device_id == device.id]

        assert len(device_entities) == 3
