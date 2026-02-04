"""Unit tests for insight extraction from script output.

Tests the parsing and normalization of script output into insights.
T110: Insight extraction tests.
"""

import json
from unittest.mock import MagicMock

import pytest

from src.agents.data_scientist import DataScientistAgent
from src.graph.state import AnalysisState, AnalysisType, AgentRole
from src.sandbox.runner import SandboxResult


@pytest.fixture
def agent():
    """Create DataScientistAgent for testing."""
    return DataScientistAgent()


@pytest.fixture
def analysis_state():
    """Create sample analysis state."""
    return AnalysisState(
        current_agent=AgentRole.DATA_SCIENTIST,
        analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
        entity_ids=["sensor.grid_power", "sensor.solar_power"],
        time_range_hours=24,
    )


class TestInsightExtractionFromJSON:
    """Tests for extracting insights from JSON output."""

    def test_extract_single_insight(self, agent, analysis_state):
        """Test extracting a single insight from valid JSON."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [{
                    "type": "energy_optimization",
                    "title": "High Grid Usage",
                    "description": "Grid power usage is 20% above average",
                    "confidence": 0.85,
                    "impact": "high",
                    "evidence": {"avg_usage": 5.2, "current_usage": 6.24},
                    "entities": ["sensor.grid_power"],
                }]
            }),
            stderr="",
            duration_seconds=1.5,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert len(insights) == 1
        assert insights[0]["type"] == "energy_optimization"
        assert insights[0]["title"] == "High Grid Usage"
        assert insights[0]["confidence"] == 0.85
        assert insights[0]["impact"] == "high"

    def test_extract_multiple_insights(self, agent, analysis_state):
        """Test extracting multiple insights from JSON."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [
                    {
                        "type": "energy_optimization",
                        "title": "Peak Usage",
                        "description": "Peak at 2PM",
                        "confidence": 0.9,
                        "impact": "medium",
                    },
                    {
                        "type": "anomaly_detection",
                        "title": "Unusual Spike",
                        "description": "Spike detected at 3AM",
                        "confidence": 0.75,
                        "impact": "high",
                    },
                ]
            }),
            stderr="",
            duration_seconds=2.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert len(insights) == 2
        assert insights[0]["type"] == "energy_optimization"
        assert insights[1]["type"] == "anomaly_detection"

    def test_extract_with_missing_fields(self, agent, analysis_state):
        """Test that missing fields get default values."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [{
                    "title": "Simple Insight",
                }]
            }),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert len(insights) == 1
        assert insights[0]["type"] == "custom"  # Default type
        assert insights[0]["confidence"] == 0.5  # Default confidence
        assert insights[0]["impact"] == "medium"  # Default impact
        assert insights[0]["description"] == ""  # Default description


class TestConfidenceNormalization:
    """Tests for confidence score normalization."""

    def test_confidence_above_one_clamped(self, agent, analysis_state):
        """Test that confidence > 1.0 is clamped to 1.0."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [{"confidence": 1.5, "title": "Test"}]
            }),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert insights[0]["confidence"] == 1.0

    def test_confidence_below_zero_clamped(self, agent, analysis_state):
        """Test that confidence < 0.0 is clamped to 0.0."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [{"confidence": -0.5, "title": "Test"}]
            }),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert insights[0]["confidence"] == 0.0

    def test_confidence_valid_range_preserved(self, agent, analysis_state):
        """Test that valid confidence values are preserved."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [{"confidence": 0.73, "title": "Test"}]
            }),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert insights[0]["confidence"] == 0.73


class TestInsightExtractionFromFailure:
    """Tests for handling failed script executions."""

    def test_extract_from_exit_code_error(self, agent, analysis_state):
        """Test insight creation from non-zero exit code."""
        result = SandboxResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="NameError: name 'pandas' is not defined",
            duration_seconds=0.5,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert len(insights) == 1
        assert insights[0]["type"] == "error"
        assert "failed" in insights[0]["title"].lower()
        assert "pandas" in insights[0]["description"]

    def test_extract_from_timeout(self, agent, analysis_state):
        """Test insight creation from timed out execution."""
        result = SandboxResult(
            success=False,
            exit_code=-1,
            stdout="",
            stderr="Script execution timed out",
            duration_seconds=30.0,
            policy_name="standard",
            timed_out=True,
        )

        insights = agent._extract_insights(result, analysis_state)

        assert len(insights) == 1
        assert insights[0]["type"] == "error"
        assert insights[0]["evidence"]["timed_out"] is True


class TestInsightExtractionFromRawOutput:
    """Tests for handling non-JSON output."""

    def test_extract_from_plain_text(self, agent, analysis_state):
        """Test fallback to raw text when JSON parsing fails."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout="Analysis complete. Energy usage is normal.",
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert len(insights) == 1
        assert insights[0]["confidence"] == 0.5  # Default for raw output
        assert "Energy usage is normal" in insights[0]["description"]

    def test_extract_from_malformed_json(self, agent, analysis_state):
        """Test handling of malformed JSON."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout='{"insights": [{"title": incomplete',
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        # Should fall back to raw output handling
        assert len(insights) == 1
        assert "incomplete" in insights[0]["description"]

    def test_extract_from_empty_output(self, agent, analysis_state):
        """Test handling of empty stdout."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert len(insights) == 1
        # Empty output still creates an insight with analysis type


class TestRecommendationExtraction:
    """Tests for extracting recommendations from output."""

    def test_extract_recommendations(self, agent):
        """Test extracting recommendations from JSON."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [],
                "recommendations": [
                    "Shift high-power appliances to off-peak hours",
                    "Consider adding solar battery storage",
                ]
            }),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        recs = agent._extract_recommendations(result)

        assert len(recs) == 2
        assert "off-peak" in recs[0].lower()
        assert "solar" in recs[1].lower()

    def test_extract_no_recommendations(self, agent):
        """Test handling when no recommendations in output."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({"insights": []}),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        recs = agent._extract_recommendations(result)

        assert recs == []

    def test_extract_recommendations_from_failed(self, agent):
        """Test that failed execution returns no recommendations."""
        result = SandboxResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="Error",
            duration_seconds=0.1,
            policy_name="standard",
        )

        recs = agent._extract_recommendations(result)

        assert recs == []


class TestEntityAssociation:
    """Tests for associating entities with insights."""

    def test_entities_from_insight(self, agent, analysis_state):
        """Test that entities from insight are preserved."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [{
                    "title": "Test",
                    "entities": ["sensor.specific_sensor"],
                }]
            }),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        assert insights[0]["entities"] == ["sensor.specific_sensor"]

    def test_entities_default_to_state(self, agent, analysis_state):
        """Test that missing entities default to state entities."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({
                "insights": [{"title": "Test"}]  # No entities specified
            }),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = agent._extract_insights(result, analysis_state)

        # Should default to the entities from analysis_state
        assert insights[0]["entities"] == analysis_state.entity_ids
