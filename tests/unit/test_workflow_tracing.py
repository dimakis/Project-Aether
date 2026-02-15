"""Unit tests for MLflow tracing in ArchitectWorkflow.

Part 2a: stream_conversation uses @mlflow.trace (async generator support)
Part 2c: session grouping uses metadata, not tags
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage

from src.graph.state import ConversationState


def _make_workflow():
    """Create ArchitectWorkflow with mocked agent (avoids real LLM import)."""
    from src.agents.architect.workflow import ArchitectWorkflow

    w = ArchitectWorkflow.__new__(ArchitectWorkflow)
    w.agent = MagicMock()
    w.agent.model_name = "test-model"
    w.agent._build_messages.return_value = [HumanMessage(content="test")]
    w.agent._get_entity_context = AsyncMock(return_value=(None, None))
    w.agent._get_ha_tools.return_value = []
    w.agent._is_mutating_tool.return_value = False
    w.agent._extract_proposals.return_value = []
    w.agent.get_tool_llm.return_value = MagicMock(astream=MagicMock(return_value=_empty_astream()))
    return w


async def _empty_astream():
    """Empty async stream that yields one content chunk."""
    yield AIMessageChunk(content="Hello")


class TestStreamConversationTracing:
    """stream_conversation should use @mlflow.trace for tracing."""

    @pytest.mark.asyncio
    async def test_emits_trace_id_event(self):
        """The stream should yield a trace_id event early."""
        mock_span = MagicMock()
        mock_span.request_id = "trace-abc123"

        with patch("src.agents.architect.workflow.mlflow") as mock_mlflow:
            # Make @mlflow.trace a passthrough (we test event emission, not MLflow internals)
            mock_mlflow.trace = lambda **kw: lambda fn: fn
            mock_mlflow.get_current_active_span.return_value = mock_span

            workflow = _make_workflow()
            state = ConversationState(messages=[])
            events = []

            async for event in workflow.stream_conversation(state=state, user_message="hi"):
                events.append(event)

        trace_events = [e for e in events if e.get("type") == "trace_id"]
        assert len(trace_events) == 1
        assert trace_events[0]["content"] == "trace-abc123"

    @pytest.mark.asyncio
    async def test_uses_metadata_for_session_grouping(self):
        """Session grouping should use metadata per MLflow 3.x docs."""
        with patch("src.agents.architect.workflow.mlflow") as mock_mlflow:
            mock_mlflow.trace = lambda **kw: lambda fn: fn
            mock_mlflow.get_current_active_span.return_value = None

            workflow = _make_workflow()
            state = ConversationState(messages=[])

            async for _ in workflow.stream_conversation(state=state, user_message="hi"):
                pass

        # Check that update_current_trace was called with metadata
        mock_mlflow.update_current_trace.assert_called()
        call_kwargs = mock_mlflow.update_current_trace.call_args
        kw = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        assert "metadata" in kw, "update_current_trace must be called with metadata="
        assert "mlflow.trace.session" in kw["metadata"]

    @pytest.mark.asyncio
    async def test_applies_mlflow_trace_decorator(self):
        """stream_conversation should apply @mlflow.trace to the inner generator."""
        trace_calls = []

        def mock_trace_decorator(**kw):
            trace_calls.append(kw)
            return lambda fn: fn

        with patch("src.agents.architect.workflow.mlflow") as mock_mlflow:
            mock_mlflow.trace = mock_trace_decorator
            mock_mlflow.get_current_active_span.return_value = None

            workflow = _make_workflow()
            state = ConversationState(messages=[])

            async for _ in workflow.stream_conversation(state=state, user_message="hi"):
                pass

        assert len(trace_calls) == 1
        assert trace_calls[0]["name"] == "conversation_turn"
        assert "output_reducer" in trace_calls[0]

    @pytest.mark.asyncio
    async def test_yields_state_event_at_end(self):
        """The stream should end with a state event."""
        with patch("src.agents.architect.workflow.mlflow", None):
            workflow = _make_workflow()
            state = ConversationState(messages=[])
            events = []

            async for event in workflow.stream_conversation(state=state, user_message="hi"):
                events.append(event)

        state_events = [e for e in events if e.get("type") == "state"]
        assert len(state_events) == 1

    @pytest.mark.asyncio
    async def test_works_without_mlflow(self):
        """When mlflow is None, streaming works without tracing."""
        with patch("src.agents.architect.workflow.mlflow", None):
            workflow = _make_workflow()
            state = ConversationState(messages=[])
            events = []

            async for event in workflow.stream_conversation(state=state, user_message="hi"):
                events.append(event)

        # Should have token events and a state event, but no trace_id
        token_events = [e for e in events if e.get("type") == "token"]
        trace_events = [e for e in events if e.get("type") == "trace_id"]
        assert len(token_events) >= 1
        assert len(trace_events) == 0


class TestContinueConversationTracing:
    """continue_conversation should use metadata for session grouping."""

    @pytest.mark.asyncio
    async def test_uses_metadata_not_tags(self):
        """Session ID should be set as metadata, not just tags."""
        with patch("src.agents.architect.workflow.mlflow") as mock_mlflow:
            # Make @mlflow.trace a passthrough decorator
            mock_mlflow.trace = lambda **kw: lambda fn: fn
            mock_mlflow.get_current_active_span.return_value = None

            workflow = _make_workflow()
            workflow.agent.invoke = AsyncMock(return_value={"messages": []})
            state = ConversationState(messages=[])

            await workflow.continue_conversation(
                state=state,
                user_message="hi",
            )

        # update_current_trace should use metadata=
        if mock_mlflow.update_current_trace.called:
            call_kwargs = mock_mlflow.update_current_trace.call_args
            kw = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
            assert "metadata" in kw, (
                "continue_conversation should use metadata for session grouping"
            )
