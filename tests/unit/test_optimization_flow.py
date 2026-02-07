"""Unit tests for the optimization flow (suggest-to-proposal).

Tests the propose_automation tool and AutomationSuggestion model.
Constitution: Reliability & Quality.

TDD: T237 - Suggestion flow tests.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.state import AutomationSuggestion


class TestAutomationSuggestionModel:
    def test_create_suggestion(self):
        suggestion = AutomationSuggestion(
            pattern="Bedroom lights off at 22:00 every night",
            entities=["light.bedroom"],
            proposed_trigger="time: 22:00",
            proposed_action="turn off light.bedroom",
            confidence=0.85,
            evidence={"occurrences": 7, "typical_time": "22:00"},
            source_insight_type="automation_gap",
        )
        assert suggestion.pattern == "Bedroom lights off at 22:00 every night"
        assert suggestion.confidence == 0.85
        assert len(suggestion.entities) == 1

    def test_default_values(self):
        suggestion = AutomationSuggestion(pattern="test")
        assert suggestion.entities == []
        assert suggestion.proposed_trigger == ""
        assert suggestion.proposed_action == ""
        assert suggestion.confidence == 0.0

    def test_confidence_bounds(self):
        suggestion = AutomationSuggestion(pattern="test", confidence=0.5)
        assert 0.0 <= suggestion.confidence <= 1.0

    def test_serialization(self):
        suggestion = AutomationSuggestion(
            pattern="test pattern",
            entities=["light.test"],
            confidence=0.9,
        )
        data = suggestion.model_dump()
        assert data["pattern"] == "test pattern"
        assert data["entities"] == ["light.test"]
        assert data["confidence"] == 0.9


class TestAnalysisStateWithSuggestion:
    def test_state_accepts_suggestion(self):
        from src.graph.state import AnalysisState, AnalysisType

        suggestion = AutomationSuggestion(
            pattern="test",
            confidence=0.8,
        )
        state = AnalysisState(
            analysis_type=AnalysisType.AUTOMATION_GAP_DETECTION,
            automation_suggestion=suggestion,
        )
        assert state.automation_suggestion is not None
        assert state.automation_suggestion.confidence == 0.8

    def test_state_none_suggestion(self):
        from src.graph.state import AnalysisState

        state = AnalysisState()
        assert state.automation_suggestion is None


class TestFormatBehavioralAnalysis:
    def test_format_with_suggestion(self):
        from unittest.mock import MagicMock

        from src.tools.agent_tools import _format_behavioral_analysis

        state = MagicMock()
        state.insights = [{
            "type": "automation_gap",
            "title": "Bedroom lights pattern",
            "description": "Lights off at 22:00",
            "confidence": 0.85,
            "impact": "high",
        }]
        state.recommendations = ["Automate bedroom lights"]
        state.automation_suggestion = AutomationSuggestion(
            pattern="Bedroom lights off at 22:00",
            entities=["light.bedroom"],
            proposed_trigger="time: 22:00",
            proposed_action="turn off light.bedroom",
            confidence=0.85,
        )

        result = _format_behavioral_analysis(state, "gaps", 168)
        assert "Automation Suggestion" in result
        assert "Bedroom lights" in result

    def test_format_without_suggestion(self):
        from unittest.mock import MagicMock

        from src.tools.agent_tools import _format_behavioral_analysis

        state = MagicMock()
        state.insights = [{
            "type": "behavioral_pattern",
            "title": "Peak usage at 8am",
            "description": "Most activity at 8am",
            "confidence": 0.6,
            "impact": "medium",
        }]
        state.recommendations = []
        state.automation_suggestion = None

        result = _format_behavioral_analysis(state, "behavior", 168)
        assert "Peak usage" in result
        assert "Automation Suggestion" not in result
