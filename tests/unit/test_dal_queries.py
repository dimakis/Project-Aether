"""Unit tests for Natural Language Query interface.

Tests NL query parsing and execution with mocked dependencies.
Constitution: Reliability & Quality - query interface testing.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.dal.queries import NaturalLanguageQueryEngine


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def query_engine(mock_session):
    """Create query engine with mock session."""
    return NaturalLanguageQueryEngine(mock_session)


class TestIntentParsing:
    """Tests for query intent parsing."""

    @pytest.mark.asyncio
    async def test_parse_domain_light(self, query_engine):
        """Test parsing query with light domain."""
        intent = await query_engine._parse_intent("Show me all lights")

        assert intent["filters"].get("domain") == "light"

    @pytest.mark.asyncio
    async def test_parse_domain_switch(self, query_engine):
        """Test parsing query with switch domain."""
        intent = await query_engine._parse_intent("List all switches")

        assert intent["filters"].get("domain") == "switch"

    @pytest.mark.asyncio
    async def test_parse_domain_sensor(self, query_engine):
        """Test parsing query with sensor domain."""
        intent = await query_engine._parse_intent("What sensors do I have?")

        assert intent["filters"].get("domain") == "sensor"

    @pytest.mark.asyncio
    async def test_parse_state_on(self, query_engine):
        """Test parsing query looking for 'on' state."""
        intent = await query_engine._parse_intent("Which lights are on?")

        assert intent["filters"].get("state") == "on"

    @pytest.mark.asyncio
    async def test_parse_state_off(self, query_engine):
        """Test parsing query looking for 'off' state."""
        intent = await query_engine._parse_intent("What lights are off?")

        assert intent["filters"].get("state") == "off"

    @pytest.mark.asyncio
    async def test_parse_count_query(self, query_engine):
        """Test parsing count query."""
        intent = await query_engine._parse_intent("How many lights do I have?")

        assert intent["type"] == "count"

    @pytest.mark.asyncio
    async def test_parse_area_living_room(self, query_engine):
        """Test parsing query with area mention."""
        intent = await query_engine._parse_intent("Show lights in living room")

        assert intent["filters"].get("area_name") == "living room"

    @pytest.mark.asyncio
    async def test_parse_device_query(self, query_engine):
        """Test parsing device query."""
        intent = await query_engine._parse_intent("Show me all devices")

        assert intent["type"] == "list_devices"

    @pytest.mark.asyncio
    async def test_parse_area_query(self, query_engine):
        """Test parsing area query."""
        intent = await query_engine._parse_intent("Which areas do I have?")

        assert intent["type"] == "list_areas"

    @pytest.mark.asyncio
    async def test_parse_automation_query(self, query_engine):
        """Test parsing automation query."""
        intent = await query_engine._parse_intent("List all automations")

        assert intent["type"] == "list_automations"


class TestQueryExecution:
    """Tests for query execution."""

    @pytest.mark.asyncio
    async def test_execute_count_query(self, query_engine, mock_session):
        """Test executing count query."""
        # Mock entity_repo.count
        query_engine.entity_repo.count = AsyncMock(return_value=42)

        result = await query_engine._execute_query(
            {
                "type": "count",
                "filters": {"domain": "light"},
            }
        )

        assert result["count"] == 42

    @pytest.mark.asyncio
    async def test_execute_list_entities(self, query_engine):
        """Test executing entity list query."""
        mock_entities = [
            MagicMock(
                id="1",
                entity_id="light.test",
                name="Test",
                domain="light",
                state="on",
                device_class=None,
                unit_of_measurement=None,
                area=None,
                device=None,
            )
        ]
        query_engine.entity_repo.list_all = AsyncMock(return_value=mock_entities)

        result = await query_engine._execute_query(
            {
                "type": "list_entities",
                "filters": {"domain": "light"},
                "limit": 20,
            }
        )

        assert "entities" in result
        assert len(result["entities"]) == 1

    @pytest.mark.asyncio
    async def test_execute_list_devices(self, query_engine):
        """Test executing device list query."""
        mock_devices = [
            MagicMock(
                id="1",
                ha_device_id="device_123",
                name="Test Device",
                manufacturer="Test",
                model="Model 1",
                area=None,
            )
        ]
        query_engine.device_repo.list_all = AsyncMock(return_value=mock_devices)

        result = await query_engine._execute_query(
            {
                "type": "list_devices",
                "filters": {},
                "limit": 20,
            }
        )

        assert "devices" in result
        assert len(result["devices"]) == 1

    @pytest.mark.asyncio
    async def test_execute_list_areas(self, query_engine):
        """Test executing area list query."""
        mock_areas = [
            MagicMock(
                id="1",
                ha_area_id="living_room",
                name="Living Room",
                entities=[],
            )
        ]
        query_engine.area_repo.list_all = AsyncMock(return_value=mock_areas)

        result = await query_engine._execute_query(
            {
                "type": "list_areas",
                "filters": {},
                "limit": 20,
            }
        )

        assert "areas" in result
        assert len(result["areas"]) == 1


class TestExplanationGeneration:
    """Tests for query explanation generation."""

    def test_count_explanation(self, query_engine):
        """Test explanation for count query."""
        explanation = query_engine._generate_explanation(
            {"type": "count", "filters": {"domain": "light"}},
            {"count": 10, "domain": "light"},
        )

        assert "10" in explanation
        assert "light" in explanation.lower()

    def test_entity_list_explanation(self, query_engine):
        """Test explanation for entity list query."""
        explanation = query_engine._generate_explanation(
            {"type": "list_entities", "filters": {"domain": "switch", "state": "on"}},
            {"count": 5, "entities": []},
        )

        assert "5" in explanation

    def test_device_explanation(self, query_engine):
        """Test explanation for device query."""
        explanation = query_engine._generate_explanation(
            {"type": "list_devices", "filters": {}},
            {"count": 15},
        )

        assert "15" in explanation
        assert "device" in explanation.lower()


class TestFullQuery:
    """Tests for full query flow."""

    @pytest.mark.asyncio
    async def test_full_query_flow(self, query_engine):
        """Test complete query from question to result."""
        # Mock the entity repo
        mock_entities = [
            MagicMock(
                id="1",
                entity_id="light.living_room",
                name="Living Room",
                domain="light",
                state="on",
                device_class=None,
                unit_of_measurement=None,
                area=MagicMock(name="Living Room"),
                device=None,
            )
        ]
        query_engine.entity_repo.list_all = AsyncMock(return_value=mock_entities)

        result = await query_engine.query("Show me lights that are on")

        assert "question" in result
        assert "intent" in result
        assert "result" in result
        assert "explanation" in result

    @pytest.mark.asyncio
    async def test_query_with_context(self, query_engine):
        """Test query with conversation context."""
        mock_entities = []
        query_engine.entity_repo.list_all = AsyncMock(return_value=mock_entities)

        result = await query_engine.query(
            "What about sensors?",
            context={"previous_query": "lights"},
        )

        assert result is not None
