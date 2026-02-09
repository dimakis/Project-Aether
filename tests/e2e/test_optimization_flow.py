"""E2E tests for the full optimization flow.

Tests the complete pipeline: analyze -> suggest -> propose -> approve.
Constitution: Reliability & Quality.

TDD: T241 - Full optimization flow.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import AnalysisType, AutomationSuggestion


class TestFullOptimizationFlow:
    @pytest.mark.asyncio
    async def test_analysis_to_suggestion(self):
        """DS should produce insights and suggestions from behavioral data."""
        from src.agents.data_scientist import DataScientistAgent
        from src.graph.state import AnalysisState
        from src.sandbox.runner import SandboxResult

        # mock HA with behavioral data
        mock_mcp = AsyncMock()
        mock_mcp.get_logbook = AsyncMock(return_value=[])
        mock_mcp.list_automations = AsyncMock(return_value=[])
        mock_mcp.get_history = AsyncMock(
            return_value={
                "entity_id": "sensor.test",
                "states": [],
                "count": 0,
            }
        )
        mock_mcp.list_entities = AsyncMock(return_value=[])

        # Mock LLM response with script
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='```python\nimport json\nresult = {"insights": [{"type": "automation_gap", "title": "Test Gap", "description": "Test", "confidence": 0.9, "impact": "high", "entities": ["light.test"]}], "recommendations": ["Automate this"]}\nprint(json.dumps(result))\n```'
            )
        )

        # Mock sandbox execution
        mock_sandbox_result = SandboxResult(
            success=True,
            exit_code=0,
            stdout='{"insights": [{"type": "automation_gap", "title": "Test Gap", "description": "Test pattern detected", "confidence": 0.9, "impact": "high", "entities": ["light.test"], "evidence": {"proposed_trigger": "time: 22:00", "proposed_action": "turn off"}}], "recommendations": ["Automate this pattern"]}',
            stderr="",
            duration_seconds=1.0,
            timed_out=False,
            policy_name="test",
        )

        agent = DataScientistAgent(ha_client=mock_mcp)
        agent._llm = mock_llm

        with patch.object(agent._sandbox, "run", return_value=mock_sandbox_result):
            state = AnalysisState(
                analysis_type=AnalysisType.AUTOMATION_GAP_DETECTION,
                time_range_hours=168,
            )
            updates = await agent.invoke(state)

        assert len(updates["insights"]) >= 1
        # Should generate a suggestion for high-confidence gap
        suggestion = updates.get("automation_suggestion")
        assert suggestion is not None
        assert isinstance(suggestion, AutomationSuggestion)
        assert suggestion.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_suggestion_to_proposal(self):
        """Architect should create a proposal from a DS suggestion."""
        suggestion = AutomationSuggestion(
            pattern="Test pattern",
            entities=["light.test"],
            proposed_trigger="time: 22:00",
            proposed_action="turn off light.test",
            confidence=0.9,
            source_insight_type="automation_gap",
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='```json\n{"proposal": {"name": "Test Automation", "description": "Auto test", "trigger": [{"platform": "time", "at": "22:00"}], "actions": [{"service": "light.turn_off"}], "mode": "single"}}\n```'
            )
        )

        with patch("src.agents.architect.get_llm", return_value=mock_llm):
            from src.agents.architect import ArchitectAgent

            architect = ArchitectAgent()
            architect._llm = mock_llm

            result = await architect.receive_suggestion(suggestion, session=None)

        assert result["proposal_data"] is not None
        assert result["proposal_data"]["name"] == "Test Automation"
