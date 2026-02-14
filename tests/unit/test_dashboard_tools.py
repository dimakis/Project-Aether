"""Tests for dashboard tools.

Validates the LangChain-compatible tools for the Dashboard Designer agent,
including YAML generation, validation, and dashboard listing.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestGenerateDashboardYaml:
    """Tests for the generate_dashboard_yaml tool."""

    @pytest.fixture(autouse=True)
    def _patch_ha_client(self):
        """Patch the HA client for all tests in this class."""
        mock_client = AsyncMock()
        mock_client.get_areas = AsyncMock(
            return_value=[
                {"area_id": "living_room", "name": "Living Room"},
                {"area_id": "kitchen", "name": "Kitchen"},
            ]
        )
        mock_client.get_entities_by_area = AsyncMock(
            return_value=[
                {
                    "entity_id": "light.living_room",
                    "state": "on",
                    "attributes": {"friendly_name": "Living Room Light"},
                },
                {
                    "entity_id": "sensor.living_room_temp",
                    "state": "22.5",
                    "attributes": {
                        "friendly_name": "Living Room Temperature",
                        "unit_of_measurement": "°C",
                    },
                },
            ]
        )
        with patch("src.tools.dashboard_tools.get_ha_client", return_value=mock_client):
            self.mock_client = mock_client
            yield

    @pytest.mark.asyncio
    async def test_generate_returns_yaml_string(self):
        """generate_dashboard_yaml returns a YAML-formatted string."""
        from src.tools.dashboard_tools import generate_dashboard_yaml

        result = await generate_dashboard_yaml.ainvoke(
            {"title": "Test Dashboard", "areas": ["living_room"]}
        )
        assert isinstance(result, str)
        assert "views:" in result or "title:" in result

    @pytest.mark.asyncio
    async def test_generate_includes_title(self):
        """Generated YAML includes the requested title."""
        from src.tools.dashboard_tools import generate_dashboard_yaml

        result = await generate_dashboard_yaml.ainvoke(
            {"title": "Energy Overview", "areas": ["living_room"]}
        )
        assert "Energy Overview" in result


class TestValidateDashboardYaml:
    """Tests for the validate_dashboard_yaml tool."""

    @pytest.mark.asyncio
    async def test_valid_yaml_passes(self):
        """Valid Lovelace YAML returns success."""
        from src.tools.dashboard_tools import validate_dashboard_yaml

        yaml_str = """
views:
  - title: Overview
    cards:
      - type: entities
        entities:
          - light.living_room
"""
        result = await validate_dashboard_yaml.ainvoke({"yaml_content": yaml_str})
        assert "valid" in result.lower() or "success" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_yaml_returns_error(self):
        """Invalid YAML returns an error message."""
        from src.tools.dashboard_tools import validate_dashboard_yaml

        result = await validate_dashboard_yaml.ainvoke({"yaml_content": "not: [valid: yaml: {"})
        assert "error" in result.lower() or "invalid" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_views_key(self):
        """YAML without views key returns a warning."""
        from src.tools.dashboard_tools import validate_dashboard_yaml

        yaml_str = """
title: My Dashboard
cards:
  - type: entities
"""
        result = await validate_dashboard_yaml.ainvoke({"yaml_content": yaml_str})
        assert "views" in result.lower()


class TestListDashboards:
    """Tests for the list_dashboards tool."""

    @pytest.fixture(autouse=True)
    def _patch_ha_client(self):
        mock_client = AsyncMock()
        mock_client.list_dashboards = AsyncMock(
            return_value=[
                {"id": "lovelace", "title": "Home", "mode": "storage"},
                {"id": "lovelace-energy", "title": "Energy", "mode": "yaml"},
            ]
        )
        with patch("src.tools.dashboard_tools.get_ha_client", return_value=mock_client):
            self.mock_client = mock_client
            yield

    @pytest.mark.asyncio
    async def test_returns_dashboard_list(self):
        """list_dashboards returns a summary of dashboards."""
        from src.tools.dashboard_tools import list_dashboards

        result = await list_dashboards.ainvoke({})
        assert isinstance(result, str)
        assert "lovelace" in result.lower() or "dashboard" in result.lower()


class TestGenerateDashboardYamlNoN1:
    """Test that generate_dashboard_yaml does NOT call list_entities per area."""

    @pytest.mark.asyncio
    async def test_list_entities_called_once_for_multiple_areas(self):
        """list_entities should be called at most once, not per area."""
        mock_client = AsyncMock()
        mock_client.list_entities = AsyncMock(
            return_value=[
                {"entity_id": "light.living", "attributes": {"area_id": "living_room"}},
                {"entity_id": "light.kitchen", "attributes": {"area_id": "kitchen"}},
                {"entity_id": "sensor.temp", "attributes": {"area_id": "living_room"}},
            ]
        )

        with patch("src.tools.dashboard_tools.get_ha_client", return_value=mock_client):
            from src.tools.dashboard_tools import generate_dashboard_yaml

            result = await generate_dashboard_yaml.ainvoke(
                {"title": "Test", "areas": ["living_room", "kitchen", "bedroom"]}
            )

        # list_entities should be called exactly once regardless of area count
        assert mock_client.list_entities.call_count == 1
        assert isinstance(result, str)


class TestGetDashboardTools:
    """Tests for the get_dashboard_tools function."""

    def test_returns_list_of_tools(self):
        """get_dashboard_tools returns a list of tool objects."""
        from src.tools.dashboard_tools import get_dashboard_tools

        tools = get_dashboard_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 3

    def test_tool_names(self):
        """Tool list contains the expected tool names."""
        from src.tools.dashboard_tools import get_dashboard_tools

        tools = get_dashboard_tools()
        names = [t.name for t in tools]
        assert "generate_dashboard_yaml" in names
        assert "validate_dashboard_yaml" in names
        assert "list_dashboards" in names
