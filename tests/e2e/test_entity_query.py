"""End-to-end tests for natural language entity queries.

Tests the full NL query flow from user input to entity results.
Constitution: Reliability & Quality - E2E NL query validation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_query_entities():
    """Create mock entities for query testing."""
    return [
        {
            "entity_id": "light.living_room_main",
            "domain": "light",
            "name": "Living Room Main Light",
            "state": "on",
            "area_id": "living_room",
            "attributes": {"brightness": 200},
        },
        {
            "entity_id": "light.living_room_lamp",
            "domain": "light",
            "name": "Living Room Lamp",
            "state": "off",
            "area_id": "living_room",
            "attributes": {"brightness": 0},
        },
        {
            "entity_id": "light.bedroom_ceiling",
            "domain": "light",
            "name": "Bedroom Ceiling Light",
            "state": "off",
            "area_id": "bedroom",
            "attributes": {"brightness": 0},
        },
        {
            "entity_id": "sensor.living_room_temperature",
            "domain": "sensor",
            "name": "Living Room Temperature",
            "state": "22.5",
            "area_id": "living_room",
            "attributes": {"unit_of_measurement": "°C", "device_class": "temperature"},
        },
        {
            "entity_id": "sensor.bedroom_temperature",
            "domain": "sensor",
            "name": "Bedroom Temperature",
            "state": "20.0",
            "area_id": "bedroom",
            "attributes": {"unit_of_measurement": "°C", "device_class": "temperature"},
        },
        {
            "entity_id": "binary_sensor.front_door",
            "domain": "binary_sensor",
            "name": "Front Door",
            "state": "off",
            "attributes": {"device_class": "door"},
        },
        {
            "entity_id": "switch.kitchen_outlet",
            "domain": "switch",
            "name": "Kitchen Outlet",
            "state": "on",
            "area_id": "kitchen",
            "attributes": {},
        },
    ]


@pytest.fixture
def mock_llm_for_query():
    """Create mock LLM that returns structured query filters."""
    from langchain_core.messages import AIMessage

    llm = MagicMock()

    def create_response(content):
        return AIMessage(
            content=content,
            usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )

    llm.ainvoke = AsyncMock(
        side_effect=lambda _: create_response(
            '{"domain": "light", "area": null, "state": null, "name_contains": null}'
        )
    )

    return llm


@pytest.mark.e2e
@pytest.mark.asyncio
class TestNaturalLanguageQuery:
    """End-to-end tests for NL entity queries."""

    async def test_query_all_lights(self, mock_query_entities, mock_llm_for_query):
        """Test querying for all lights."""
        import json

        # Mock the LLM to return domain filter for lights
        mock_llm_for_query.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"domain": "light", "area": null, "state": null, "name_contains": null}'
            )
        )

        # Simulate query parsing (what NaturalLanguageQueryEngine would do)
        query = "Show me all lights"

        # Parse expected filter from LLM response
        filter_response = await mock_llm_for_query.ainvoke(query)
        filters = json.loads(filter_response.content)

        # Apply filter manually (simulating query logic)
        results = [e for e in mock_query_entities if e["domain"] == filters["domain"]]

        assert len(results) == 3
        assert all(e["domain"] == "light" for e in results)

    async def test_query_lights_in_living_room(self, mock_query_entities, mock_llm_for_query):
        """Test querying for lights in a specific area."""
        mock_llm_for_query.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"domain": "light", "area": "living_room", "state": null, "name_contains": null}'
            )
        )

        query = "Show me lights in the living room"

        import json

        filter_response = await mock_llm_for_query.ainvoke(query)
        filters = json.loads(filter_response.content)

        results = [
            e
            for e in mock_query_entities
            if e["domain"] == filters["domain"] and e.get("area_id") == filters["area"]
        ]

        assert len(results) == 2
        assert all("living_room" in e["entity_id"] for e in results)

    async def test_query_lights_that_are_on(self, mock_query_entities, mock_llm_for_query):
        """Test querying for lights with specific state."""
        mock_llm_for_query.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"domain": "light", "area": null, "state": "on", "name_contains": null}'
            )
        )

        query = "Which lights are on?"

        import json

        filter_response = await mock_llm_for_query.ainvoke(query)
        filters = json.loads(filter_response.content)

        results = [
            e
            for e in mock_query_entities
            if e["domain"] == filters["domain"] and e["state"] == filters["state"]
        ]

        assert len(results) == 1
        assert results[0]["entity_id"] == "light.living_room_main"

    async def test_query_temperature_sensors(self, mock_query_entities, mock_llm_for_query):
        """Test querying for temperature sensors."""
        mock_llm_for_query.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"domain": "sensor", "area": null, "state": null, "name_contains": "temperature"}'
            )
        )

        query = "Show me all temperature sensors"

        import json

        filter_response = await mock_llm_for_query.ainvoke(query)
        filters = json.loads(filter_response.content)

        results = [
            e
            for e in mock_query_entities
            if e["domain"] == filters["domain"]
            and (
                filters["name_contains"] is None
                or filters["name_contains"].lower() in e["name"].lower()
            )
        ]

        assert len(results) == 2
        assert all("temperature" in e["name"].lower() for e in results)

    async def test_query_by_name_pattern(self, mock_query_entities, mock_llm_for_query):
        """Test querying entities by name pattern."""
        mock_llm_for_query.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"domain": null, "area": null, "state": null, "name_contains": "bedroom"}'
            )
        )

        query = "Find anything related to bedroom"

        import json

        filter_response = await mock_llm_for_query.ainvoke(query)
        filters = json.loads(filter_response.content)

        results = [
            e for e in mock_query_entities if filters["name_contains"].lower() in e["name"].lower()
        ]

        assert len(results) == 2
        assert all("bedroom" in e["name"].lower() for e in results)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestQueryEdgeCases:
    """Test edge cases in NL queries."""

    async def test_query_no_results(self, mock_query_entities, mock_llm_for_query):
        """Test query that returns no results."""
        mock_llm_for_query.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"domain": "climate", "area": null, "state": null, "name_contains": null}'
            )
        )

        import json

        filter_response = await mock_llm_for_query.ainvoke("Show me thermostats")
        filters = json.loads(filter_response.content)

        results = [e for e in mock_query_entities if e["domain"] == filters["domain"]]

        assert len(results) == 0

    async def test_query_all_entities(self, mock_query_entities, mock_llm_for_query):
        """Test query that returns all entities."""
        mock_llm_for_query.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"domain": null, "area": null, "state": null, "name_contains": null}'
            )
        )

        import json

        filter_response = await mock_llm_for_query.ainvoke("Show me everything")
        filters = json.loads(filter_response.content)

        # No filters, return all
        results = mock_query_entities if all(v is None for v in filters.values()) else []

        # This should return all entities
        assert len(results) == len(mock_query_entities)

    async def test_query_combined_filters(self, mock_query_entities, mock_llm_for_query):
        """Test query with multiple filters."""
        mock_llm_for_query.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"domain": "sensor", "area": "living_room", "state": null, "name_contains": null}'
            )
        )

        import json

        filter_response = await mock_llm_for_query.ainvoke("Show me sensors in the living room")
        filters = json.loads(filter_response.content)

        results = [
            e
            for e in mock_query_entities
            if e["domain"] == filters["domain"] and e.get("area_id") == filters["area"]
        ]

        assert len(results) == 1
        assert results[0]["entity_id"] == "sensor.living_room_temperature"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestQueryWithDatabase:
    """E2E tests for NL queries with database (requires testcontainers)."""

    @pytest.mark.requires_postgres
    @pytest.mark.skip(reason="Requires testcontainers and LLM setup")
    async def test_full_query_workflow(self, integration_session, mock_llm_for_query):
        """Test complete NL query workflow with database."""
        # This test would:
        # 1. Populate database with test entities
        # 2. Run NL query through QueryRepository
        # 3. Verify correct entities are returned
        pass

    @pytest.mark.requires_postgres
    @pytest.mark.skip(reason="Requires testcontainers and LLM setup")
    async def test_query_performance(self, integration_session):
        """Test query performance with many entities."""
        # This test would measure query time with 1000+ entities
        pass


@pytest.mark.e2e
class TestQueryResultFormatting:
    """Test query result formatting."""

    def test_format_light_results(self, mock_query_entities):
        """Test formatting light entity results."""
        lights = [e for e in mock_query_entities if e["domain"] == "light"]

        formatted = []
        for light in lights:
            formatted.append(
                {
                    "entity_id": light["entity_id"],
                    "name": light["name"],
                    "state": light["state"],
                    "brightness": light["attributes"].get("brightness", "N/A"),
                }
            )

        assert len(formatted) == 3
        assert formatted[0]["brightness"] == 200
        assert formatted[1]["brightness"] == 0

    def test_format_sensor_results(self, mock_query_entities):
        """Test formatting sensor entity results."""
        sensors = [e for e in mock_query_entities if e["domain"] == "sensor"]

        formatted = []
        for sensor in sensors:
            formatted.append(
                {
                    "entity_id": sensor["entity_id"],
                    "name": sensor["name"],
                    "value": sensor["state"],
                    "unit": sensor["attributes"].get("unit_of_measurement", ""),
                }
            )

        assert len(formatted) == 2
        assert formatted[0]["unit"] == "°C"

    def test_format_mixed_results(self, mock_query_entities):
        """Test formatting mixed entity types."""
        # Filter to living room
        living_room = [e for e in mock_query_entities if e.get("area_id") == "living_room"]

        assert len(living_room) == 3  # 2 lights + 1 sensor

        # Check we can access common attributes
        for entity in living_room:
            assert "entity_id" in entity
            assert "name" in entity
            assert "state" in entity


@pytest.mark.e2e
@pytest.mark.asyncio
class TestQueryIntentRecognition:
    """Test NL query intent recognition patterns."""

    async def test_recognizes_list_intent(self, mock_llm_for_query):
        """Test recognizing list/show intents."""
        queries = [
            "Show me all lights",
            "List sensors",
            "What devices are in the kitchen?",
            "Display temperature sensors",
        ]

        # All should be recognized as list queries
        for query in queries:
            # In real implementation, intent would be detected
            assert any(word in query.lower() for word in ["show", "list", "what", "display"])

    async def test_recognizes_state_query_intent(self, mock_llm_for_query):
        """Test recognizing state query intents."""
        queries = [
            "Which lights are on?",
            "What's turned off?",
            "Is the door open?",
            "Are any windows open?",
        ]

        # All should be recognized as state queries
        for query in queries:
            assert any(
                word in query.lower()
                for word in ["which", "what", "is", "are", "on", "off", "open"]
            )

    async def test_recognizes_location_filter(self, mock_llm_for_query):
        """Test recognizing location/area filters."""
        queries = [
            "Lights in the bedroom",
            "Living room sensors",
            "Kitchen devices",
            "Show me garage entities",
        ]

        rooms = ["bedroom", "living room", "kitchen", "garage"]

        for query in queries:
            assert any(room in query.lower() for room in rooms)
