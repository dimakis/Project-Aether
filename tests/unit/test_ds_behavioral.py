"""Unit tests for Data Scientist behavioral analysis extensions.

Tests behavioral prompts, data collection, and suggestion generation.
Constitution: Reliability & Quality.

TDD: T234 variant - DS behavioral prompts + suggestion generation.
"""

from unittest.mock import AsyncMock

import pytest

from src.agents.data_scientist import (
    BEHAVIORAL_ANALYSIS_TYPES,
    DataScientistAgent,
)
from src.agents.prompts import load_prompt

DATA_SCIENTIST_BEHAVIORAL_PROMPT = load_prompt("data_scientist_behavioral")
from src.graph.state import AnalysisState, AnalysisType, AutomationSuggestion


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client."""
    client = AsyncMock()
    client.get_logbook = AsyncMock(return_value=[])
    client.list_automations = AsyncMock(return_value=[])
    return client


@pytest.fixture
def ds_agent(mock_ha_client):
    """Create DataScientistAgent with mock HA."""
    return DataScientistAgent(ha_client=mock_ha_client)


class TestBehavioralAnalysisTypes:
    def test_behavioral_types_defined(self):
        """All behavioral analysis types should be in the set."""
        assert AnalysisType.BEHAVIOR_ANALYSIS in BEHAVIORAL_ANALYSIS_TYPES
        assert AnalysisType.AUTOMATION_ANALYSIS in BEHAVIORAL_ANALYSIS_TYPES
        assert AnalysisType.AUTOMATION_GAP_DETECTION in BEHAVIORAL_ANALYSIS_TYPES
        assert AnalysisType.CORRELATION_DISCOVERY in BEHAVIORAL_ANALYSIS_TYPES
        assert AnalysisType.DEVICE_HEALTH in BEHAVIORAL_ANALYSIS_TYPES

    def test_energy_types_not_behavioral(self):
        """Energy types should not be in the behavioral set."""
        assert AnalysisType.ENERGY_OPTIMIZATION not in BEHAVIORAL_ANALYSIS_TYPES
        assert AnalysisType.DIAGNOSTIC not in BEHAVIORAL_ANALYSIS_TYPES


class TestBehavioralPrompt:
    def test_prompt_exists(self):
        """Behavioral prompt should exist and have content."""
        assert DATA_SCIENTIST_BEHAVIORAL_PROMPT
        assert "behavioral" in DATA_SCIENTIST_BEHAVIORAL_PROMPT.lower()
        assert "automation" in DATA_SCIENTIST_BEHAVIORAL_PROMPT.lower()


class TestBuildAnalysisPrompt:
    def test_behavior_analysis_prompt(self, ds_agent):
        state = AnalysisState(analysis_type=AnalysisType.BEHAVIOR_ANALYSIS)
        prompt = ds_agent._build_analysis_prompt(state, {"entity_count": 5, "total_kwh": 0})
        assert "behavioral" in prompt.lower() or "manually" in prompt.lower()

    def test_automation_gap_prompt(self, ds_agent):
        state = AnalysisState(analysis_type=AnalysisType.AUTOMATION_GAP_DETECTION)
        prompt = ds_agent._build_analysis_prompt(state, {"entity_count": 5, "total_kwh": 0})
        assert "automation" in prompt.lower() or "gap" in prompt.lower()

    def test_correlation_prompt(self, ds_agent):
        state = AnalysisState(analysis_type=AnalysisType.CORRELATION_DISCOVERY)
        prompt = ds_agent._build_analysis_prompt(state, {"entity_count": 5, "total_kwh": 0})
        assert "correlation" in prompt.lower()

    def test_device_health_prompt(self, ds_agent):
        state = AnalysisState(analysis_type=AnalysisType.DEVICE_HEALTH)
        prompt = ds_agent._build_analysis_prompt(state, {"entity_count": 5, "total_kwh": 0})
        assert "health" in prompt.lower() or "device" in prompt.lower()

    def test_cost_optimization_prompt(self, ds_agent):
        state = AnalysisState(analysis_type=AnalysisType.COST_OPTIMIZATION)
        prompt = ds_agent._build_analysis_prompt(state, {"entity_count": 5, "total_kwh": 0})
        assert "cost" in prompt.lower()


class TestGenerateAutomationSuggestion:
    def test_returns_suggestion_for_high_confidence_gap(self, ds_agent):
        insights = [
            {
                "type": "automation_gap",
                "title": "Bedroom lights off at 22:00",
                "description": "You turn off bedroom lights at 22:00 every night",
                "confidence": 0.85,
                "impact": "high",
                "evidence": {
                    "proposed_trigger": "time: 22:00",
                    "proposed_action": "turn off light.bedroom",
                },
                "entities": ["light.bedroom"],
            }
        ]

        suggestion = ds_agent._generate_automation_suggestion(insights)
        assert suggestion is not None
        assert isinstance(suggestion, AutomationSuggestion)
        assert "light.bedroom" in suggestion.entities
        assert suggestion.confidence == 0.85

    def test_returns_none_for_low_confidence(self, ds_agent):
        insights = [
            {
                "type": "automation_gap",
                "title": "Occasional pattern",
                "description": "Sometimes lights are off",
                "confidence": 0.3,
                "impact": "low",
                "evidence": {},
                "entities": [],
            }
        ]

        suggestion = ds_agent._generate_automation_suggestion(insights)
        assert suggestion is None

    def test_handles_different_insight_types(self, ds_agent):
        for insight_type in [
            "energy_optimization",
            "cost_saving",
            "anomaly_detection",
            "usage_pattern",
            "behavioral_pattern",
            "correlation",
            "device_health",
            "automation_inefficiency",
        ]:
            insights = [
                {
                    "type": insight_type,
                    "title": f"Test {insight_type}",
                    "description": "Test description",
                    "confidence": 0.9,
                    "impact": "critical",
                    "evidence": {},
                    "entities": ["test.entity"],
                }
            ]

            suggestion = ds_agent._generate_automation_suggestion(insights)
            assert suggestion is not None, f"Should suggest for {insight_type}"
            assert suggestion.source_insight_type == insight_type
