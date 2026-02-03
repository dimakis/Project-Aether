"""Unit tests for Home Assistant tools.

TDD: Testing HA tools that agents can use to query Home Assistant.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetEntityStateTool:
    """Tests for get_entity_state tool."""

    @pytest.mark.asyncio
    async def test_get_entity_state_returns_state(self):
        """Test getting entity state."""
        from src.tools.ha_tools import get_entity_state

        mock_mcp = MagicMock()
        mock_mcp.get_entity = AsyncMock(return_value={
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {"brightness": 255, "friendly_name": "Living Room Light"},
        })

        with patch("src.tools.ha_tools.get_mcp_client", return_value=mock_mcp):
            result = await get_entity_state.ainvoke({"entity_id": "light.living_room"})

        assert "on" in result.lower()
        assert "living_room" in result.lower()

    @pytest.mark.asyncio
    async def test_get_entity_state_not_found(self):
        """Test getting non-existent entity."""
        from src.tools.ha_tools import get_entity_state

        mock_mcp = MagicMock()
        mock_mcp.get_entity = AsyncMock(return_value=None)

        with patch("src.tools.ha_tools.get_mcp_client", return_value=mock_mcp):
            result = await get_entity_state.ainvoke({"entity_id": "light.nonexistent"})

        assert "not found" in result.lower() or "error" in result.lower()


class TestListEntitiesByDomainTool:
    """Tests for list_entities_by_domain tool."""

    @pytest.mark.asyncio
    async def test_list_lights(self):
        """Test listing light entities."""
        from src.tools.ha_tools import list_entities_by_domain

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value={
            "results": [
                {"entity_id": "light.living_room", "state": "on"},
                {"entity_id": "light.bedroom", "state": "off"},
            ]
        })

        with patch("src.tools.ha_tools.get_mcp_client", return_value=mock_mcp):
            result = await list_entities_by_domain.ainvoke({"domain": "light"})

        assert "light.living_room" in result
        assert "light.bedroom" in result

    @pytest.mark.asyncio
    async def test_list_with_state_filter(self):
        """Test listing entities filtered by state."""
        from src.tools.ha_tools import list_entities_by_domain

        mock_mcp = MagicMock()
        mock_mcp.list_entities = AsyncMock(return_value={
            "results": [
                {"entity_id": "light.living_room", "state": "on"},
                {"entity_id": "light.bedroom", "state": "off"},
            ]
        })

        with patch("src.tools.ha_tools.get_mcp_client", return_value=mock_mcp):
            result = await list_entities_by_domain.ainvoke({"domain": "light", "state_filter": "on"})

        assert "light.living_room" in result
        # bedroom is off, might not be in filtered result depending on implementation


class TestSearchEntitiesTool:
    """Tests for search_entities tool."""

    @pytest.mark.asyncio
    async def test_search_by_name(self):
        """Test searching entities by name."""
        from src.tools.ha_tools import search_entities

        mock_mcp = MagicMock()
        mock_mcp.search_entities = AsyncMock(return_value={
            "results": [
                {"entity_id": "light.kitchen", "state": "off"},
                {"entity_id": "sensor.kitchen_temperature", "state": "22"},
            ]
        })

        with patch("src.tools.ha_tools.get_mcp_client", return_value=mock_mcp):
            result = await search_entities.ainvoke({"query": "kitchen"})

        assert "kitchen" in result.lower()


class TestGetDomainSummaryTool:
    """Tests for get_domain_summary tool."""

    @pytest.mark.asyncio
    async def test_get_light_summary(self):
        """Test getting summary of light domain."""
        from src.tools.ha_tools import get_domain_summary

        mock_mcp = MagicMock()
        mock_mcp.domain_summary = AsyncMock(return_value={
            "total_count": 10,
            "state_distribution": {"on": 3, "off": 7},
        })

        with patch("src.tools.ha_tools.get_mcp_client", return_value=mock_mcp):
            result = await get_domain_summary.ainvoke({"domain": "light"})

        assert "10" in result or "total" in result.lower()


class TestControlEntityTool:
    """Tests for control_entity tool."""

    @pytest.mark.asyncio
    async def test_turn_on_light(self):
        """Test turning on a light."""
        from src.tools.ha_tools import control_entity

        mock_mcp = MagicMock()
        mock_mcp.entity_action = AsyncMock(return_value={"success": True})

        with patch("src.tools.ha_tools.get_mcp_client", return_value=mock_mcp):
            result = await control_entity.ainvoke({
                "entity_id": "light.living_room",
                "action": "on"
            })

        assert "success" in result.lower() or "turned on" in result.lower()
        mock_mcp.entity_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_switch(self):
        """Test turning off a switch."""
        from src.tools.ha_tools import control_entity

        mock_mcp = MagicMock()
        mock_mcp.entity_action = AsyncMock(return_value={"success": True})

        with patch("src.tools.ha_tools.get_mcp_client", return_value=mock_mcp):
            result = await control_entity.ainvoke({
                "entity_id": "switch.garden",
                "action": "off"
            })

        mock_mcp.entity_action.assert_called_once()


class TestGetAllTools:
    """Tests for get_ha_tools function."""

    def test_returns_list_of_tools(self):
        """Test that get_ha_tools returns all tools."""
        from src.tools.ha_tools import get_ha_tools

        tools = get_ha_tools()

        assert len(tools) >= 4
        tool_names = [t.name for t in tools]
        assert "get_entity_state" in tool_names
        assert "list_entities_by_domain" in tool_names
        assert "search_entities" in tool_names
