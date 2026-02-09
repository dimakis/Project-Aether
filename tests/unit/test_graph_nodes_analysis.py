"""Unit tests for analysis workflow nodes (src/graph/nodes/analysis.py).

All HA, agent, and sandbox calls are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import AnalysisState


def _make_state(**overrides) -> MagicMock:
    state = MagicMock(spec=AnalysisState)
    state.run_id = "run-1"
    state.mlflow_run_id = None
    state.entity_ids = ["sensor.energy_total"]
    state.time_range_hours = 24
    state.generated_script = None
    state.script_executions = []
    state.insights = []
    state.recommendations = []
    state.automation_suggestion = None
    state.analysis_type = "energy"
    state.errors = []
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


class TestCollectEnergyDataNode:
    async def test_collects_energy_data(self):
        from src.graph.nodes.analysis import collect_energy_data_node

        mock_ha = MagicMock()
        mock_energy = MagicMock()
        mock_energy.get_aggregated_energy = AsyncMock(
            return_value={"total_kwh": 42.5}
        )

        with (
            patch("src.ha.EnergyHistoryClient", return_value=mock_energy),
        ):
            state = _make_state()
            result = await collect_energy_data_node(state, ha_client=mock_ha)
            assert "entity_ids" in result

    async def test_discovers_sensors_when_empty(self):
        from src.graph.nodes.analysis import collect_energy_data_node

        mock_ha = MagicMock()
        mock_energy = MagicMock()
        mock_energy.get_energy_sensors = AsyncMock(
            return_value=[{"entity_id": "sensor.auto_discovered"}]
        )
        mock_energy.get_aggregated_energy = AsyncMock(
            return_value={"total_kwh": 10.0}
        )

        with patch("src.ha.EnergyHistoryClient", return_value=mock_energy):
            state = _make_state(entity_ids=[])
            result = await collect_energy_data_node(state, ha_client=mock_ha)
            assert "sensor.auto_discovered" in result["entity_ids"]


class TestAnalysisErrorNode:
    async def test_error_node(self):
        from src.graph.nodes.analysis import analysis_error_node

        state = _make_state()
        error = RuntimeError("Analysis crashed")
        result = await analysis_error_node(state, error=error)
        assert result["insights"][0]["type"] == "error"
        assert "RuntimeError" in result["messages"][0].content


class TestCollectBehavioralDataNode:
    async def test_collects_behavioral_data(self):
        from src.graph.nodes.analysis import collect_behavioral_data_node

        mock_ha = MagicMock()
        mock_logbook = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_entries = 100
        mock_stats.automation_triggers = 20
        mock_stats.manual_actions = 30
        mock_stats.unique_entities = 15
        mock_logbook.get_stats = AsyncMock(return_value=mock_stats)

        with patch("src.ha.LogbookHistoryClient", return_value=mock_logbook):
            result = await collect_behavioral_data_node(_make_state(), ha_client=mock_ha)
            assert "100 entries" in result["messages"][0].content

    async def test_handles_error(self):
        from src.graph.nodes.analysis import collect_behavioral_data_node

        mock_ha = MagicMock()
        mock_logbook = MagicMock()
        mock_logbook.get_stats = AsyncMock(side_effect=Exception("HA error"))

        with patch("src.ha.LogbookHistoryClient", return_value=mock_logbook):
            result = await collect_behavioral_data_node(_make_state(), ha_client=mock_ha)
            assert "Failed" in result["messages"][0].content


class TestAnalyzeAndSuggestNode:
    async def test_delegates_to_agent(self):
        from src.graph.nodes.analysis import analyze_and_suggest_node

        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={"insights": [{"type": "test"}]})
        mock_agent.role = MagicMock()
        mock_agent.role.value = "data_scientist"

        with (
            patch("src.agents.DataScientistAgent", return_value=mock_agent),
            patch("src.api.metrics.get_metrics_collector", return_value=MagicMock()),
        ):
            result = await analyze_and_suggest_node(_make_state())
            assert result == {"insights": [{"type": "test"}]}

    async def test_handles_error(self):
        from src.graph.nodes.analysis import analyze_and_suggest_node

        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(side_effect=Exception("Agent failed"))
        mock_agent.role = MagicMock()
        mock_agent.role.value = "data_scientist"

        with (
            patch("src.agents.DataScientistAgent", return_value=mock_agent),
            patch("src.api.metrics.get_metrics_collector", return_value=MagicMock()),
        ):
            result = await analyze_and_suggest_node(_make_state())
            assert result["insights"][0]["type"] == "error"


class TestArchitectReviewNode:
    async def test_no_suggestion(self):
        from src.graph.nodes.analysis import architect_review_node

        state = _make_state(automation_suggestion=None)
        result = await architect_review_node(state)
        assert "No automation suggestions" in result["messages"][0].content

    async def test_requires_session(self):
        from src.graph.nodes.analysis import architect_review_node

        suggestion = MagicMock()
        suggestion.pattern = "Turn off lights at night"
        state = _make_state(automation_suggestion=suggestion)

        with (
            patch("src.agents.ArchitectAgent"),
            pytest.raises(ValueError, match="Session is required"),
        ):
            await architect_review_node(state, session=None)

    async def test_review_success(self):
        from src.graph.nodes.analysis import architect_review_node

        suggestion = MagicMock()
        suggestion.pattern = "Turn off lights at night"
        state = _make_state(automation_suggestion=suggestion)

        mock_architect = MagicMock()
        mock_architect.receive_suggestion = AsyncMock(
            return_value={
                "response": "Created proposal",
                "proposal_name": "Night Lights Off",
                "proposal_yaml": "alias: Night Lights Off",
            }
        )
        mock_session = AsyncMock()

        with patch("src.agents.ArchitectAgent", return_value=mock_architect):
            result = await architect_review_node(state, session=mock_session)
            assert "Night Lights Off" in result["messages"][0].content


class TestPresentRecommendationsNode:
    async def test_with_insights_and_recommendations(self):
        from src.graph.nodes.analysis import present_recommendations_node

        state = _make_state(
            insights=[
                {"title": "High energy usage", "impact": "high"},
                {"title": "Idle devices", "impact": "low"},
            ],
            recommendations=["Turn off idle devices", "Schedule heater"],
            automation_suggestion=None,
        )
        result = await present_recommendations_node(state)
        content = result["messages"][0].content
        assert "2 insight(s)" in content
        assert "High energy usage" in content

    async def test_with_automation_suggestion(self):
        from src.graph.nodes.analysis import present_recommendations_node

        suggestion = MagicMock()
        suggestion.pattern = "Auto-dim lights at night based on sunset"

        state = _make_state(
            insights=[],
            recommendations=[],
            automation_suggestion=suggestion,
        )
        result = await present_recommendations_node(state)
        assert "Auto-dim lights" in result["messages"][0].content

    async def test_empty_results(self):
        from src.graph.nodes.analysis import present_recommendations_node

        state = _make_state(
            insights=[],
            recommendations=[],
            automation_suggestion=None,
        )
        result = await present_recommendations_node(state)
        assert "0 insight(s)" in result["messages"][0].content
