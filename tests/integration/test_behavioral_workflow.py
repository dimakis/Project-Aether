"""Integration tests for the behavioral analysis workflow.

Tests the full optimization workflow with mocked HA client.
Constitution: Reliability & Quality.

TDD: T238 - Full behavioral analysis workflow.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.graph.state import AnalysisState, AnalysisType


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client with behavioral data."""
    client = AsyncMock()

    now = datetime.now(UTC)
    client.get_logbook = AsyncMock(
        return_value=[
            {
                "entity_id": "light.living_room",
                "name": "Living Room",
                "message": "turned on",
                "when": (now - timedelta(hours=2)).isoformat(),
                "state": "on",
                "context_user_id": "user1",
            },
            {
                "entity_id": "automation.sunset_lights",
                "name": "Sunset Lights",
                "message": "triggered",
                "when": (now - timedelta(hours=1)).isoformat(),
                "state": "on",
            },
        ]
    )
    client.list_automations = AsyncMock(return_value=[])
    client.get_history = AsyncMock(
        return_value={
            "entity_id": "light.living_room",
            "states": [],
            "count": 0,
        }
    )
    client.list_entities = AsyncMock(return_value=[])

    return client


class TestOptimizationWorkflowBuild:
    def test_build_optimization_graph(self, mock_ha_client):
        """Optimization graph should build without errors."""
        from src.graph.workflows import build_optimization_graph

        graph = build_optimization_graph(ha_client=mock_ha_client)
        assert graph is not None

    def test_optimization_in_registry(self):
        """Optimization workflow should be in the workflow registry."""
        from src.graph.workflows import WORKFLOW_REGISTRY

        assert "optimization" in WORKFLOW_REGISTRY


class TestOptimizationNodes:
    @pytest.mark.asyncio
    async def test_collect_behavioral_data_node(self, mock_ha_client):
        """Behavioral data collection node should return stats."""
        from src.graph.nodes import collect_behavioral_data_node

        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
            time_range_hours=168,
        )

        result = await collect_behavioral_data_node(state, ha_client=mock_ha_client)
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_present_recommendations_node(self):
        """Recommendations node should format output."""
        from src.graph.nodes import present_recommendations_node

        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
            insights=[
                {
                    "type": "behavioral_pattern",
                    "title": "Test",
                    "impact": "medium",
                }
            ],
            recommendations=["Test recommendation"],
        )

        result = await present_recommendations_node(state)
        assert "messages" in result
