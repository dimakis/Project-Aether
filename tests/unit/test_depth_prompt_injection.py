"""Unit tests for depth prompt injection into analyst prompts.

Tests A1: Verify that _build_analysis_prompt appends the depth fragment
for each analyst, and that the BaseAnalyst helper works correctly.
"""

from __future__ import annotations


class TestBaseAnalystDepthAppend:
    """Test the shared _append_depth_fragment helper in BaseAnalyst."""

    def test_appends_quick_fragment(self):
        from src.agents.base_analyst import BaseAnalyst

        result = BaseAnalyst._append_depth_fragment("Base prompt.", "quick")
        assert "Quick" in result
        assert "Base prompt." in result

    def test_appends_deep_fragment(self):
        from src.agents.base_analyst import BaseAnalyst

        result = BaseAnalyst._append_depth_fragment("Base prompt.", "deep")
        assert "Deep" in result
        assert "/workspace/output/" in result

    def test_standard_appends_fragment(self):
        from src.agents.base_analyst import BaseAnalyst

        result = BaseAnalyst._append_depth_fragment("Base prompt.", "standard")
        assert "Standard" in result

    def test_unknown_depth_returns_original(self):
        from src.agents.base_analyst import BaseAnalyst

        result = BaseAnalyst._append_depth_fragment("Base prompt.", "unknown")
        assert result == "Base prompt."


class TestEnergyAnalystDepthInjection:
    """Test that EnergyAnalyst injects depth fragment."""

    def test_default_prompt_includes_depth(self):
        from src.agents.energy_analyst import EnergyAnalyst
        from src.graph.state import AnalysisState, AnalysisType

        analyst = EnergyAnalyst.__new__(EnergyAnalyst)
        state = AnalysisState(
            analysis_type=AnalysisType.CUSTOM,
            depth="deep",
        )
        data = {"entity_count": 5, "total_kwh": 100.0}

        prompt = analyst._build_analysis_prompt(state, data)
        assert "Deep" in prompt

    def test_quick_depth_no_charts(self):
        from src.agents.energy_analyst import EnergyAnalyst
        from src.graph.state import AnalysisState, AnalysisType

        analyst = EnergyAnalyst.__new__(EnergyAnalyst)
        state = AnalysisState(
            analysis_type=AnalysisType.CUSTOM,
            depth="quick",
        )
        data = {"entity_count": 5, "total_kwh": 100.0}

        prompt = analyst._build_analysis_prompt(state, data)
        assert "Quick" in prompt


class TestBehavioralAnalystDepthInjection:
    """Test that BehavioralAnalyst injects depth fragment."""

    def test_prompt_includes_depth(self):
        from src.agents.behavioral_analyst import BehavioralAnalyst
        from src.graph.state import AnalysisState, AnalysisType

        analyst = BehavioralAnalyst.__new__(BehavioralAnalyst)
        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
            depth="deep",
        )
        data = {"entity_count": 10}

        prompt = analyst._build_analysis_prompt(state, data)
        assert "Deep" in prompt


class TestDiagnosticAnalystDepthInjection:
    """Test that DiagnosticAnalyst injects depth fragment."""

    def test_prompt_includes_depth(self):
        from src.agents.diagnostic_analyst import DiagnosticAnalyst
        from src.graph.state import AnalysisState, AnalysisType

        analyst = DiagnosticAnalyst.__new__(DiagnosticAnalyst)
        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            depth="deep",
        )
        data = {}

        prompt = analyst._build_analysis_prompt(state, data)
        assert "Deep" in prompt


class TestDataScientistDepthInjection:
    """Test that DataScientistAgent injects depth fragment."""

    def test_custom_prompt_includes_depth(self):
        from src.agents.data_scientist import DataScientistAgent
        from src.graph.state import AnalysisState, AnalysisType

        agent = DataScientistAgent.__new__(DataScientistAgent)
        state = AnalysisState(
            analysis_type=AnalysisType.CUSTOM,
            custom_query="test",
            depth="deep",
        )
        data = {"entity_count": 5, "total_kwh": 100.0}

        prompt = agent._build_analysis_prompt(state, data)
        assert "Deep" in prompt
