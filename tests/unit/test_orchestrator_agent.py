"""Tests for OrchestratorAgent intent classification and routing (Feature 30).

Covers:
- Agent instantiation and role
- Intent classification with mocked LLM
- Routing to the correct domain agent
- Fallback to Knowledge agent when no match
- Clarification request when confidence is low
- Available agents discovery from registry data
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from src.graph.state import AgentRole, ConversationState


class TestOrchestratorInit:
    """OrchestratorAgent basic instantiation."""

    def test_role_is_orchestrator(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()
        assert agent.role == AgentRole.ORCHESTRATOR

    def test_name_defaults_to_orchestrator(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()
        assert agent.name == "Orchestrator"

    def test_accepts_model_name(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent(model_name="gpt-4o-mini")
        assert agent.model_name == "gpt-4o-mini"


class TestIntentClassification:
    """OrchestratorAgent.classify_intent() routes to the right agent."""

    @pytest.fixture()
    def agent(self):
        from src.agents.orchestrator import OrchestratorAgent

        return OrchestratorAgent(model_name="test-model")

    @pytest.fixture()
    def available_agents(self):
        return [
            {
                "name": "architect",
                "domain": "home",
                "description": "Home automation design and control",
                "intent_patterns": ["home_automation", "device_control", "lights"],
                "capabilities": ["control_devices", "create_automations"],
            },
            {
                "name": "knowledge",
                "domain": "knowledge",
                "description": "General knowledge and questions",
                "intent_patterns": ["general_question", "explain", "trivia"],
                "capabilities": ["answer_questions"],
            },
            {
                "name": "data_scientist",
                "domain": "analytics",
                "description": "Energy and usage analysis",
                "intent_patterns": ["energy_analysis", "usage_patterns"],
                "capabilities": ["analyze_data", "generate_reports"],
            },
        ]

    @pytest.mark.asyncio()
    async def test_classifies_home_intent(self, agent, available_agents):
        mock_response = MagicMock()
        mock_response.content = '{"agent": "architect", "confidence": 0.95, "reasoning": "User wants to control lights"}'

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_classification_llm", return_value=mock_llm):
            result = await agent.classify_intent("turn off the kitchen lights", available_agents)

        assert result["agent"] == "architect"
        assert result["confidence"] >= 0.9

    @pytest.mark.asyncio()
    async def test_classifies_knowledge_intent(self, agent, available_agents):
        mock_response = MagicMock()
        mock_response.content = (
            '{"agent": "knowledge", "confidence": 0.92, "reasoning": "General knowledge question"}'
        )

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_classification_llm", return_value=mock_llm):
            result = await agent.classify_intent("what is the capital of France?", available_agents)

        assert result["agent"] == "knowledge"

    @pytest.mark.asyncio()
    async def test_low_confidence_returns_clarification(self, agent, available_agents):
        mock_response = MagicMock()
        mock_response.content = (
            '{"agent": "architect", "confidence": 0.3, "reasoning": "Ambiguous request"}'
        )

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_classification_llm", return_value=mock_llm):
            result = await agent.classify_intent("set a timer", available_agents)

        assert result["needs_clarification"] is True

    @pytest.mark.asyncio()
    async def test_fallback_to_knowledge_on_no_match(self, agent, available_agents):
        mock_response = MagicMock()
        mock_response.content = (
            '{"agent": "unknown", "confidence": 0.4, "reasoning": "No matching agent"}'
        )

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_classification_llm", return_value=mock_llm):
            result = await agent.classify_intent("tell me a joke", available_agents)

        assert result["agent"] == "knowledge"

    @pytest.mark.asyncio()
    async def test_malformed_llm_response_falls_back(self, agent, available_agents):
        mock_response = MagicMock()
        mock_response.content = "I think you should use the architect"

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_classification_llm", return_value=mock_llm):
            result = await agent.classify_intent("turn on the lights", available_agents)

        assert result["agent"] == "knowledge"
        assert result["confidence"] < 0.5


class TestOrchestratorInvoke:
    """OrchestratorAgent.invoke() updates state with routing decision."""

    @pytest.mark.asyncio()
    async def test_invoke_sets_active_agent(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent(model_name="test")
        state = ConversationState(
            messages=[HumanMessage(content="turn off the lights")],
        )

        mock_classification = {
            "agent": "architect",
            "confidence": 0.95,
            "reasoning": "Home automation request",
            "needs_clarification": False,
        }

        with (
            patch.object(
                agent, "classify_intent", new_callable=AsyncMock, return_value=mock_classification
            ),
            patch.object(agent, "_get_available_agents", new_callable=AsyncMock, return_value=[]),
        ):
            result = await agent.invoke(state)

        assert result["active_agent"] == "architect"

    @pytest.mark.asyncio()
    async def test_invoke_returns_current_agent_orchestrator(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent(model_name="test")
        state = ConversationState(
            messages=[HumanMessage(content="turn off the lights")],
        )

        mock_classification = {
            "agent": "architect",
            "confidence": 0.95,
            "reasoning": "Home automation request",
            "needs_clarification": False,
        }

        with (
            patch.object(
                agent, "classify_intent", new_callable=AsyncMock, return_value=mock_classification
            ),
            patch.object(agent, "_get_available_agents", new_callable=AsyncMock, return_value=[]),
        ):
            result = await agent.invoke(state)

        assert result["current_agent"] == AgentRole.ORCHESTRATOR
