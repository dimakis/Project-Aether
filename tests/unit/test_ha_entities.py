"""Unit tests for HA entities module.

Tests EntityMixin methods with mocked _request.
"""

from unittest.mock import AsyncMock

import pytest

from src.ha.base import HAClientError
from src.ha.entities import EntityMixin


class MockHAClient(EntityMixin):
    """Mock HA client that inherits EntityMixin for testing."""

    def __init__(self):
        self._request = AsyncMock()


@pytest.fixture
def ha_client():
    """Create a mock HA client."""
    return MockHAClient()


class TestFetchEntityRegistry:
    """Tests for _fetch_entity_registry."""

    @pytest.mark.asyncio
    async def test_fetch_entity_registry_success(self, ha_client):
        """Test successful entity registry fetch."""
        registry_data = [
            {
                "entity_id": "light.living_room",
                "area_id": "living_room",
                "device_id": "device_123",
                "icon": "mdi:lightbulb",
            },
            {
                "entity_id": "sensor.temperature",
                "area_id": "bedroom",
                "device_id": "device_456",
            },
        ]
        ha_client._request.return_value = registry_data

        result = await ha_client._fetch_entity_registry()

        assert len(result) == 2
        assert "light.living_room" in result
        assert result["light.living_room"]["area_id"] == "living_room"
        assert result["sensor.temperature"]["device_id"] == "device_456"
        ha_client._request.assert_called_once_with("GET", "/api/config/entity_registry")

    @pytest.mark.asyncio
    async def test_fetch_entity_registry_empty(self, ha_client):
        """Test empty registry response."""
        ha_client._request.return_value = []

        result = await ha_client._fetch_entity_registry()

        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_entity_registry_invalid_format(self, ha_client):
        """Test invalid registry format."""
        ha_client._request.return_value = None

        result = await ha_client._fetch_entity_registry()

        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_entity_registry_exception(self, ha_client):
        """Test exception handling."""
        ha_client._request.side_effect = Exception("Network error")

        result = await ha_client._fetch_entity_registry()

        assert result == {}


class TestGetAreaRegistry:
    """Tests for get_area_registry."""

    @pytest.mark.asyncio
    async def test_get_area_registry_success(self, ha_client):
        """Test successful area registry fetch."""
        area_data = [
            {"area_id": "living_room", "name": "Living Room", "floor_id": "floor_1"},
            {"area_id": "bedroom", "name": "Bedroom"},
        ]
        ha_client._request.return_value = area_data

        result = await ha_client.get_area_registry()

        assert len(result) == 2
        assert result[0]["area_id"] == "living_room"
        ha_client._request.assert_called_once_with("GET", "/api/config/area_registry/list")

    @pytest.mark.asyncio
    async def test_get_area_registry_empty(self, ha_client):
        """Test empty area registry."""
        ha_client._request.return_value = []

        result = await ha_client.get_area_registry()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_area_registry_exception(self, ha_client):
        """Test exception handling."""
        ha_client._request.side_effect = Exception("Network error")

        result = await ha_client.get_area_registry()

        assert result == []


class TestListEntities:
    """Tests for list_entities."""

    @pytest.mark.asyncio
    async def test_list_entities_basic(self, ha_client):
        """Test basic entity listing."""
        states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room Light"},
            },
            {
                "entity_id": "sensor.temperature",
                "state": "22.5",
                "attributes": {"friendly_name": "Temperature"},
            },
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.list_entities()

        assert len(result) == 2
        assert result[0]["entity_id"] == "light.living_room"
        assert result[0]["state"] == "on"
        assert result[0]["name"] == "Living Room Light"
        assert result[0]["domain"] == "light"

    @pytest.mark.asyncio
    async def test_list_entities_with_domain_filter(self, ha_client):
        """Test filtering by domain."""
        states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room"},
            },
            {
                "entity_id": "sensor.temperature",
                "state": "22.5",
                "attributes": {"friendly_name": "Temperature"},
            },
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.list_entities(domain="light")

        assert len(result) == 1
        assert result[0]["entity_id"] == "light.living_room"

    @pytest.mark.asyncio
    async def test_list_entities_with_search_query(self, ha_client):
        """Test search query filtering."""
        states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room Light"},
            },
            {
                "entity_id": "light.bedroom",
                "state": "off",
                "attributes": {"friendly_name": "Bedroom Light"},
            },
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.list_entities(search_query="living")

        assert len(result) == 1
        assert result[0]["entity_id"] == "light.living_room"

    @pytest.mark.asyncio
    async def test_list_entities_with_limit(self, ha_client):
        """Test limit parameter."""
        states = [
            {
                "entity_id": f"light.entity_{i}",
                "state": "on",
                "attributes": {"friendly_name": f"Light {i}"},
            }
            for i in range(10)
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.list_entities(limit=3)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_entities_detailed(self, ha_client):
        """Test detailed mode."""
        states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room", "brightness": 255},
                "last_changed": "2024-01-01T00:00:00",
                "last_updated": "2024-01-01T00:00:00",
            },
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.list_entities(detailed=True)

        assert len(result) == 1
        assert "attributes" in result[0]
        assert "last_changed" in result[0]
        assert result[0]["attributes"]["brightness"] == 255

    @pytest.mark.asyncio
    async def test_list_entities_with_registry_metadata(self, ha_client):
        """Test merging registry metadata."""
        states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room"},
            },
        ]
        registry_data = [
            {
                "entity_id": "light.living_room",
                "area_id": "living_room",
                "device_id": "device_123",
                "icon": "mdi:lightbulb",
            },
        ]
        ha_client._request.side_effect = [states, registry_data]

        result = await ha_client.list_entities()

        assert len(result) == 1
        assert result[0]["area_id"] == "living_room"
        assert result[0]["device_id"] == "device_123"
        assert result[0]["icon"] == "mdi:lightbulb"

    @pytest.mark.asyncio
    async def test_list_entities_fails_on_empty_states(self, ha_client):
        """Test error when states are empty."""
        ha_client._request.return_value = None

        with pytest.raises(HAClientError):
            await ha_client.list_entities()


