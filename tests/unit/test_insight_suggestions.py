"""Unit tests for automation suggestion formatting.

Tests that the Data Scientist's automation suggestions are correctly
generated and formatted in the agent tool responses.

TDD: T-MR08, T-MR09 - Insight automation suggestions.
"""

from unittest.mock import MagicMock

import pytest

from src.agents.data_scientist import DataScientistAgent
from src.graph.state import AnalysisState, AnalysisType, AgentRole, AutomationSuggestion


class TestGenerateAutomationSuggestion:
    """Tests for DataScientistAgent._generate_automation_suggestion."""

    def _make_agent(self):
        """Create a DataScientistAgent with mock MCP."""
        return DataScientistAgent(mcp_client=MagicMock())

    def test_no_insights_returns_none(self):
        """No insights should produce no suggestion."""
        agent = self._make_agent()
        assert agent._generate_automation_suggestion([]) is None

    def test_low_confidence_insight_returns_none(self):
        """Low confidence insight should not produce suggestion."""
        agent = self._make_agent()
        insights = [{
            "type": "energy_optimization",
            "title": "Test",
            "description": "Low confidence finding",
            "confidence": 0.5,
            "impact": "high",
        }]
        assert agent._generate_automation_suggestion(insights) is None

    def test_low_impact_insight_returns_none(self):
        """Low impact insight should not produce suggestion."""
        agent = self._make_agent()
        insights = [{
            "type": "energy_optimization",
            "title": "Test",
            "description": "High confidence but low impact",
            "confidence": 0.95,
            "impact": "low",
        }]
        assert agent._generate_automation_suggestion(insights) is None

    def test_high_confidence_high_impact_energy_optimization(self):
        """High confidence + high impact energy optimization should suggest scheduling."""
        agent = self._make_agent()
        insights = [{
            "type": "energy_optimization",
            "title": "Peak Hour Waste",
            "description": "HVAC running at full power during peak rates",
            "confidence": 0.92,
            "impact": "high",
        }]
        suggestion = agent._generate_automation_suggestion(insights)
        assert suggestion is not None
        assert isinstance(suggestion, AutomationSuggestion)
        assert "Peak Hour Waste" in suggestion.pattern
        assert "off-peak" in suggestion.proposed_trigger

    def test_high_confidence_critical_anomaly_detection(self):
        """High confidence + critical anomaly should suggest alert automation."""
        agent = self._make_agent()
        insights = [{
            "type": "anomaly_detection",
            "title": "Unusual Spike",
            "description": "Power consumption spike at 3 AM",
            "confidence": 0.88,
            "impact": "critical",
        }]
        suggestion = agent._generate_automation_suggestion(insights)
        assert suggestion is not None
        assert isinstance(suggestion, AutomationSuggestion)
        assert "Unusual Spike" in suggestion.pattern
        assert "alert" in suggestion.proposed_action.lower() or "corrective" in suggestion.proposed_action.lower()

    def test_high_confidence_usage_pattern(self):
        """High confidence + high impact usage pattern should suggest optimization."""
        agent = self._make_agent()
        insights = [{
            "type": "usage_pattern",
            "title": "Consistent Nighttime Waste",
            "description": "Lights left on from 1-6 AM daily",
            "confidence": 0.95,
            "impact": "high",
        }]
        suggestion = agent._generate_automation_suggestion(insights)
        assert suggestion is not None
        assert isinstance(suggestion, AutomationSuggestion)
        assert "Consistent Nighttime Waste" in suggestion.pattern
        assert suggestion.source_insight_type == "usage_pattern"

    def test_generic_high_confidence_type(self):
        """Unknown insight type with high confidence should produce generic suggestion."""
        agent = self._make_agent()
        insights = [{
            "type": "custom",
            "title": "Custom Finding",
            "description": "Something important was found",
            "confidence": 0.85,
            "impact": "high",
        }]
        suggestion = agent._generate_automation_suggestion(insights)
        assert suggestion is not None
        assert isinstance(suggestion, AutomationSuggestion)
        assert "Custom Finding" in suggestion.pattern

    def test_first_qualifying_insight_used(self):
        """Only the first qualifying insight should be used for suggestion."""
        agent = self._make_agent()
        insights = [
            {
                "type": "energy_optimization",
                "title": "Low Confidence",
                "description": "Not qualifying",
                "confidence": 0.3,
                "impact": "high",
            },
            {
                "type": "anomaly_detection",
                "title": "First Qualifying",
                "description": "This one qualifies",
                "confidence": 0.9,
                "impact": "critical",
            },
            {
                "type": "energy_optimization",
                "title": "Second Qualifying",
                "description": "This also qualifies but should be ignored",
                "confidence": 0.95,
                "impact": "high",
            },
        ]
        suggestion = agent._generate_automation_suggestion(insights)
        assert suggestion is not None
        assert "First Qualifying" in suggestion.pattern
        assert "Second Qualifying" not in suggestion.pattern

    def test_cost_saving_type_suggests_scheduling(self):
        """Cost saving insight should suggest scheduling automation."""
        agent = self._make_agent()
        insights = [{
            "type": "cost_saving",
            "title": "Rate Arbitrage Opportunity",
            "description": "Could save $50/month by shifting load",
            "confidence": 0.91,
            "impact": "high",
        }]
        suggestion = agent._generate_automation_suggestion(insights)
        assert suggestion is not None
        assert isinstance(suggestion, AutomationSuggestion)
        assert "Rate Arbitrage Opportunity" in suggestion.pattern
        assert "off-peak" in suggestion.proposed_trigger


