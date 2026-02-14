"""Unit tests for ToolDispatcher.

Tests that ToolDispatcher correctly executes tools with progress draining,
timeouts, and approval_required handling for mutating tools.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.agents.execution_context import emit_progress, get_execution_context
from src.agents.streaming.parser import ParsedToolCall


class TestToolDispatcher:
    """Tests for dispatch_tool_calls() async generator."""

    @pytest.mark.asyncio
    async def test_tool_start_and_end_events(self):
        """Simple tool execution should yield tool_start then tool_end."""
        from src.agents.streaming.dispatcher import dispatch_tool_calls

        async def tool_invoke(args):
            return "result text"

        mock_tool = MagicMock()
        mock_tool.name = "get_entity_state"
        mock_tool.ainvoke = tool_invoke

        tool_calls = [
            ParsedToolCall(
                name="get_entity_state",
                args={"entity_id": "light.x"},
                id="call-1",
                is_mutating=False,
            ),
        ]
        tool_lookup = {"get_entity_state": mock_tool}

        events = []
        async for event in dispatch_tool_calls(
            tool_calls=tool_calls,
            tool_lookup=tool_lookup,
            conversation_id="conv-1",
        ):
            events.append(dict(event))

        types = [e["type"] for e in events]
        assert "tool_start" in types
        assert "tool_end" in types
        assert types.index("tool_start") < types.index("tool_end")

        # tool_end should have the result
        tool_end = next(e for e in events if e["type"] == "tool_end")
        assert "result text" in tool_end["result"]

    @pytest.mark.asyncio
    async def test_mutating_tool_yields_approval_required(self):
        """Mutating tools should yield approval_required and skip execution."""
        from src.agents.streaming.dispatcher import dispatch_tool_calls

        tool_calls = [
            ParsedToolCall(
                name="execute_service", args={"action": "on"}, id="call-1", is_mutating=True
            ),
        ]

        events = []
        async for event in dispatch_tool_calls(
            tool_calls=tool_calls,
            tool_lookup={},
            conversation_id="conv-1",
        ):
            events.append(dict(event))

        types = [e["type"] for e in events]
        assert "approval_required" in types
        assert "tool_start" not in types

        # Should carry the approval result
        result_events = [e for e in events if e["type"] == "_dispatch_result"]
        assert len(result_events) == 1
        results = result_events[0]["tool_results"]
        assert "call-1" in results
        assert "approval" in results["call-1"].lower()

    @pytest.mark.asyncio
    async def test_tool_not_found(self):
        """Unknown tool should produce 'not found' result without crashing."""
        from src.agents.streaming.dispatcher import dispatch_tool_calls

        tool_calls = [
            ParsedToolCall(name="unknown_tool", args={}, id="call-1", is_mutating=False),
        ]

        events = []
        async for event in dispatch_tool_calls(
            tool_calls=tool_calls,
            tool_lookup={},
            conversation_id="conv-1",
        ):
            events.append(dict(event))

        result_events = [e for e in events if e["type"] == "_dispatch_result"]
        assert len(result_events) == 1
        results = result_events[0]["tool_results"]
        assert "not found" in results["call-1"].lower()

    @pytest.mark.asyncio
    async def test_progress_events_forwarded(self):
        """Progress events emitted by a tool should appear in the stream."""
        from src.agents.streaming.dispatcher import dispatch_tool_calls

        async def tool_with_progress(args):
            ctx = get_execution_context()
            assert ctx is not None
            emit_progress("agent_start", "energy_analyst", "Started")
            await asyncio.sleep(0.05)
            emit_progress("status", "energy_analyst", "Working...")
            await asyncio.sleep(0.05)
            emit_progress("agent_end", "energy_analyst", "Done")
            return "analysis complete"

        mock_tool = MagicMock()
        mock_tool.name = "consult_data_science_team"
        mock_tool.ainvoke = tool_with_progress

        tool_calls = [
            ParsedToolCall(
                name="consult_data_science_team",
                args={"query": "test"},
                id="call-1",
                is_mutating=False,
            ),
        ]
        tool_lookup = {"consult_data_science_team": mock_tool}

        events = []
        async for event in dispatch_tool_calls(
            tool_calls=tool_calls,
            tool_lookup=tool_lookup,
            conversation_id="conv-1",
        ):
            events.append(dict(event))

        types = [e["type"] for e in events]
        assert "agent_start" in types
        assert "agent_end" in types

        # Progress events should be between tool_start and tool_end
        start_idx = types.index("tool_start")
        end_idx = types.index("tool_end")
        for i, t in enumerate(types):
            if t in ("agent_start", "agent_end", "status"):
                assert start_idx < i < end_idx

    @pytest.mark.asyncio
    async def test_tool_timeout(self):
        """A tool exceeding its timeout should produce an error tool_end."""
        from src.agents.streaming.dispatcher import dispatch_tool_calls

        async def slow_tool(args):
            await asyncio.sleep(10)
            return "should not reach"  # pragma: no cover

        mock_tool = MagicMock()
        mock_tool.name = "consult_data_science_team"
        mock_tool.ainvoke = slow_tool

        tool_calls = [
            ParsedToolCall(
                name="consult_data_science_team", args={}, id="call-1", is_mutating=False
            ),
        ]
        tool_lookup = {"consult_data_science_team": mock_tool}

        with patch("src.agents.streaming.dispatcher.get_settings") as mock_settings:
            settings = MagicMock()
            settings.tool_timeout_seconds = 0.1
            settings.analysis_tool_timeout_seconds = 0.2
            mock_settings.return_value = settings

            events = []
            async for event in dispatch_tool_calls(
                tool_calls=tool_calls,
                tool_lookup=tool_lookup,
                conversation_id="conv-1",
            ):
                events.append(dict(event))

        tool_end = next(e for e in events if e["type"] == "tool_end")
        assert "timeout" in tool_end["result"].lower() or "error" in tool_end["result"].lower()

    @pytest.mark.asyncio
    async def test_tool_exception_handled(self):
        """A tool that raises should produce an error tool_end."""
        from src.agents.streaming.dispatcher import dispatch_tool_calls

        async def failing_tool(args):
            raise ValueError("Something went wrong")

        mock_tool = MagicMock()
        mock_tool.name = "get_entity_state"
        mock_tool.ainvoke = failing_tool

        tool_calls = [
            ParsedToolCall(name="get_entity_state", args={}, id="call-1", is_mutating=False),
        ]
        tool_lookup = {"get_entity_state": mock_tool}

        events = []
        async for event in dispatch_tool_calls(
            tool_calls=tool_calls,
            tool_lookup=tool_lookup,
            conversation_id="conv-1",
        ):
            events.append(dict(event))

        tool_end = next(e for e in events if e["type"] == "tool_end")
        assert "error" in tool_end["result"].lower()

    @pytest.mark.asyncio
    async def test_proposal_tracking(self):
        """seek_approval tool results mentioning 'submitted' should be tracked."""
        from src.agents.streaming.dispatcher import dispatch_tool_calls

        async def seek_approval_tool(args):
            return "Proposal submitted successfully"

        mock_tool = MagicMock()
        mock_tool.name = "seek_approval"
        mock_tool.ainvoke = seek_approval_tool

        tool_calls = [
            ParsedToolCall(name="seek_approval", args={}, id="call-1", is_mutating=False),
        ]
        tool_lookup = {"seek_approval": mock_tool}

        events = []
        async for event in dispatch_tool_calls(
            tool_calls=tool_calls,
            tool_lookup=tool_lookup,
            conversation_id="conv-1",
        ):
            events.append(dict(event))

        result_events = [e for e in events if e["type"] == "_dispatch_result"]
        assert len(result_events) == 1
        assert len(result_events[0]["proposal_summaries"]) == 1
        assert "submitted" in result_events[0]["proposal_summaries"][0].lower()

    @pytest.mark.asyncio
    async def test_multiple_tools_sequential(self):
        """Multiple tool calls should be executed sequentially."""
        from src.agents.streaming.dispatcher import dispatch_tool_calls

        order = []

        async def tool_a(args):
            order.append("a")
            return "result a"

        async def tool_b(args):
            order.append("b")
            return "result b"

        mock_tool_a = MagicMock()
        mock_tool_a.name = "get_entity_state"
        mock_tool_a.ainvoke = tool_a

        mock_tool_b = MagicMock()
        mock_tool_b.name = "search_entities"
        mock_tool_b.ainvoke = tool_b

        tool_calls = [
            ParsedToolCall(name="get_entity_state", args={}, id="call-1", is_mutating=False),
            ParsedToolCall(name="search_entities", args={}, id="call-2", is_mutating=False),
        ]
        tool_lookup = {"get_entity_state": mock_tool_a, "search_entities": mock_tool_b}

        events = []
        async for event in dispatch_tool_calls(
            tool_calls=tool_calls,
            tool_lookup=tool_lookup,
            conversation_id="conv-1",
        ):
            events.append(dict(event))

        assert order == ["a", "b"]
        tool_starts = [e for e in events if e["type"] == "tool_start"]
        assert len(tool_starts) == 2
