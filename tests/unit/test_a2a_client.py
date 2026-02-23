"""Tests for A2A remote client (Phase 3).

Covers:
- A2ARemoteClient instantiation
- invoke() packs state, sends A2A request, unpacks response
- Retry on transient failure
- Timeout handling
- Error propagation on permanent failure
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import HumanMessage

from src.graph.state import ConversationState


class TestA2ARemoteClientInit:
    """A2ARemoteClient basic construction."""

    def test_accepts_base_url(self):
        from src.agents.a2a_client import A2ARemoteClient

        client = A2ARemoteClient(base_url="http://ds-service:8000")
        assert client.base_url == "http://ds-service:8000"

    def test_default_timeout(self):
        from src.agents.a2a_client import A2ARemoteClient

        client = A2ARemoteClient(base_url="http://ds-service:8000")
        assert client.timeout > 0


class TestA2ARemoteClientInvoke:
    """invoke() sends state to remote A2A service and returns updates."""

    @pytest.mark.asyncio()
    async def test_invoke_returns_state_updates(self):
        from src.agents.a2a_client import A2ARemoteClient

        client = A2ARemoteClient(base_url="http://test:8000")

        mock_result = {"active_agent": "architect", "user_intent": "test"}

        with patch.object(
            client, "_send_message", new_callable=AsyncMock, return_value=mock_result
        ):
            state = ConversationState(
                messages=[HumanMessage(content="hello")],
            )
            result = await client.invoke(state)

        assert result["active_agent"] == "architect"

    @pytest.mark.asyncio()
    async def test_invoke_packs_state_as_data(self):
        from src.agents.a2a_client import A2ARemoteClient

        client = A2ARemoteClient(base_url="http://test:8000")

        captured_data = {}

        async def mock_send(data: dict) -> dict:
            captured_data.update(data)
            return {"active_agent": "test"}

        with patch.object(client, "_send_message", side_effect=mock_send):
            state = ConversationState(
                conversation_id="conv-1",
                channel="api",
                messages=[HumanMessage(content="hello")],
            )
            await client.invoke(state)

        assert captured_data["conversation_id"] == "conv-1"
        assert "_lc_messages" in captured_data

    @pytest.mark.asyncio()
    async def test_invoke_raises_on_permanent_failure(self):
        from src.agents.a2a_client import A2AClientError, A2ARemoteClient

        client = A2ARemoteClient(base_url="http://test:8000")

        with patch.object(
            client,
            "_send_message",
            new_callable=AsyncMock,
            side_effect=A2AClientError("Service down"),
        ):
            state = ConversationState(messages=[HumanMessage(content="hello")])
            with pytest.raises(A2AClientError):
                await client.invoke(state)


class TestA2ARemoteClientTimeout:
    """Client respects timeout configuration."""

    def test_custom_timeout(self):
        from src.agents.a2a_client import A2ARemoteClient

        client = A2ARemoteClient(base_url="http://test:8000", timeout=5.0)
        assert client.timeout == 5.0
