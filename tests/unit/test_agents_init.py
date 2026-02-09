"""Unit tests for BaseAgent class and agent initialization.

Tests BaseAgent methods: trace_span, logging, metric, conversation.
All inline imports (mlflow, src.tracing.context) are patched at SOURCE.
Module-level imports (emit_progress, log_param, etc.) are patched at
src.agents.<name> because they were imported at module level.
"""

import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.agents import BaseAgent, LibrarianAgent
from src.graph.state import AgentRole, BaseState


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    async def invoke(self, state, **kwargs):
        return {"status": "ok"}


class TestBaseAgentInitialization:
    """Tests for BaseAgent initialization."""

    def test_agent_init_with_role(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        assert agent.role == AgentRole.ARCHITECT
        assert agent.name == AgentRole.ARCHITECT.value

    def test_agent_init_with_custom_name(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT, name="CustomArchitect")
        assert agent.role == AgentRole.ARCHITECT
        assert agent.name == "CustomArchitect"

    def test_librarian_agent_init(self):
        agent = LibrarianAgent()
        assert agent.role == AgentRole.LIBRARIAN
        assert agent.name == "Librarian"

    def test_agent_has_settings(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        assert agent._settings is not None


class TestBaseAgentTraceSpan:
    """Tests for BaseAgent.trace_span context manager."""

    async def test_trace_span_yields_metadata(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        with patch("src.agents.emit_progress"):
            async with agent.trace_span("test_op") as metadata:
                assert metadata["agent_role"] == "architect"
                assert metadata["operation"] == "test_op"
                assert "started_at" in metadata

    async def test_trace_span_emits_progress(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        with patch("src.agents.emit_progress") as mock_emit:
            async with agent.trace_span("test_op"):
                pass
            # Should emit agent_start and agent_end
            calls = [c[0][0] for c in mock_emit.call_args_list]
            assert "agent_start" in calls
            assert "agent_end" in calls

    async def test_trace_span_handles_error(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        with (
            patch("src.agents.emit_progress"),
            patch("src.agents.add_span_event"),
        ):
            with pytest.raises(ValueError, match="test error"):
                async with agent.trace_span("test_op") as metadata:
                    raise ValueError("test error")

    async def test_trace_span_with_state_context(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        mock_state = MagicMock(spec=BaseState)
        mock_state.run_id = "run-123"
        mock_state.current_agent = AgentRole.ARCHITECT

        with (
            patch("src.agents.emit_progress"),
            patch("src.agents.get_active_span", return_value=None),
            patch("src.agents.add_span_event"),
            patch("src.agents.log_param"),
        ):
            async with agent.trace_span("test_op", state=mock_state) as metadata:
                assert metadata["run_id"] == "run-123"

    async def test_trace_span_mlflow_unavailable(self):
        """When mlflow import fails, operation should still complete."""
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        with (
            patch("src.agents.emit_progress"),
            patch.dict("sys.modules", {"mlflow": None}),
        ):
            async with agent.trace_span("test_op") as metadata:
                metadata["result"] = "ok"
            assert metadata["status"] == "success"

    async def test_trace_span_with_mlflow_available(self):
        """When mlflow is available, span should be created."""
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        mock_mlflow = MagicMock()
        mock_span_ctx = MagicMock()
        mock_mlflow.start_span.return_value = mock_span_ctx

        with (
            patch("src.agents.emit_progress"),
            patch("src.agents.get_active_span", return_value=MagicMock()),
            patch("src.agents.add_span_event"),
            patch.dict(
                "sys.modules",
                {"mlflow": mock_mlflow},
            ),
        ):
            async with agent.trace_span("test_op"):
                pass


class TestBaseAgentLogging:
    """Tests for BaseAgent logging methods."""

    def test_log_param(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        with patch("src.agents.log_param") as mock_log_param:
            agent.log_param("test_key", "test_value")
            mock_log_param.assert_called_once_with(
                f"{agent.name}.test_key", "test_value"
            )

    def test_log_metric_with_active_run(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()  # has active run
        with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
            agent.log_metric("accuracy", 0.95)
            mock_mlflow.log_metric.assert_called_once()

    def test_log_metric_no_active_run(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = None
        with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
            agent.log_metric("accuracy", 0.95)
            mock_mlflow.log_metric.assert_not_called()

    def test_log_metric_mlflow_error(self):
        """Should not raise when mlflow fails."""
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        with patch.dict("sys.modules", {"mlflow": None}):
            # Should not raise
            agent.log_metric("accuracy", 0.95)


class TestBaseAgentConversation:
    """Tests for BaseAgent.log_conversation."""

    def test_log_conversation_basic(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]
        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation("conv-123", messages)
            mock_log_dict.assert_called_once()
            call_args = mock_log_dict.call_args[0]
            data = call_args[0]
            assert data["conversation_id"] == "conv-123"
            assert data["message_count"] == 2

    def test_log_conversation_with_response(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        messages = [HumanMessage(content="Hello")]
        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation("conv-123", messages, response="World")
            data = mock_log_dict.call_args[0][0]
            assert data["message_count"] == 2  # original + response

    def test_log_conversation_with_tool_calls(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        messages = [HumanMessage(content="Hello")]
        tool_calls = [{"name": "search", "args": {"q": "test"}, "result": "found"}]
        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation("conv-123", messages, tool_calls=tool_calls)
            data = mock_log_dict.call_args[0][0]
            assert "tool_calls" in data
            assert data["tool_calls"][0]["name"] == "search"

    def test_log_conversation_message_types(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        messages = [
            HumanMessage(content="User message"),
            AIMessage(content="AI message"),
            ToolMessage(content="Tool result", tool_call_id="tc-1"),
        ]
        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation("conv-123", messages)
            data = mock_log_dict.call_args[0][0]
            roles = [m["role"] for m in data["messages"]]
            assert "user" in roles
            assert "assistant" in roles
            assert "tool" in roles

    def test_log_conversation_truncates_long_content(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        long_content = "x" * 5000
        messages = [HumanMessage(content=long_content)]
        with patch("src.agents.log_dict") as mock_log_dict:
            agent.log_conversation("conv-123", messages)
            data = mock_log_dict.call_args[0][0]
            assert len(data["messages"][0]["content"]) <= 2000


class TestBaseAgentStateContext:
    """Tests for BaseAgent._log_state_context."""

    def test_log_state_context_none(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        with patch("src.agents.log_param") as mock_log:
            agent._log_state_context(None)
            mock_log.assert_not_called()

    def test_log_state_context_with_state(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        mock_state = MagicMock(spec=BaseState)
        mock_state.run_id = "run-123"
        mock_state.current_agent = AgentRole.ARCHITECT
        # Remove conversation attributes to simplify
        del mock_state.conversation_id
        del mock_state.messages
        del mock_state.status

        with patch("src.agents.log_param") as mock_log:
            agent._log_state_context(mock_state)
            assert mock_log.call_count >= 2  # run_id + agent


class TestBaseAgentSpanIO:
    """Tests for _set_span_inputs and _set_span_outputs."""

    def test_set_span_inputs_with_set_inputs(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        mock_span = MagicMock()
        mock_span.set_inputs = MagicMock()
        agent._set_span_inputs(mock_span, {"key": "value"})
        mock_span.set_inputs.assert_called_once_with({"key": "value"})

    def test_set_span_inputs_none_span(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        agent._set_span_inputs(None, {"key": "value"})  # Should not raise

    def test_set_span_outputs_with_set_outputs(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        mock_span = MagicMock()
        mock_span.set_outputs = MagicMock()
        agent._set_span_outputs(mock_span, {"result": "ok"})
        mock_span.set_outputs.assert_called_once_with({"result": "ok"})

    def test_set_span_outputs_none_span(self):
        agent = ConcreteAgent(role=AgentRole.ARCHITECT)
        agent._set_span_outputs(None, {"result": "ok"})  # Should not raise


class TestLibrarianAgentInvoke:
    """Tests for LibrarianAgent.invoke."""

    async def test_invoke_delegates_to_discovery_node(self):
        agent = LibrarianAgent()
        mock_state = MagicMock()
        expected = {"entities_found": 5}

        with patch(
            "src.graph.nodes.run_discovery_node",
            return_value=expected,
        ) as mock_node:
            result = await agent.invoke(mock_state)
            assert result == expected
            mock_node.assert_called_once()
