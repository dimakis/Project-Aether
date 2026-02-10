"""Unit tests for HARegistryCache.

T220: HARegistryCache with TTL, entity/service/area/device caching.
Feature 27: YAML Semantic Validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_ha_client() -> MagicMock:
    """Mock HA client with entity/service/area responses."""
    client = MagicMock()

    client.list_entities = AsyncMock(
        return_value=[
            {"entity_id": "light.living_room", "state": "on", "attributes": {}},
            {"entity_id": "light.bedroom", "state": "off", "attributes": {}},
            {"entity_id": "switch.fan", "state": "on", "attributes": {}},
            {"entity_id": "sensor.temperature", "state": "22.5", "attributes": {}},
        ]
    )

    client.list_services = AsyncMock(
        return_value=[
            {
                "domain": "light",
                "services": {
                    "turn_on": {
                        "description": "Turn on light",
                        "fields": {
                            "brightness": {"description": "Brightness", "selector": {"number": {}}},
                            "color_temp": {"description": "Color temp"},
                        },
                    },
                    "turn_off": {"description": "Turn off light", "fields": {}},
                    "toggle": {"description": "Toggle light", "fields": {}},
                },
            },
            {
                "domain": "switch",
                "services": {
                    "turn_on": {"description": "Turn on switch", "fields": {}},
                    "turn_off": {"description": "Turn off switch", "fields": {}},
                },
            },
            {
                "domain": "homeassistant",
                "services": {
                    "restart": {"description": "Restart HA", "fields": {}},
                },
            },
        ]
    )

    client.get_area_registry = AsyncMock(
        return_value=[
            {"area_id": "living_room", "name": "Living Room"},
            {"area_id": "bedroom", "name": "Bedroom"},
            {"area_id": "kitchen", "name": "Kitchen"},
        ]
    )

    return client


class TestHARegistryCacheInit:
    """Test cache initialization."""

    def test_create_cache(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client, ttl_seconds=300)
        assert cache._ttl_seconds == 300

    def test_default_ttl(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        assert cache._ttl_seconds == 600  # 10 min default


class TestEntityLookup:
    """Test entity existence checks."""

    @pytest.mark.asyncio
    async def test_entity_exists(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        assert await cache.entity_exists("light.living_room") is True
        assert await cache.entity_exists("light.bedroom") is True

    @pytest.mark.asyncio
    async def test_entity_not_exists(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        assert await cache.entity_exists("light.nonexistent") is False

    @pytest.mark.asyncio
    async def test_get_entity_ids(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        ids = await cache.get_entity_ids()
        assert "light.living_room" in ids
        assert "switch.fan" in ids
        assert len(ids) == 4

    @pytest.mark.asyncio
    async def test_get_entity_ids_by_domain(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        light_ids = await cache.get_entity_ids(domain="light")
        assert light_ids == {"light.living_room", "light.bedroom"}


class TestServiceLookup:
    """Test service validation checks."""

    @pytest.mark.asyncio
    async def test_service_exists(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        assert await cache.service_exists("light.turn_on") is True
        assert await cache.service_exists("switch.turn_off") is True

    @pytest.mark.asyncio
    async def test_service_not_exists(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        assert await cache.service_exists("light.nonexistent") is False
        assert await cache.service_exists("fake.service") is False

    @pytest.mark.asyncio
    async def test_get_service_fields(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        fields = await cache.get_service_fields("light.turn_on")
        assert fields is not None
        assert "brightness" in fields

    @pytest.mark.asyncio
    async def test_get_service_fields_unknown(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        fields = await cache.get_service_fields("light.nonexistent")
        assert fields is None

    @pytest.mark.asyncio
    async def test_get_domains(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        domains = await cache.get_service_domains()
        assert "light" in domains
        assert "switch" in domains
        assert "homeassistant" in domains


class TestAreaLookup:
    """Test area existence checks."""

    @pytest.mark.asyncio
    async def test_area_exists(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        assert await cache.area_exists("living_room") is True
        assert await cache.area_exists("bedroom") is True

    @pytest.mark.asyncio
    async def test_area_not_exists(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)
        assert await cache.area_exists("nonexistent_room") is False


class TestCacheTTL:
    """Test cache TTL and refresh behaviour."""

    @pytest.mark.asyncio
    async def test_caches_entities(self, mock_ha_client: MagicMock) -> None:
        """Second call uses cached data — no extra HA calls."""
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)

        await cache.entity_exists("light.living_room")
        await cache.entity_exists("light.bedroom")

        # list_entities should be called only once
        assert mock_ha_client.list_entities.call_count == 1

    @pytest.mark.asyncio
    async def test_caches_services(self, mock_ha_client: MagicMock) -> None:
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)

        await cache.service_exists("light.turn_on")
        await cache.service_exists("switch.turn_off")

        assert mock_ha_client.list_services.call_count == 1

    @pytest.mark.asyncio
    async def test_invalidate_clears_cache(self, mock_ha_client: MagicMock) -> None:
        """invalidate() forces re-fetch on next access."""
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client)

        await cache.entity_exists("light.living_room")
        assert mock_ha_client.list_entities.call_count == 1

        cache.invalidate()

        await cache.entity_exists("light.living_room")
        assert mock_ha_client.list_entities.call_count == 2

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, mock_ha_client: MagicMock) -> None:
        """Expired TTL forces re-fetch."""
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=mock_ha_client, ttl_seconds=0)

        await cache.entity_exists("light.living_room")
        # TTL=0 means always expired
        await cache.entity_exists("light.living_room")

        assert mock_ha_client.list_entities.call_count == 2