class TestGetEntity:
    """Tests for get_entity."""

    @pytest.mark.asyncio
    async def test_get_entity_success(self, ha_client):
        """Test successful entity retrieval."""
        state = {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {"friendly_name": "Living Room", "brightness": 255},
            "last_changed": "2024-01-01T00:00:00",
        }
        ha_client._request.return_value = state

        result = await ha_client.get_entity("light.living_room")

        assert result is not None
        assert result["entity_id"] == "light.living_room"
        assert result["state"] == "on"
        assert result["name"] == "Living Room"
        assert result["domain"] == "light"
        assert "attributes" in result
        ha_client._request.assert_called_once_with("GET", "/api/states/light.living_room")

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, ha_client):
        """Test entity not found."""
        ha_client._request.return_value = None

        result = await ha_client.get_entity("light.nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_entity_not_detailed(self, ha_client):
        """Test entity retrieval without detailed mode."""
        state = {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {"friendly_name": "Living Room"},
        }
        ha_client._request.return_value = state

        result = await ha_client.get_entity("light.living_room", detailed=False)

        assert result is not None
        assert "attributes" not in result
        assert "last_changed" not in result


class TestDomainSummary:
    """Tests for domain_summary."""

    @pytest.mark.asyncio
    async def test_domain_summary_basic(self, ha_client):
        """Test basic domain summary."""
        states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room", "brightness": 255},
            },
            {
                "entity_id": "light.bedroom",
                "state": "off",
                "attributes": {"friendly_name": "Bedroom"},
            },
            {
                "entity_id": "light.kitchen",
                "state": "on",
                "attributes": {"friendly_name": "Kitchen"},
            },
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.domain_summary("light")

        assert result["total_count"] == 3
        assert result["state_distribution"]["on"] == 2
        assert result["state_distribution"]["off"] == 1
        assert len(result["examples"]["on"]) == 2
        assert len(result["examples"]["off"]) == 1
        assert "brightness" in result["common_attributes"]

    @pytest.mark.asyncio
    async def test_domain_summary_with_example_limit(self, ha_client):
        """Test domain summary with example limit."""
        states = [
            {
                "entity_id": f"light.entity_{i}",
                "state": "on",
                "attributes": {"friendly_name": f"Light {i}"},
            }
            for i in range(10)
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.domain_summary("light", example_limit=2)

        assert len(result["examples"]["on"]) == 2


class TestEntityAction:
    """Tests for entity_action."""

    @pytest.mark.asyncio
    async def test_entity_action_turn_on(self, ha_client):
        """Test turning entity on."""
        ha_client._request.return_value = {}

        result = await ha_client.entity_action("light.living_room", "on")

        assert result["success"] is True
        ha_client._request.assert_called_once_with(
            "POST",
            "/api/services/light/turn_on",
            json={"entity_id": "light.living_room"},
        )

    @pytest.mark.asyncio
    async def test_entity_action_turn_off(self, ha_client):
        """Test turning entity off."""
        ha_client._request.return_value = {}

        result = await ha_client.entity_action("light.living_room", "off")

        assert result["success"] is True
        ha_client._request.assert_called_once_with(
            "POST",
            "/api/services/light/turn_off",
            json={"entity_id": "light.living_room"},
        )

    @pytest.mark.asyncio
    async def test_entity_action_toggle(self, ha_client):
        """Test toggling entity."""
        ha_client._request.return_value = {}

        result = await ha_client.entity_action("light.living_room", "toggle")

        assert result["success"] is True
        ha_client._request.assert_called_once_with(
            "POST",
            "/api/services/light/toggle",
            json={"entity_id": "light.living_room"},
        )

    @pytest.mark.asyncio
    async def test_entity_action_with_params(self, ha_client):
        """Test entity action with additional parameters."""
        ha_client._request.return_value = {}

        result = await ha_client.entity_action(
            "light.living_room",
            "on",
            params={"brightness": 255, "color_temp": 370},
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["brightness"] == 255
        assert call_args[1]["json"]["color_temp"] == 370


class TestCallService:
    """Tests for call_service."""

    @pytest.mark.asyncio
    async def test_call_service_basic(self, ha_client):
        """Test basic service call."""
        ha_client._request.return_value = {"result": "success"}

        result = await ha_client.call_service(
            "light", "turn_on", {"entity_id": "light.living_room"}
        )

        assert result == {"result": "success"}
        ha_client._request.assert_called_once_with(
            "POST",
            "/api/services/light/turn_on",
            json={"entity_id": "light.living_room"},
        )

    @pytest.mark.asyncio
    async def test_call_service_no_data(self, ha_client):
        """Test service call without data."""
        ha_client._request.return_value = {}

        result = await ha_client.call_service("automation", "reload")

        assert result == {}
        ha_client._request.assert_called_once_with(
            "POST",
            "/api/services/automation/reload",
            json={},
        )


class TestGetHistory:
    """Tests for get_history."""

    @pytest.mark.asyncio
    async def test_get_history_success(self, ha_client):
        """Test successful history retrieval."""
        history_data = [
            [
                {
                    "state": "on",
                    "last_changed": "2024-01-01T00:00:00",
                },
                {
                    "state": "off",
                    "last_changed": "2024-01-01T01:00:00",
                },
            ],
        ]
        ha_client._request.return_value = history_data

        result = await ha_client.get_history("light.living_room", hours=24)

        assert result["entity_id"] == "light.living_room"
        assert result["count"] == 2
        assert len(result["states"]) == 2
        assert result["first_changed"] == "2024-01-01T00:00:00"
        assert result["last_changed"] == "2024-01-01T01:00:00"

    @pytest.mark.asyncio
    async def test_get_history_empty(self, ha_client):
        """Test empty history."""
        ha_client._request.return_value = None

        result = await ha_client.get_history("light.living_room", hours=24)

        assert result["entity_id"] == "light.living_room"
        assert result["count"] == 0
        assert result["states"] == []

    @pytest.mark.asyncio
    async def test_get_history_custom_hours(self, ha_client):
        """Test history with custom hours."""
        ha_client._request.return_value = [[]]

        result = await ha_client.get_history("light.living_room", hours=48)

        assert result["count"] == 0
        call_args = ha_client._request.call_args
        assert "filter_entity_id" in call_args[1]["params"]


class TestGetHistoryBatch:
    """Tests for get_history_batch — batch multi-entity history in a single API call."""

    @pytest.mark.asyncio
    async def test_get_history_batch_multiple_entities(self, ha_client):
        """Test batch fetching history for multiple entities in one API call."""
        # HA returns list of lists — one inner list per entity, ordered by filter_entity_id
        history_data = [
            [
                {
                    "entity_id": "light.living_room",
                    "state": "on",
                    "last_changed": "2024-01-01T00:00:00",
                },
                {
                    "entity_id": "light.living_room",
                    "state": "off",
                    "last_changed": "2024-01-01T01:00:00",
                },
            ],
            [
                {
                    "entity_id": "sensor.temperature",
                    "state": "22.5",
                    "last_changed": "2024-01-01T00:00:00",
                },
            ],
        ]
        ha_client._request.return_value = history_data

        result = await ha_client.get_history_batch(
            ["light.living_room", "sensor.temperature"], hours=24
        )

        # Single API call with comma-separated entity IDs
        ha_client._request.assert_called_once()
        call_args = ha_client._request.call_args
        assert call_args[1]["params"]["filter_entity_id"] == "light.living_room,sensor.temperature"

        # Results keyed by entity_id
        assert "light.living_room" in result
        assert "sensor.temperature" in result
        assert result["light.living_room"]["count"] == 2
        assert result["sensor.temperature"]["count"] == 1
        assert len(result["light.living_room"]["states"]) == 2

    @pytest.mark.asyncio
    async def test_get_history_batch_single_entity(self, ha_client):
        """Test batch with single entity is backward compatible."""
        history_data = [
            [
                {
                    "entity_id": "light.kitchen",
                    "state": "on",
                    "last_changed": "2024-01-01T00:00:00",
                },
            ],
        ]
        ha_client._request.return_value = history_data

        result = await ha_client.get_history_batch(["light.kitchen"], hours=12)

        assert "light.kitchen" in result
        assert result["light.kitchen"]["count"] == 1

    @pytest.mark.asyncio
    async def test_get_history_batch_empty_list(self, ha_client):
        """Test batch with empty entity list returns empty dict."""
        result = await ha_client.get_history_batch([], hours=24)

        assert result == {}
        ha_client._request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_history_batch_no_data(self, ha_client):
        """Test batch when HA returns no data."""
        ha_client._request.return_value = None

        result = await ha_client.get_history_batch(
            ["light.living_room", "sensor.temperature"], hours=24
        )

        # All entities should have empty states
        assert result["light.living_room"]["count"] == 0
        assert result["sensor.temperature"]["count"] == 0

    @pytest.mark.asyncio
    async def test_get_history_batch_partial_data(self, ha_client):
        """Test batch when HA returns data for fewer entities than requested."""
        # HA may return fewer inner lists if some entities have no history
        history_data = [
            [
                {
                    "entity_id": "light.living_room",
                    "state": "on",
                    "last_changed": "2024-01-01T00:00:00",
                },
            ],
        ]
        ha_client._request.return_value = history_data

        result = await ha_client.get_history_batch(
            ["light.living_room", "sensor.temperature"], hours=24
        )

        # First entity has data, second gets empty result
        assert result["light.living_room"]["count"] == 1
        assert result["sensor.temperature"]["count"] == 0


class TestGetLogbook:
    """Tests for get_logbook."""

    @pytest.mark.asyncio
    async def test_get_logbook_success(self, ha_client):
        """Test successful logbook retrieval."""
        logbook_data = [
            {
                "when": "2024-01-01T00:00:00",
                "name": "Living Room Light",
                "entity_id": "light.living_room",
                "state": "on",
            },
            {
                "when": "2024-01-01T01:00:00",
                "name": "Living Room Light",
                "entity_id": "light.living_room",
                "state": "off",
            },
        ]
        ha_client._request.return_value = logbook_data

        result = await ha_client.get_logbook(hours=24)

        assert len(result) == 2
        assert result[0]["entity_id"] == "light.living_room"

    @pytest.mark.asyncio
    async def test_get_logbook_with_entity_filter(self, ha_client):
        """Test logbook with entity filter."""
        logbook_data = [
            {
                "when": "2024-01-01T00:00:00",
                "entity_id": "light.living_room",
                "state": "on",
            },
        ]
        ha_client._request.return_value = logbook_data

        result = await ha_client.get_logbook(hours=24, entity_id="light.living_room")

        assert len(result) == 1
        call_args = ha_client._request.call_args
        assert call_args[1]["params"]["entity"] == "light.living_room"

    @pytest.mark.asyncio
    async def test_get_logbook_empty(self, ha_client):
        """Test empty logbook."""
        ha_client._request.return_value = None

        result = await ha_client.get_logbook(hours=24)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_logbook_invalid_format(self, ha_client):
        """Test invalid logbook format."""
        ha_client._request.return_value = {"invalid": "format"}

        result = await ha_client.get_logbook(hours=24)

        assert result == []


class TestSearchEntities:
    """Tests for search_entities."""

    @pytest.mark.asyncio
    async def test_search_entities_success(self, ha_client):
        """Test successful entity search."""
        states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room Light"},
            },
            {
                "entity_id": "light.bedroom",
                "state": "off",
                "attributes": {"friendly_name": "Bedroom Light"},
            },
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.search_entities("living", limit=20)

        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert "domains" in result
        assert result["domains"]["light"] == 1

    @pytest.mark.asyncio
    async def test_search_entities_multiple_domains(self, ha_client):
        """Test search across multiple domains."""
        states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room Light"},
            },
            {
                "entity_id": "sensor.living_temperature",
                "state": "22.5",
                "attributes": {"friendly_name": "Living Temperature"},
            },
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.search_entities("living")

        assert result["count"] == 2
        assert result["domains"]["light"] == 1
        assert result["domains"]["sensor"] == 1

    @pytest.mark.asyncio
    async def test_search_entities_with_limit(self, ha_client):
        """Test search with limit."""
        states = [
            {
                "entity_id": f"light.entity_{i}",
                "state": "on",
                "attributes": {"friendly_name": f"Light {i}"},
            }
            for i in range(10)
        ]
        ha_client._request.side_effect = [states, []]

        result = await ha_client.search_entities("light", limit=5)

        assert result["count"] == 5
        assert len(result["results"]) == 5
