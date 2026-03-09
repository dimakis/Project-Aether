"""Unit tests for KnowledgeAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.state import AgentRole, ConversationState


class TestKnowledgeAgent:
    @pytest.mark.asyncio
    async def test_invoke_returns_ai_message(self):
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="42"))

        with (
            patch("src.agents.knowledge.get_llm", return_value=mock_llm),
            patch("src.agents.knowledge.load_prompt_for_agent", return_value="You are helpful."),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            from src.agents.knowledge import KnowledgeAgent

            agent = KnowledgeAgent()
            result = await agent.invoke(
                ConversationState(messages=[HumanMessage(content="What is 6*7?")])
            )

        assert "messages" in result
        assert result["messages"][0].content == "42"
        assert result["current_agent"] == AgentRole.KNOWLEDGE

    @pytest.mark.asyncio
    async def test_invoke_falls_back_to_default_prompt(self):
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="I don't know"))

        with (
            patch("src.agents.knowledge.get_llm", return_value=mock_llm),
            patch(
                "src.agents.knowledge.load_prompt_for_agent",
                side_effect=FileNotFoundError("no prompt"),
            ),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            from src.agents.knowledge import KnowledgeAgent

            agent = KnowledgeAgent()
            result = await agent.invoke(
                ConversationState(messages=[HumanMessage(content="obscure question")])
            )

        assert "messages" in result
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "knowledgeable AI assistant" in call_args[0].content
