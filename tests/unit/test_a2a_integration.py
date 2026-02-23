"""Integration tests for A2A state serialization round-trip (Phase 3).

Verifies that state survives the full pack -> DataPart -> unpack cycle,
including LangChain message serialization.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.a2a_service import pack_state_to_data, unpack_data_to_state_updates
from src.graph.state import AnalysisState, ConversationState


class TestStateRoundTrip:
    """State data survives pack -> unpack without loss."""

    def test_conversation_state_round_trip(self):
        state = ConversationState(
            conversation_id="conv-123",
            channel="api",
            active_agent="architect",
            user_intent="turn on the lights",
        )
        packed = pack_state_to_data(state)
        unpacked = unpack_data_to_state_updates(packed)

        assert unpacked["conversation_id"] == "conv-123"
        assert unpacked["channel"] == "api"
        assert unpacked["active_agent"] == "architect"
        assert unpacked["user_intent"] == "turn on the lights"

    def test_analysis_state_round_trip(self):
        state = AnalysisState(
            run_id="run-456",
        )
        packed = pack_state_to_data(state)
        unpacked = unpack_data_to_state_updates(packed)

        assert unpacked["run_id"] == "run-456"

    def test_empty_state_round_trip(self):
        state = ConversationState()
        packed = pack_state_to_data(state)
        unpacked = unpack_data_to_state_updates(packed)

        assert "conversation_id" in unpacked
        assert "status" in unpacked


class TestLangChainMessageSerialization:
    """LangChain messages survive pack -> dumpd -> load round-trip."""

    def test_human_message_round_trip(self):
        from langchain_core.load import load

        state = ConversationState(
            messages=[HumanMessage(content="hello world")],
        )
        packed = pack_state_to_data(state)

        assert "_lc_messages" in packed
        assert len(packed["_lc_messages"]) == 1

        restored = load(packed["_lc_messages"][0])
        assert isinstance(restored, HumanMessage)
        assert restored.content == "hello world"

    def test_multi_message_round_trip(self):
        from langchain_core.load import load

        state = ConversationState(
            messages=[
                SystemMessage(content="You are helpful"),
                HumanMessage(content="hi"),
                AIMessage(content="Hello! How can I help?"),
            ],
        )
        packed = pack_state_to_data(state)
        assert len(packed["_lc_messages"]) == 3

        restored = [load(m) for m in packed["_lc_messages"]]
        assert isinstance(restored[0], SystemMessage)
        assert isinstance(restored[1], HumanMessage)
        assert isinstance(restored[2], AIMessage)
        assert restored[2].content == "Hello! How can I help?"

    def test_empty_messages_no_lc_key(self):
        state = ConversationState(messages=[])
        packed = pack_state_to_data(state)
        assert "_lc_messages" not in packed

    def test_lc_messages_excluded_from_unpack(self):
        packed = {
            "conversation_id": "conv-1",
            "_lc_messages": [{"type": "human", "content": "hi"}],
        }
        unpacked = unpack_data_to_state_updates(packed)
        assert "_lc_messages" not in unpacked
        assert unpacked["conversation_id"] == "conv-1"


class TestErrorHandling:
    """A2A client handles error scenarios gracefully."""

    @pytest.mark.asyncio()
    async def test_client_raises_on_connection_refused(self):
        from src.agents.a2a_client import A2AClientError, A2ARemoteClient

        client = A2ARemoteClient(
            base_url="http://127.0.0.1:19999",
            timeout=1.0,
        )
        state = ConversationState(messages=[HumanMessage(content="test")])

        with pytest.raises(A2AClientError):
            await client.invoke(state)

    def test_unpack_handles_empty_dict(self):
        result = unpack_data_to_state_updates({})
        assert result == {}

    def test_pack_handles_state_with_none_fields(self):
        state = ConversationState(
            channel=None,
            active_agent=None,
        )
        packed = pack_state_to_data(state)
        assert packed["channel"] is None
        assert packed["active_agent"] is None
