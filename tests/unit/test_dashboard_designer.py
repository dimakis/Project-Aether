"""Tests for the Dashboard Designer agent.

Validates the conversational agent that generates Lovelace dashboard
configurations by consulting DS team specialists.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDashboardDesignerInit:
    """Initialization tests for DashboardDesignerAgent."""

    def test_role_is_dashboard_designer(self):
        """Agent has the DASHBOARD_DESIGNER role."""
        from src.agents.dashboard_designer import DashboardDesignerAgent
        from src.graph.state import AgentRole

        agent = DashboardDesignerAgent()
        assert agent.role == AgentRole.DASHBOARD_DESIGNER

    def test_name_is_dashboard_designer(self):
        """Agent name is 'Dashboard Designer'."""
        from src.agents.dashboard_designer import DashboardDesignerAgent

        agent = DashboardDesignerAgent()
        assert agent.name == "Dashboard Designer"

    def test_inherits_base_agent(self):
        """Agent inherits from BaseAgent."""
        from src.agents import BaseAgent
        from src.agents.dashboard_designer import DashboardDesignerAgent

        agent = DashboardDesignerAgent()
        assert isinstance(agent, BaseAgent)

    def test_custom_model_name(self):
        """Can override model name at construction."""
        from src.agents.dashboard_designer import DashboardDesignerAgent

        agent = DashboardDesignerAgent(model_name="gpt-4o")
        assert agent.model_name == "gpt-4o"


class TestDashboardDesignerTools:
    """Verify the agent's tool configuration."""

    def test_has_dashboard_tools(self):
        """Agent's tools include dashboard-specific tools."""
        from src.agents.dashboard_designer import DashboardDesignerAgent

        agent = DashboardDesignerAgent()
        tool_names = [t.name for t in agent.tools]
        assert "generate_dashboard_yaml" in tool_names
        assert "validate_dashboard_yaml" in tool_names
        assert "list_dashboards" in tool_names


class TestDashboardDesignerInvoke:
    """Tests for the invoke method."""

    @pytest.fixture(autouse=True)
    def _patch_dependencies(self):
        """Patch LLM and HA client for tests."""
        mock_llm = MagicMock()
        mock_ai_msg = MagicMock()
        mock_ai_msg.content = "Here's a dashboard design for your energy monitoring."
        mock_ai_msg.tool_calls = []
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=mock_ai_msg)

        with patch("src.agents.dashboard_designer.get_llm", return_value=mock_llm):
            self.mock_llm = mock_llm
            yield

    @pytest.mark.asyncio
    async def test_invoke_returns_messages(self):
        """invoke returns a dict with messages key."""
        from src.agents.dashboard_designer import DashboardDesignerAgent
        from src.graph.state import DashboardState

        agent = DashboardDesignerAgent()
        state = DashboardState(user_intent="design energy dashboard")

        # Add a user message to the state
        from langchain_core.messages import HumanMessage

        state.messages = [HumanMessage(content="Create an energy dashboard")]

        result = await agent.invoke(state)
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_invoke_includes_system_prompt(self):
        """invoke sends the system prompt to the LLM."""
        from langchain_core.messages import HumanMessage

        from src.agents.dashboard_designer import DashboardDesignerAgent
        from src.graph.state import DashboardState

        agent = DashboardDesignerAgent()
        state = DashboardState()
        state.messages = [HumanMessage(content="Design a dashboard")]

        await agent.invoke(state)

        # The LLM should have been called with messages
        assert self.mock_llm.ainvoke.called
        call_args = self.mock_llm.ainvoke.call_args[0][0]
        # First message should be the system prompt
        assert any("Dashboard Designer" in str(m) or "Lovelace" in str(m) for m in call_args)
