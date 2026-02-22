"""Tests for orchestration-related model extensions (Feature 30).

Covers:
- Agent entity routing fields (domain, intent_patterns, is_routable, capabilities)
- ConversationState extensions (channel, active_agent)
- AgentRole / AgentName enum extensions (KNOWLEDGE)
"""

from __future__ import annotations


class TestAgentRoutingFields:
    """Agent entity must have routing metadata for Orchestrator discovery."""

    def test_agent_has_domain_field(self):
        from src.storage.entities.agent import Agent

        agent = Agent(
            name="knowledge",
            description="General knowledge",
            domain="knowledge",
        )
        assert agent.domain == "knowledge"

    def test_agent_domain_defaults_to_none(self):
        from src.storage.entities.agent import Agent

        agent = Agent(name="architect", description="HA architect")
        assert agent.domain is None

    def test_agent_has_is_routable_field(self):
        from src.storage.entities.agent import Agent

        agent = Agent(
            name="knowledge",
            description="General knowledge",
            is_routable=True,
        )
        assert agent.is_routable is True

    def test_agent_is_routable_server_default(self):
        from src.storage.entities.agent import Agent

        col = Agent.__table__.c.is_routable
        assert str(col.server_default.arg) == "false"

    def test_agent_has_intent_patterns_field(self):
        from src.storage.entities.agent import Agent

        patterns = ["general_question", "trivia", "explain"]
        agent = Agent(
            name="knowledge",
            description="General knowledge",
            intent_patterns=patterns,
        )
        assert agent.intent_patterns == patterns

    def test_agent_intent_patterns_server_default(self):
        from src.storage.entities.agent import Agent

        col = Agent.__table__.c.intent_patterns
        assert str(col.server_default.arg) == "[]"

    def test_agent_has_capabilities_field(self):
        from src.storage.entities.agent import Agent

        caps = ["answer_questions", "explain_concepts"]
        agent = Agent(
            name="knowledge",
            description="General knowledge",
            capabilities=caps,
        )
        assert agent.capabilities == caps

    def test_agent_capabilities_server_default(self):
        from src.storage.entities.agent import Agent

        col = Agent.__table__.c.capabilities
        assert str(col.server_default.arg) == "[]"


class TestAgentNameExtension:
    """AgentName literal must include 'knowledge' for the Knowledge Agent."""

    def test_knowledge_is_valid_agent_name(self):
        # AgentName is a Literal type — verify 'knowledge' is accepted
        # by checking the type's __args__
        import typing

        from src.storage.entities.agent import AgentName

        args = typing.get_args(AgentName)
        assert "knowledge" in args

    def test_dashboard_designer_is_valid_agent_name(self):
        import typing

        from src.storage.entities.agent import AgentName

        args = typing.get_args(AgentName)
        assert "dashboard_designer" in args


class TestAgentRoleExtension:
    """AgentRole enum must include KNOWLEDGE for the Knowledge Agent."""

    def test_knowledge_role_exists(self):
        from src.graph.state.enums import AgentRole

        assert AgentRole.KNOWLEDGE == "knowledge"

    def test_knowledge_role_is_str_enum(self):
        from src.graph.state.enums import AgentRole

        assert isinstance(AgentRole.KNOWLEDGE, str)


class TestConversationStateExtension:
    """ConversationState must have channel and active_agent fields."""

    def test_channel_field_defaults_to_none(self):
        from src.graph.state.conversation import ConversationState

        state = ConversationState()
        assert state.channel is None

    def test_channel_field_accepts_text(self):
        from src.graph.state.conversation import ConversationState

        state = ConversationState(channel="text")
        assert state.channel == "text"

    def test_channel_field_accepts_voice(self):
        from src.graph.state.conversation import ConversationState

        state = ConversationState(channel="voice")
        assert state.channel == "voice"

    def test_active_agent_field_defaults_to_none(self):
        from src.graph.state.conversation import ConversationState

        state = ConversationState()
        assert state.active_agent is None

    def test_active_agent_field_accepts_agent_name(self):
        from src.graph.state.conversation import ConversationState

        state = ConversationState(active_agent="architect")
        assert state.active_agent == "architect"

    def test_state_serialization_includes_new_fields(self):
        from src.graph.state.conversation import ConversationState

        state = ConversationState(channel="voice", active_agent="knowledge")
        data = state.model_dump()
        assert data["channel"] == "voice"
        assert data["active_agent"] == "knowledge"
