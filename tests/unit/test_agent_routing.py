"""Tests for agent routing logic (Feature 30).

The routing helper resolves the `agent` field from a ChatCompletionRequest
into a concrete active_agent on the ConversationState and determines which
workflow to use.

Covers:
- "auto" defaults to "architect" (backward compatible)
- Explicit agent name is passed through
- State gets active_agent and channel populated
- Unknown agent names fall back gracefully
"""

from __future__ import annotations

from src.graph.state import ConversationState


class TestResolveAgentRouting:
    """resolve_agent_routing() determines the active agent and workflow."""

    def test_auto_defaults_to_architect(self):
        from src.agents.routing import resolve_agent_routing

        result = resolve_agent_routing(agent="auto")
        assert result.active_agent == "architect"
        assert result.workflow_agent == "architect"

    def test_explicit_architect_bypasses_orchestrator(self):
        from src.agents.routing import resolve_agent_routing

        result = resolve_agent_routing(agent="architect")
        assert result.active_agent == "architect"
        assert result.workflow_agent == "architect"
        assert result.needs_orchestrator is False

    def test_explicit_knowledge_sets_active_agent(self):
        from src.agents.routing import resolve_agent_routing

        result = resolve_agent_routing(agent="knowledge")
        assert result.active_agent == "knowledge"

    def test_explicit_data_scientist_sets_active_agent(self):
        from src.agents.routing import resolve_agent_routing

        result = resolve_agent_routing(agent="data_scientist")
        assert result.active_agent == "data_scientist"

    def test_auto_marks_needs_orchestrator(self):
        from src.agents.routing import resolve_agent_routing

        result = resolve_agent_routing(agent="auto")
        assert result.needs_orchestrator is True

    def test_channel_defaults_to_api(self):
        from src.agents.routing import resolve_agent_routing

        result = resolve_agent_routing(agent="auto")
        assert result.channel == "api"

    def test_channel_can_be_overridden(self):
        from src.agents.routing import resolve_agent_routing

        result = resolve_agent_routing(agent="architect", channel="voice")
        assert result.channel == "voice"

    def test_unknown_agent_falls_back_to_architect(self):
        from src.agents.routing import resolve_agent_routing

        result = resolve_agent_routing(agent="nonexistent_agent")
        assert result.active_agent == "architect"
        assert result.workflow_agent == "architect"


class TestApplyRoutingToState:
    """apply_routing_to_state() populates ConversationState fields."""

    def test_applies_active_agent_to_state(self):
        from src.agents.routing import apply_routing_to_state, resolve_agent_routing

        state = ConversationState(conversation_id="conv-1")
        routing = resolve_agent_routing(agent="knowledge")
        apply_routing_to_state(state, routing)

        assert state.active_agent == "knowledge"

    def test_applies_channel_to_state(self):
        from src.agents.routing import apply_routing_to_state, resolve_agent_routing

        state = ConversationState(conversation_id="conv-1")
        routing = resolve_agent_routing(agent="auto")
        apply_routing_to_state(state, routing)

        assert state.channel == "api"

    def test_auto_routing_sets_architect_as_active(self):
        from src.agents.routing import apply_routing_to_state, resolve_agent_routing

        state = ConversationState(conversation_id="conv-1")
        routing = resolve_agent_routing(agent="auto")
        apply_routing_to_state(state, routing)

        assert state.active_agent == "architect"
