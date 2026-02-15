"""Unit tests for multi-turn tool loop in stream_conversation().

Tests that the LLM can chain multiple tool calls in sequence by
using tool_llm (with tools bound) for follow-up calls.

TDD: Multi-turn tool loop with max iteration guard.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage

from src.agents.architect import ArchitectWorkflow
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
    return workflow


def _make_tool_call_chunk(name, args_str, call_id, index=0):
    """Create a mock AIMessageChunk with a tool call chunk."""
    chunk = AIMessageChunk(content="")
    chunk.tool_call_chunks = [{"name": name, "args": args_str, "id": call_id, "index": index}]
    return chunk


async def _async_iter(items):
    """Convert a list to an async iterator."""
    for item in items:
        yield item


class TestMultiTurnToolLoop:
    """Tests that tool_llm is used for follow-up calls, enabling chaining."""

    @pytest.mark.asyncio
    async def test_two_sequential_tool_calls(self):
        """LLM should be able to call a tool, then call another tool in follow-up."""
        workflow = _make_workflow()
        state = ConversationState(messages=[])

        tool_call_count = 0

        async def tool_invoke(args):
            nonlocal tool_call_count
            tool_call_count += 1
            return f"tool result {tool_call_count}"

        mock_tool = MagicMock()
        mock_tool.name = "get_entity_state"
        mock_tool.ainvoke = tool_invoke

        # Round 1: LLM calls get_entity_state
        round1_chunks = [
            _make_tool_call_chunk("get_entity_state", '{"entity_id": "light.kitchen"}', "call-1"),
        ]

        # Round 2: LLM calls get_entity_state again
        round2_chunks = [
            _make_tool_call_chunk("get_entity_state", '{"entity_id": "light.bedroom"}', "call-2"),
        ]

        # Round 3: LLM gives final answer
        round3_chunks = [
            AIMessageChunk(content="Both lights are on."),
        ]

        call_count = 0

        async def mock_astream(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                async for item in _async_iter(round1_chunks):
                    yield item
            elif call_count == 2:
                async for item in _async_iter(round2_chunks):
                    yield item
            else:
                async for item in _async_iter(round3_chunks):
                    yield item

        tool_llm_mock = MagicMock()
        tool_llm_mock.astream = mock_astream

        workflow.agent.get_tool_llm = MagicMock(return_value=tool_llm_mock)
        workflow.agent._get_ha_tools.return_value = [mock_tool]

        events = []
        async for event in workflow.stream_conversation(state, "check lights"):
            events.append(dict(event))

        event_types = [e["type"] for e in events]

        # Should have two tool_start/tool_end pairs
        assert event_types.count("tool_start") == 2, (
            f"Expected 2 tool_start, got {event_types.count('tool_start')} in {event_types}"
        )
        assert event_types.count("tool_end") == 2, (
            f"Expected 2 tool_end, got {event_types.count('tool_end')} in {event_types}"
        )

        # Should have tokens from final response
        assert "token" in event_types

        # Both tools should have been invoked
        assert tool_call_count == 2

    @pytest.mark.asyncio
    async def test_max_iterations_guard(self):
        """Tool loop should stop after MAX_TOOL_ITERATIONS to prevent infinite loops."""
        workflow = _make_workflow()
        state = ConversationState(messages=[])

        async def tool_invoke(args):
            return "result"

        mock_tool = MagicMock()
        mock_tool.name = "get_entity_state"
        mock_tool.ainvoke = tool_invoke

        call_count = 0

        async def mock_astream(messages, **kwargs):
            """Always return tool calls, simulating infinite loop."""
            nonlocal call_count
            call_count += 1
            async for item in _async_iter(
                [
                    _make_tool_call_chunk("get_entity_state", "{}", f"call-{call_count}"),
                ]
            ):
                yield item

        tool_llm_mock = MagicMock()
        tool_llm_mock.astream = mock_astream

        workflow.agent.get_tool_llm = MagicMock(return_value=tool_llm_mock)
        workflow.agent._get_ha_tools.return_value = [mock_tool]

        events = []
        async for event in workflow.stream_conversation(state, "infinite loop"):
            events.append(dict(event))

        event_types = [e["type"] for e in events]

        # Should have tool calls, but limited by max iterations
        tool_starts = event_types.count("tool_start")
        assert tool_starts <= 10, f"Expected max 10 tool rounds, got {tool_starts}"
        assert tool_starts >= 2, f"Expected at least 2 rounds, got {tool_starts}"

    @pytest.mark.asyncio
    async def test_single_tool_call_followed_by_response(self):
        """Single tool call should still work (backward compatible)."""
        workflow = _make_workflow()
        state = ConversationState(messages=[])

        async def tool_invoke(args):
            return "result"

        mock_tool = MagicMock()
        mock_tool.name = "get_entity_state"
        mock_tool.ainvoke = tool_invoke

        round1_chunks = [
            _make_tool_call_chunk("get_entity_state", "{}", "call-1"),
        ]
        round2_chunks = [
            AIMessageChunk(content="The light is on."),
        ]

        call_count = 0

        async def mock_astream(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                async for item in _async_iter(round1_chunks):
                    yield item
            else:
                async for item in _async_iter(round2_chunks):
                    yield item

        tool_llm_mock = MagicMock()
        tool_llm_mock.astream = mock_astream

        workflow.agent.get_tool_llm = MagicMock(return_value=tool_llm_mock)
        workflow.agent._get_ha_tools.return_value = [mock_tool]

        events = []
        async for event in workflow.stream_conversation(state, "check light"):
            events.append(dict(event))

        event_types = [e["type"] for e in events]
        assert event_types.count("tool_start") == 1
        assert event_types.count("tool_end") == 1
        assert "token" in event_types
