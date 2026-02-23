"""Tests for A2A service wrapper (Phase 3).

Covers:
- create_a2a_service() returns a FastAPI app
- Agent Card is served at /.well-known/agent.json
- Health and readiness endpoints work
- AetherAgentExecutor wraps BaseAgent.invoke() correctly
- State serialization: Pydantic state -> DataPart -> state updates
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage


class TestCreateA2AService:
    """create_a2a_service() produces a working FastAPI app."""

    def test_returns_fastapi_app(self):
        from src.agents.a2a_service import create_a2a_service

        app = create_a2a_service(
            agent_name="test-agent",
            agent_description="A test agent",
            agent_skills=[{"id": "test", "name": "Test", "description": "Testing"}],
        )
        from starlette.applications import Starlette

        assert isinstance(app, Starlette)

    def test_health_endpoint(self):
        from src.agents.a2a_service import create_a2a_service

        app = create_a2a_service(
            agent_name="test-agent",
            agent_description="Test",
            agent_skills=[],
        )
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/health" in routes

    def test_agent_card_endpoint(self):
        from src.agents.a2a_service import create_a2a_service

        app = create_a2a_service(
            agent_name="test-agent",
            agent_description="Test",
            agent_skills=[],
        )
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/.well-known/agent-card.json" in routes


class TestAetherAgentExecutor:
    """AetherAgentExecutor bridges BaseAgent to A2A AgentExecutor."""

    @pytest.mark.asyncio()
    async def test_execute_calls_agent_invoke(self):
        from a2a.server.agent_execution.context import RequestContext
        from a2a.server.events import InMemoryQueueManager
        from a2a.types import (
            Message,
            Part,
            TextPart,
        )

        from src.agents.a2a_service import AetherAgentExecutor

        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(
            return_value={"active_agent": "architect", "user_intent": "test"}
        )

        executor = AetherAgentExecutor(mock_agent)

        context = MagicMock(spec=RequestContext)
        context.message = Message(
            role="user",
            parts=[Part(root=TextPart(text="turn on the lights"))],
            message_id="msg-1",
        )
        context.get_user_input.return_value = "turn on the lights"
        context.task_id = "task-1"
        context.context_id = "ctx-1"

        queue_manager = InMemoryQueueManager()
        queue = await queue_manager.create_or_tap("task-1")

        await executor.execute(context, queue)

        mock_agent.invoke.assert_called_once()


class TestStateSerializer:
    """State serialization round-trip: Pydantic state -> DataPart -> dict."""

    def test_pack_state_to_data_part(self):
        from src.agents.a2a_service import pack_state_to_data
        from src.graph.state import ConversationState

        state = ConversationState(
            conversation_id="conv-1",
            channel="api",
            active_agent="architect",
        )
        data = pack_state_to_data(state)
        assert isinstance(data, dict)
        assert data["conversation_id"] == "conv-1"
        assert data["channel"] == "api"

    def test_pack_state_includes_messages_as_dumpd(self):
        from src.agents.a2a_service import pack_state_to_data
        from src.graph.state import ConversationState

        state = ConversationState(
            messages=[HumanMessage(content="hello")],
        )
        data = pack_state_to_data(state)
        assert "_lc_messages" in data
        assert len(data["_lc_messages"]) == 1

    def test_unpack_data_to_state_updates(self):
        from src.agents.a2a_service import unpack_data_to_state_updates

        data = {
            "active_agent": "architect",
            "user_intent": "turn on lights",
            "current_agent": "orchestrator",
        }
        updates = unpack_data_to_state_updates(data)
        assert updates["active_agent"] == "architect"
        assert updates["user_intent"] == "turn on lights"
