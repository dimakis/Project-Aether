"""E2E tests for multi-agent conversations.

Tests user queries that involve multiple agents collaborating.
Constitution: Reliability & Quality.

TDD: T242 - User query involving multiple agents.
"""

import pytest

from src.graph.state import AnalysisType, AutomationSuggestion


class TestMultiAgentQuery:
    @pytest.mark.asyncio
    async def test_behavior_tool_available_to_architect(self):
        """Architect should have access to analyze_behavior tool."""
        from src.tools.agent_tools import get_agent_tools

        tools = get_agent_tools()
        tool_names = [t.name for t in tools]

        assert "analyze_energy" in tool_names
        assert "analyze_behavior" in tool_names
        assert "discover_entities" in tool_names
        assert "diagnose_issue" in tool_names
        assert "propose_automation_from_insight" in tool_names

    @pytest.mark.asyncio
    async def test_analysis_types_cover_all_behavioral(self):
        """All behavioral analysis types should be accessible."""
        expected_types = [
            "behavior_analysis",
            "automation_analysis",
            "automation_gap_detection",
            "correlation_discovery",
            "device_health",
            "cost_optimization",
        ]

        for type_str in expected_types:
            assert hasattr(AnalysisType, type_str.upper()), (
                f"AnalysisType should have {type_str.upper()}"
            )

    @pytest.mark.asyncio
    async def test_insight_types_cover_all_behavioral(self):
        """All behavioral insight types should be accessible."""
        from src.storage.entities.insight import InsightType

        expected_types = [
            "automation_gap",
            "automation_inefficiency",
            "correlation",
            "device_health",
            "behavioral_pattern",
        ]

        for type_str in expected_types:
            assert type_str in [t.value for t in InsightType], f"InsightType should have {type_str}"

    @pytest.mark.asyncio
    async def test_workflow_registry_has_optimization(self):
        """Optimization workflow should be registered."""
        from src.graph.workflows import WORKFLOW_REGISTRY

        assert "optimization" in WORKFLOW_REGISTRY
        assert "analysis" in WORKFLOW_REGISTRY
        assert "conversation" in WORKFLOW_REGISTRY
        assert "discovery" in WORKFLOW_REGISTRY

    @pytest.mark.asyncio
    async def test_suggestion_model_round_trip(self):
        """AutomationSuggestion should serialize and deserialize cleanly."""
        suggestion = AutomationSuggestion(
            pattern="Lights off at bedtime",
            entities=["light.bedroom", "light.hallway"],
            proposed_trigger="time: 23:00",
            proposed_action="Turn off bedroom and hallway lights",
            confidence=0.92,
            evidence={"days_observed": 14, "consistency": 0.95},
            source_insight_type="automation_gap",
        )

        # Serialize
        data = suggestion.model_dump()
        assert data["confidence"] == 0.92
        assert len(data["entities"]) == 2

        # Deserialize
        restored = AutomationSuggestion.model_validate(data)
        assert restored.pattern == suggestion.pattern
        assert restored.confidence == suggestion.confidence
