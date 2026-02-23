"""Tests for AetherAgentExecutor full state handling (Phase 4).

The executor must accept full state via DataPart, not just text.
This enables multi-turn conversations and AnalysisState workflows
across container boundaries.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage

from src.agents.a2a_service import pack_state_to_data


class TestExtractStateFromContext:
    """_extract_state_from_context checks DataPart first, falls back to text."""

    def test_extracts_full_state_from_data_part(self):
        from a2a.types import DataPart, Message, Part

        from src.agents.a2a_service import _extract_state_from_context
        from src.graph.state import ConversationState

        original = ConversationState(
            conversation_id="conv-123",
            channel="api",
            active_agent="architect",
            messages=[HumanMessage(content="turn on lights")],
        )
        packed = pack_state_to_data(original)

        context = MagicMock()
        context.message = Message(
            role="user",
            parts=[Part(root=DataPart(data=packed))],
            message_id="msg-1",
        )

        state = _extract_state_from_context(context, "ConversationState")
        assert state.conversation_id == "conv-123"
        assert state.channel == "api"
        assert state.active_agent == "architect"
        assert len(state.messages) == 1
        assert isinstance(state.messages[0], HumanMessage)

    def test_extracts_analysis_state_from_data_part(self):
        from a2a.types import DataPart, Message, Part

        from src.agents.a2a_service import _extract_state_from_context
        from src.graph.state import AnalysisState

        original = AnalysisState(run_id="run-456")
        packed = pack_state_to_data(original)

        context = MagicMock()
        context.message = Message(
            role="user",
            parts=[Part(root=DataPart(data=packed))],
            message_id="msg-2",
        )

        state = _extract_state_from_context(context, "AnalysisState")
        assert state.run_id == "run-456"

    def test_falls_back_to_text_when_no_data_part(self):
        from a2a.types import Message, Part, TextPart

        from src.agents.a2a_service import _extract_state_from_context

        context = MagicMock()
        context.message = Message(
            role="user",
            parts=[Part(root=TextPart(text="hello world"))],
            message_id="msg-3",
        )

        state = _extract_state_from_context(context, "ConversationState")
        assert len(state.messages) == 1
        assert state.messages[0].content == "hello world"

    def test_restores_langchain_messages(self):
        from a2a.types import DataPart, Message, Part

        from src.agents.a2a_service import _extract_state_from_context
        from src.graph.state import ConversationState

        original = ConversationState(
            messages=[
                HumanMessage(content="hi"),
                AIMessage(content="hello back"),
            ],
        )
        packed = pack_state_to_data(original)

        context = MagicMock()
        context.message = Message(
            role="user",
            parts=[Part(root=DataPart(data=packed))],
            message_id="msg-4",
        )

        state = _extract_state_from_context(context, "ConversationState")
        assert len(state.messages) == 2
        assert isinstance(state.messages[0], HumanMessage)
        assert isinstance(state.messages[1], AIMessage)
        assert state.messages[1].content == "hello back"