class TestFormatEnergyAnalysisWithSuggestion:
    """Tests for _format_energy_analysis including automation suggestions."""

    def test_suggestion_appended_to_output(self):
        """Automation suggestion should be appended to formatted output."""
        from src.tools.agent_tools import _format_energy_analysis

        state = MagicMock()
        state.insights = [{
            "type": "energy_optimization",
            "title": "Test Finding",
            "description": "Test description",
            "confidence": 0.9,
            "impact": "high",
        }]
        state.recommendations = ["Save energy"]
        state.entity_ids = ["sensor.power"]
        state.automation_suggestion = AutomationSuggestion(
            pattern="Schedule devices during off-peak hours",
            entities=["sensor.power"],
            proposed_trigger="time: off-peak hours",
            proposed_action="Schedule energy-intensive devices",
            confidence=0.9,
        )

        result = _format_energy_analysis(state, "energy_optimization", 24)
        assert "Data Scientist Suggestion" in result
        assert "off-peak hours" in result
        assert "Would you like me to design an automation" in result

    def test_no_suggestion_no_extra_content(self):
        """Without suggestion, no suggestion section should appear."""
        from src.tools.agent_tools import _format_energy_analysis

        state = MagicMock()
        state.insights = [{
            "type": "energy_optimization",
            "title": "Test Finding",
            "description": "Test",
            "confidence": 0.5,
            "impact": "medium",
        }]
        state.recommendations = []
        state.entity_ids = ["sensor.power"]
        state.automation_suggestion = None

        result = _format_energy_analysis(state, "energy_optimization", 24)
        assert "Data Scientist Suggestion" not in result


class TestFormatDiagnosticResultsWithSuggestion:
    """Tests for _format_diagnostic_results including automation suggestions."""

    def test_suggestion_appended_to_diagnostic_output(self):
        """Automation suggestion should be appended to diagnostic output."""
        from src.tools.agent_tools import _format_diagnostic_results

        state = MagicMock()
        state.insights = [{
            "type": "diagnostic",
            "title": "Integration Failure",
            "description": "Zigbee integration dropping",
            "confidence": 0.85,
            "impact": "critical",
        }]
        state.recommendations = ["Restart Zigbee"]
        state.automation_suggestion = AutomationSuggestion(
            pattern="Alert when Zigbee pattern recurs",
            entities=["sensor.zigbee"],
            proposed_trigger="state change pattern",
            proposed_action="Alert when pattern recurs",
            confidence=0.85,
        )

        result = _format_diagnostic_results(
            state, ["sensor.zigbee"], 72,
        )
        assert "Data Scientist Suggestion" in result
        assert "Zigbee pattern recurs" in result
