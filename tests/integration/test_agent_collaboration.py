"""Integration tests for DS -> Architect suggestion flow.

Tests the multi-agent collaboration where the Data Scientist
generates suggestions and the Architect creates proposals.
Constitution: Reliability & Quality.

TDD: T239 - DS -> Architect flow.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import AutomationSuggestion


class TestArchitectReceiveSuggestion:
    @pytest.mark.asyncio
    async def test_architect_receives_suggestion(self):
        """Architect should process a suggestion and generate a response."""
        suggestion = AutomationSuggestion(
            pattern="Bedroom lights off at 22:00 every night",
            entities=["light.bedroom"],
            proposed_trigger="time: 22:00",
            proposed_action="turn off light.bedroom",
            confidence=0.85,
            evidence={"occurrences": 7},
            source_insight_type="automation_gap",
        )

        # Mock the LLM response with a proposal
        mock_response = MagicMock()
        mock_response.content = """Based on the pattern, here's the automation:

```json
{
  "proposal": {
    "name": "Auto Bedroom Lights Off",
    "description": "Turn off bedroom lights at 22:00 nightly",
    "trigger": [{"platform": "time", "at": "22:00:00"}],
    "actions": [{"service": "light.turn_off", "target": {"entity_id": "light.bedroom"}}],
    "mode": "single"
  }
}
```"""

        with patch("src.agents.architect.get_llm") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_llm.return_value = mock_llm

            from src.agents.architect import ArchitectAgent

            architect = ArchitectAgent()
            architect._llm = mock_llm

            result = await architect.receive_suggestion(suggestion, session=None)

            assert "response" in result
            assert result.get("proposal_data") is not None
            assert result["proposal_data"]["name"] == "Auto Bedroom Lights Off"


class TestAnalyzeBehaviorTool:
    @pytest.mark.asyncio
    async def test_analyze_behavior_tool_exists(self):
        """The analyze_behavior tool should be in the tool list."""
        from src.tools.agent_tools import get_agent_tools

        tools = get_agent_tools()
        tool_names = [t.name for t in tools]
        assert "analyze_behavior" in tool_names

    @pytest.mark.asyncio
    async def test_propose_automation_tool_exists(self):
        """The propose_automation tool should be in the tool list."""
        from src.tools.agent_tools import get_agent_tools

        tools = get_agent_tools()
        tool_names = [t.name for t in tools]
        assert "propose_automation_from_insight" in tool_names
