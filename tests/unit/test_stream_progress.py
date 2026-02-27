"""Unit tests for stream_conversation() progress consumer.

Tests that tool execution within stream_conversation() creates an
ExecutionContext, drains progress events, and applies timeouts.

TDD: Progress consumer and timeout for tool execution in streaming.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage

from src.agents.architect import ArchitectWorkflow
from src.agents.execution_context import (
    emit_progress,
    get_execution_context,
)
from src.graph.state import ConversationState


def _make_workflow():
    """Create an ArchitectWorkflow with mocked internals."""
    mock_agent = MagicMock()
    mock_agent.name = "Architect"
    mock_agent.role = MagicMock()
    mock_agent.role.value = "architect"
    mock_agent.llm = MagicMock()
    mock_agent._get_ha_tools.return_value = []
    mock_agent._build_messages.return_value = [HumanMessage(content="test")]
    mock_agent._is_mutating_tool.return_value = False
    mock_agent._get_entity_context = AsyncMock(return_value=(None, None))

    workflow = ArchitectWorkflow.__new__(ArchitectWorkflow)
    workflow.agent = mock_agent
    workflow.session_factory = None
    return workflow


def _make_tool_call_chunk(name, args_str, call_id, index=0):
    """Create a mock AIMessageChunk with a tool call chunk."""
    chunk = AIMessageChunk(content="")
    chunk.tool_call_chunks = [{"name": name, "args": args_str, "id": call_id, "index": index}]
    return chunk


class TestStreamProgressEvents:
    """Tests that progress events from tools are yielded as StreamEvents."""

    @pytest.mark.asyncio
    async def test_progress_events_yielded_during_tool_execution(self):
        """Progress events emitted by a tool should appear in the stream."""
        workflow = _make_workflow()
        state = ConversationState(messages=[])

        async def mock_tool_invoke(args):
            """Tool that emits progress events via execution context."""
            ctx = get_execution_context()
            assert ctx is not None, "ExecutionContext should be active during tool"
            assert ctx.progress_queue is not None
            emit_progress("agent_start", "energy_analyst", "EnergyAnalyst started")
            await asyncio.sleep(0.05)  # Simulate work
            emit_progress("status", "energy_analyst", "Collecting data...")
            await asyncio.sleep(0.05)
            emit_progress("agent_end", "energy_analyst", "EnergyAnalyst completed")
            return "analysis done"

        mock_tool = MagicMock()
        mock_tool.name = "consult_data_science_team"
        mock_tool.ainvoke = mock_tool_invoke

        # First LLM call: stream tool call chunks
        chunks = [
            _make_tool_call_chunk("consult_data_science_team", '{"query": "test"}', "call-1"),
        ]

        # Follow-up LLM call: stream response
        follow_up_chunks = [
            AIMessageChunk(content="Here are the results."),
        ]

        call_count = 0

        async def mock_astream(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                async for item in _async_iter(chunks):
                    yield item
            else:
                async for item in _async_iter(follow_up_chunks):
                    yield item

        tool_llm_mock = MagicMock()
        tool_llm_mock.astream = mock_astream

        workflow.agent.get_tool_llm = MagicMock(return_value=tool_llm_mock)
        workflow.agent._get_ha_tools.return_value = [mock_tool]

        events = []
        async for event in workflow.stream_conversation(state, "test message"):
            events.append(dict(event))

        event_types = [e["type"] for e in events]

        # Should contain progress events from the tool
        assert "agent_start" in event_types, f"Expected agent_start in {event_types}"
        assert "agent_end" in event_types, f"Expected agent_end in {event_types}"
        assert "status" in event_types or "progress" in event_types, (
            f"Expected status/progress in {event_types}"
        )

        # Progress events should appear between tool_start and tool_end
        tool_start_idx = event_types.index("tool_start")
        tool_end_idx = event_types.index("tool_end")
        progress_indices = [
            i
            for i, t in enumerate(event_types)
            if t in ("agent_start", "agent_end", "status", "progress")
        ]
        for idx in progress_indices:
            assert tool_start_idx < idx < tool_end_idx, (
                f"Progress event at {idx} should be between tool_start ({tool_start_idx}) and tool_end ({tool_end_idx})"
            )

    @pytest.mark.asyncio
    async def test_tool_without_progress_events_works(self):
        """A tool that emits no progress events should still work normally."""
        workflow = _make_workflow()
        state = ConversationState(messages=[])

        async def simple_tool_invoke(args):
            return "simple result"

        mock_tool = MagicMock()
        mock_tool.name = "get_entity_state"
        mock_tool.ainvoke = simple_tool_invoke

        chunks = [
            _make_tool_call_chunk("get_entity_state", '{"entity_id": "light.kitchen"}', "call-1"),
        ]

        follow_up_chunks = [
            AIMessageChunk(content="The light is on."),
        ]

        call_count = 0

        async def mock_astream(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                async for item in _async_iter(chunks):
                    yield item
            else:
                async for item in _async_iter(follow_up_chunks):
                    yield item

        tool_llm_mock = MagicMock()
        tool_llm_mock.astream = mock_astream

        workflow.agent.get_tool_llm = MagicMock(return_value=tool_llm_mock)
        workflow.agent._get_ha_tools.return_value = [mock_tool]

        events = []
        async for event in workflow.stream_conversation(state, "test"):
            events.append(dict(event))

        event_types = [e["type"] for e in events]
        assert "tool_start" in event_types
        assert "tool_end" in event_types
        # No agent_start/agent_end progress events expected
        assert "agent_start" not in event_types
        assert "agent_end" not in event_types


class TestDrainLoopExitsImmediately:
    """Tests that the drain loop exits immediately when the tool finishes."""

    @pytest.mark.asyncio
    async def test_drain_loop_does_not_accumulate_dead_time(self):
        """Tool completing fast should not wait 0.5s per iteration.

        A tool that finishes in <50ms should complete the full stream
        (including multi-turn follow-up) in well under 1 second.
        """
        import time as _time

        workflow = _make_workflow()
        state = ConversationState(messages=[])

        async def instant_tool(args):
            """Tool that completes instantly."""
            return "instant"

        mock_tool = MagicMock()
        mock_tool.name = "get_entity_state"
        mock_tool.ainvoke = instant_tool

        chunks = [
            _make_tool_call_chunk("get_entity_state", '{"entity_id": "light.x"}', "call-1"),
        ]
        follow_up_chunks = [AIMessageChunk(content="Done.")]

        call_count = 0

        async def mock_astream(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                async for item in _async_iter(chunks):
                    yield item
            else:
                async for item in _async_iter(follow_up_chunks):
                    yield item

        tool_llm_mock = MagicMock()
        tool_llm_mock.astream = mock_astream

        workflow.agent.get_tool_llm = MagicMock(return_value=tool_llm_mock)
        workflow.agent._get_ha_tools.return_value = [mock_tool]

        t0 = _time.monotonic()
        events = []
        async for event in workflow.stream_conversation(state, "quick test"):
            events.append(dict(event))
        elapsed = _time.monotonic() - t0

        # The whole stream should complete in well under 1 second.
        # The old buggy code would stall ~0.5s per drain iteration.
        assert elapsed < 1.0, (
            f"Drain loop accumulated dead time: {elapsed:.2f}s (should be <1s for an instant tool)"
        )

        # Sanity: tool was invoked and result streamed
        event_types = [e["type"] for e in events]
        assert "tool_start" in event_types
        assert "tool_end" in event_types
        assert "token" in event_types


class TestToolTimeout:
    """Tests that tool execution respects configured timeouts."""

    @pytest.mark.asyncio
    async def test_tool_timeout_yields_error(self):
        """A tool exceeding its timeout should produce an error tool_end."""
        workflow = _make_workflow()
        state = ConversationState(messages=[])

        never_done = asyncio.Event()

        async def slow_tool_invoke(args):
            await never_done.wait()  # Block until cancelled by timeout
            return "should not reach"  # pragma: no cover

        mock_tool = MagicMock()
        mock_tool.name = "consult_data_science_team"
        mock_tool.ainvoke = slow_tool_invoke

        chunks = [
            _make_tool_call_chunk("consult_data_science_team", "{}", "call-1"),
        ]

        follow_up_chunks = [
            AIMessageChunk(content="Timed out."),
        ]

        call_count = 0

        async def mock_astream(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                async for item in _async_iter(chunks):
                    yield item
            else:
                async for item in _async_iter(follow_up_chunks):
                    yield item

        tool_llm_mock = MagicMock()
        tool_llm_mock.astream = mock_astream

        workflow.agent.get_tool_llm = MagicMock(return_value=tool_llm_mock)
        workflow.agent._get_ha_tools.return_value = [mock_tool]

        # Patch settings to use a very short timeout
        with patch("src.agents.streaming.dispatcher.get_settings") as mock_settings:
            settings = MagicMock()
            settings.tool_timeout_seconds = 0.1
            settings.analysis_tool_timeout_seconds = 0.2
            mock_settings.return_value = settings

            events = []
            async for event in workflow.stream_conversation(state, "test"):
                events.append(dict(event))

        event_types = [e["type"] for e in events]
        assert "tool_end" in event_types

        # The tool_end should contain an error indication
        tool_end_events = [e for e in events if e["type"] == "tool_end"]
        assert len(tool_end_events) >= 1
        # Result should mention timeout or error
        result = tool_end_events[0].get("result", "")
        assert "error" in result.lower() or "timeout" in result.lower(), (
            f"Expected timeout/error in tool_end result, got: {result}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _async_iter(items):
    """Convert a list to an async iterator."""
    for item in items:
        yield item
