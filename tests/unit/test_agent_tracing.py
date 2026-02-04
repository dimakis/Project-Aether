"""Unit tests for agent tracing and logging capabilities."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

from langchain_core.messages import HumanMessage, AIMessage

from src.agents import BaseAgent
from src.graph.state import AgentRole, BaseState, ConversationState


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    async def invoke(self, state, **kwargs):
        return {"status": "ok"}


class TestBaseAgentTracing:
    """Tests for BaseAgent tracing methods."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        return ConcreteAgent(role=AgentRole.ARCHITECT, name="TestAgent")

    @pytest.fixture
    def conversation_state(self):
        """Create a test conversation state."""
        return ConversationState(
            current_agent=AgentRole.ARCHITECT,
            messages=[
                HumanMessage(content="Turn on the lights"),
                AIMessage(content="I can help with that"),
            ],
        )

    def test_log_state_context_logs_run_id(self, agent):
        """Test that _log_state_context logs the run_id."""
        state = BaseState(current_agent=AgentRole.ARCHITECT)
        
        with patch("src.agents.log_param") as mock_log_param:
            agent._log_state_context(state)
            
            # Should log run_id
            calls = [call[0] for call in mock_log_param.call_args_list]
            assert any("run_id" in str(call) for call in calls)

    def test_log_state_context_logs_conversation_id(self, agent, conversation_state):
        """Test that _log_state_context logs conversation_id for ConversationState."""
        with patch("src.agents.log_param") as mock_log_param:
            agent._log_state_context(conversation_state)
            
            # Should log conversation_id
            calls = [str(call) for call in mock_log_param.call_args_list]
            assert any("conversation_id" in call for call in calls)

    def test_log_state_context_logs_message_count(self, agent, conversation_state):
        """Test that _log_state_context logs message count."""
        with patch("src.agents.log_param") as mock_log_param:
            agent._log_state_context(conversation_state)
            
            # Should log message_count
            calls = [str(call) for call in mock_log_param.call_args_list]
            assert any("message_count" in call for call in calls)

    def test_log_state_context_logs_latest_message(self, agent, conversation_state):
        """Test that _log_state_context logs the latest message."""
        with patch("src.agents.log_param") as mock_log_param:
            agent._log_state_context(conversation_state)
            
            # Should log latest_message
            calls = [str(call) for call in mock_log_param.call_args_list]
            assert any("latest_message" in call for call in calls)

    def test_log_state_context_handles_none_state(self, agent):
        """Test that _log_state_context handles None state gracefully."""
        with patch("src.agents.log_param") as mock_log_param:
            # Should not raise
            agent._log_state_context(None)
            
            # Should not log anything
            mock_log_param.assert_not_called()


class TestLogConversation:
    """Tests for the log_conversation method."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        return ConcreteAgent(role=AgentRole.ARCHITECT, name="TestAgent")

    def test_log_conversation_logs_artifact(self, agent):
        """Test that log_conversation logs a JSON artifact."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there"),
        ]
        conversation_id = str(uuid4())
        response = "New response"

        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation(conversation_id, messages, response)
            
            mock_log_dict.assert_called_once()
            call_args = mock_log_dict.call_args
            
            # Check the logged data
            logged_data = call_args[0][0]
            assert logged_data["agent"] == "TestAgent"
            assert logged_data["conversation_id"] == conversation_id
            assert logged_data["message_count"] == 3  # 2 messages + 1 response
            assert len(logged_data["messages"]) == 3

    def test_log_conversation_serializes_messages(self, agent):
        """Test that log_conversation correctly serializes messages."""
        messages = [
            HumanMessage(content="User message"),
            AIMessage(content="AI response"),
        ]
        conversation_id = str(uuid4())

        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation(conversation_id, messages)
            
            logged_data = mock_log_dict.call_args[0][0]
            
            # Check message serialization
            assert logged_data["messages"][0]["role"] == "user"
            assert logged_data["messages"][0]["content"] == "User message"
            assert logged_data["messages"][1]["role"] == "assistant"
            assert logged_data["messages"][1]["content"] == "AI response"

    def test_log_conversation_appends_response(self, agent):
        """Test that log_conversation appends the response."""
        messages = [HumanMessage(content="Hello")]
        conversation_id = str(uuid4())
        response = "New response text"

        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation(conversation_id, messages, response)
            
            logged_data = mock_log_dict.call_args[0][0]
            
            # Last message should be the response
            assert logged_data["messages"][-1]["role"] == "assistant"
            assert logged_data["messages"][-1]["content"] == response

    def test_log_conversation_truncates_long_content(self, agent):
        """Test that log_conversation truncates long message content."""
        long_content = "x" * 3000  # Longer than 2000 char limit
        messages = [HumanMessage(content=long_content)]
        conversation_id = str(uuid4())

        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation(conversation_id, messages)
            
            logged_data = mock_log_dict.call_args[0][0]
            
            # Content should be truncated
            assert len(logged_data["messages"][0]["content"]) == 2000

    def test_log_conversation_uses_correct_filename(self, agent):
        """Test that log_conversation uses correct artifact filename."""
        messages = [HumanMessage(content="Test")]
        conversation_id = "test-conv-id"

        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation(conversation_id, messages)
            
            filename = mock_log_dict.call_args[0][1]
            
            # Filename should contain agent name and conversation_id
            assert "TestAgent" in filename
            assert "test-conv-id" in filename
            assert filename.startswith("conversations/")


class TestTraceSpan:
    """Tests for the trace_span context manager."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        return ConcreteAgent(role=AgentRole.ARCHITECT, name="TestAgent")

    @pytest.mark.asyncio
    async def test_trace_span_logs_state_context(self, agent):
        """Test that trace_span calls _log_state_context."""
        state = BaseState(current_agent=AgentRole.ARCHITECT)
        
        with patch.object(agent, "_log_state_context") as mock_log_state:
            async with agent.trace_span("test_op", state):
                pass
            
            mock_log_state.assert_called_once_with(state)

    @pytest.mark.asyncio
    async def test_trace_span_yields_metadata(self, agent):
        """Test that trace_span yields span metadata dict."""
        state = BaseState(current_agent=AgentRole.ARCHITECT)
        
        async with agent.trace_span("test_op", state) as span_meta:
            assert isinstance(span_meta, dict)
            assert span_meta["agent_role"] == AgentRole.ARCHITECT.value
            assert span_meta["operation"] == "test_op"
            assert "started_at" in span_meta

    @pytest.mark.asyncio
    async def test_trace_span_updates_metadata_on_success(self, agent):
        """Test that trace_span updates metadata on successful completion."""
        state = BaseState(current_agent=AgentRole.ARCHITECT)
        
        async with agent.trace_span("test_op", state) as span_meta:
            pass
        
        assert span_meta["status"] == "success"
        assert "completed_at" in span_meta

    @pytest.mark.asyncio
    async def test_trace_span_updates_metadata_on_error(self, agent):
        """Test that trace_span updates metadata on error."""
        state = BaseState(current_agent=AgentRole.ARCHITECT)
        
        with pytest.raises(ValueError):
            async with agent.trace_span("test_op", state) as span_meta:
                raise ValueError("Test error")
        
        assert span_meta["status"] == "error"
        assert "Test error" in span_meta["error"]
