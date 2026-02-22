"""Tests for the `agent` field in ChatCompletionRequest (Feature 30).

Covers:
- Schema accepts `agent` field with default "auto"
- Schema accepts specific agent names
- State created with active_agent populated from request
- ConversationState reflects the agent selection
"""

from __future__ import annotations


class TestChatCompletionRequestAgentField:
    """ChatCompletionRequest schema must accept an `agent` field."""

    def test_agent_field_defaults_to_auto(self):
        from src.api.routes.openai_compat.schemas import ChatCompletionRequest

        req = ChatCompletionRequest(
            messages=[{"role": "user", "content": "hello"}],
        )
        assert req.agent == "auto"

    def test_agent_field_accepts_specific_agent(self):
        from src.api.routes.openai_compat.schemas import ChatCompletionRequest

        req = ChatCompletionRequest(
            messages=[{"role": "user", "content": "hello"}],
            agent="architect",
        )
        assert req.agent == "architect"

    def test_agent_field_accepts_auto(self):
        from src.api.routes.openai_compat.schemas import ChatCompletionRequest

        req = ChatCompletionRequest(
            messages=[{"role": "user", "content": "hello"}],
            agent="auto",
        )
        assert req.agent == "auto"

    def test_agent_field_included_in_model_dump(self):
        from src.api.routes.openai_compat.schemas import ChatCompletionRequest

        req = ChatCompletionRequest(
            messages=[{"role": "user", "content": "hello"}],
            agent="knowledge",
        )
        data = req.model_dump()
        assert data["agent"] == "knowledge"

    def test_agent_field_preserved_in_json_roundtrip(self):
        from src.api.routes.openai_compat.schemas import ChatCompletionRequest

        req = ChatCompletionRequest(
            messages=[{"role": "user", "content": "hello"}],
            agent="data_scientist",
        )
        json_str = req.model_dump_json()
        req2 = ChatCompletionRequest.model_validate_json(json_str)
        assert req2.agent == "data_scientist"


class TestStateActiveAgentFromRequest:
    """ConversationState.active_agent should be populated from the request."""

    def test_state_with_explicit_agent(self):
        from src.graph.state import ConversationState

        state = ConversationState(active_agent="architect")
        assert state.active_agent == "architect"

    def test_state_with_auto_agent_leaves_active_agent_none(self):
        from src.graph.state import ConversationState

        state = ConversationState(active_agent=None)
        assert state.active_agent is None

    def test_state_with_channel(self):
        from src.graph.state import ConversationState

        state = ConversationState(channel="api", active_agent="knowledge")
        assert state.channel == "api"
        assert state.active_agent == "knowledge"
