"""Unit tests for trace event helpers and SSE emission.

TDD: Tests the extraction of real-time trace events from completed
ConversationState for SSE streaming, and their integration with
_stream_chat_completion.
"""

import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.api.routes.openai_compat import _build_trace_events

# ---------------------------------------------------------------------------
# _build_trace_events
# ---------------------------------------------------------------------------


class TestBuildTraceEvents:
    """_build_trace_events extracts structured trace events from state messages
    for the agent activity panel."""

    def test_simple_response_no_tools(self):
        """A simple Architect response with no tool calls produces minimal events."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]
        events = _build_trace_events(messages, [])

        # Should have: architect start, architect end, complete
        assert len(events) >= 2
        assert events[0]["type"] == "trace"
        assert events[0]["agent"] == "architect"
        assert events[0]["event"] == "start"

        # Last event is complete
        assert events[-1]["event"] == "complete"
        assert "architect" in events[-1]["agents"]

    def test_tool_call_to_data_science_team(self):
        """When the Architect calls consult_data_science_team, DS team events appear."""
        messages = [
            HumanMessage(content="Check my energy"),
            AIMessage(
                content="Let me analyze",
                tool_calls=[{"id": "call_1", "name": "consult_data_science_team", "args": {}}],
            ),
            ToolMessage(content="Analysis results...", tool_call_id="call_1"),
            AIMessage(content="Here are the results"),
        ]
        tool_calls = ["consult_data_science_team"]
        events = _build_trace_events(messages, tool_calls)

        # Should include data_science_team events
        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "architect" in agent_names
        assert "data_science_team" in agent_names

        # Complete event should list both agents
        complete = next(e for e in events if e["event"] == "complete")
        assert "architect" in complete["agents"]
        assert "data_science_team" in complete["agents"]

    def test_tool_call_to_librarian(self):
        """discover_entities maps to librarian agent."""
        messages = [
            HumanMessage(content="Discover devices"),
            AIMessage(
                content="Running discovery",
                tool_calls=[{"id": "call_1", "name": "discover_entities", "args": {}}],
            ),
            ToolMessage(content="Results", tool_call_id="call_1"),
            AIMessage(content="Done"),
        ]
        events = _build_trace_events(messages, ["discover_entities"])

        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "librarian" in agent_names

    def test_schedule_creation_maps_to_system(self):
        """create_insight_schedule maps to system agent."""
        messages = [
            HumanMessage(content="Schedule daily check"),
            AIMessage(
                content="Creating schedule",
                tool_calls=[{"id": "call_1", "name": "create_insight_schedule", "args": {}}],
            ),
            ToolMessage(content="Created", tool_call_id="call_1"),
            AIMessage(content="Done"),
        ]
        events = _build_trace_events(messages, ["create_insight_schedule"])

        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "system" in agent_names

    def test_seek_approval_maps_to_system(self):
        """seek_approval maps to system agent."""
        messages = [
            HumanMessage(content="Turn on lights"),
            AIMessage(
                content="Submitting",
                tool_calls=[{"id": "call_1", "name": "seek_approval", "args": {}}],
            ),
            ToolMessage(content="Submitted", tool_call_id="call_1"),
            AIMessage(content="Done"),
        ]
        events = _build_trace_events(messages, ["seek_approval"])

        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "system" in agent_names

    def test_ha_tools_stay_under_architect(self):
        """HA query tools (get_entity_state, etc.) don't create separate agent events."""
        messages = [
            HumanMessage(content="What's the living room temp?"),
            AIMessage(
                content="Checking",
                tool_calls=[{"id": "call_1", "name": "get_entity_state", "args": {}}],
            ),
            ToolMessage(content="22.5°C", tool_call_id="call_1"),
            AIMessage(content="It's 22.5°C"),
        ]
        events = _build_trace_events(messages, ["get_entity_state"])

        # Only architect and complete events — no separate agent
        agent_names = [e.get("agent") for e in events if e.get("agent")]
        unique_agents = set(agent_names)
        assert unique_agents == {"architect"}

        # tool_call event should still appear
        tool_events = [e for e in events if e.get("event") == "tool_call"]
        assert len(tool_events) >= 1
        assert tool_events[0]["tool"] == "get_entity_state"

    def test_multiple_tool_calls(self):
        """Multiple tool calls produce events for each."""
        messages = [
            HumanMessage(content="Analyze energy and create schedule"),
            AIMessage(
                content="Working on it",
                tool_calls=[
                    {"id": "call_1", "name": "consult_data_science_team", "args": {}},
                    {"id": "call_2", "name": "create_insight_schedule", "args": {}},
                ],
            ),
            ToolMessage(content="Analysis done", tool_call_id="call_1"),
            ToolMessage(content="Schedule created", tool_call_id="call_2"),
            AIMessage(content="All done"),
        ]
        events = _build_trace_events(
            messages, ["consult_data_science_team", "create_insight_schedule"]
        )

        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "data_science_team" in agent_names
        assert "system" in agent_names

        complete = next(e for e in events if e["event"] == "complete")
        assert "architect" in complete["agents"]
        assert "data_science_team" in complete["agents"]
        assert "system" in complete["agents"]

    def test_all_events_have_type_trace(self):
        """Every event has type='trace'."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi"),
        ]
        events = _build_trace_events(messages, [])

        for event in events:
            assert event["type"] == "trace"

    def test_all_events_have_ts(self):
        """Every event has a numeric ts field."""
        messages = [
            HumanMessage(content="Check energy"),
            AIMessage(
                content="Analyzing",
                tool_calls=[{"id": "c1", "name": "analyze_energy", "args": {}}],
            ),
            ToolMessage(content="Results", tool_call_id="c1"),
            AIMessage(content="Done"),
        ]
        events = _build_trace_events(messages, ["analyze_energy"])

        for event in events:
            assert "ts" in event
            assert isinstance(event["ts"], (int, float))

    def test_timestamps_are_monotonically_increasing(self):
        """Timestamps should be non-decreasing."""
        messages = [
            HumanMessage(content="Check energy"),
            AIMessage(
                content="Analyzing",
                tool_calls=[{"id": "c1", "name": "analyze_energy", "args": {}}],
            ),
            ToolMessage(content="Results", tool_call_id="c1"),
            AIMessage(content="Done"),
        ]
        events = _build_trace_events(messages, ["analyze_energy"])

        timestamps = [e["ts"] for e in events]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1]

    def test_empty_messages(self):
        """Empty messages should produce minimal events."""
        events = _build_trace_events([], [])

        # At minimum: architect start, complete
        assert len(events) >= 2
        assert events[0]["event"] == "start"
        assert events[-1]["event"] == "complete"

    def test_unmapped_tool_stays_on_architect(self):
        """Tools not in TOOL_AGENT_MAP stay under the architect agent."""
        messages = [
            HumanMessage(content="Why is sensor broken?"),
            AIMessage(
                content="Investigating",
                tool_calls=[{"id": "c1", "name": "get_entity_state", "args": {}}],
            ),
            ToolMessage(content="State data", tool_call_id="c1"),
            AIMessage(content="Found the issue"),
        ]
        events = _build_trace_events(messages, ["get_entity_state"])

        agent_names = [e.get("agent") for e in events if e.get("agent")]
        unique_agents = set(agent_names)
        assert unique_agents == {"architect"}


# ---------------------------------------------------------------------------
# _stream_chat_completion — trace event emission
# ---------------------------------------------------------------------------


class TestStreamEmitsTraceEvents:
    """Verify that _stream_chat_completion emits trace SSE events
    before text chunks when the request is NOT a background request."""

    @staticmethod
    @contextmanager
    def _mock_stream(stream_events, completed_state=None):
        """Context manager that mocks all _stream_chat_completion dependencies.

        Args:
            stream_events: list of dicts that workflow.stream_conversation yields.
            completed_state: optional ConversationState to attach as final state event.
        """
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        async def _fake_stream_conversation(state, user_message, session):
            for ev in stream_events:
                yield ev
            if completed_state:
                yield {"type": "state", "state": completed_state}

        mock_workflow = MagicMock()
        mock_workflow.stream_conversation = _fake_stream_conversation

        with (
            patch("src.api.routes.openai_compat.handlers.get_session") as mock_gs,
            patch("src.api.routes.openai_compat.handlers.start_experiment_run") as mock_run,
            patch("src.api.routes.openai_compat.handlers.session_context"),
            patch("src.api.routes.openai_compat.handlers.model_context"),
            patch(
                "src.api.routes.openai_compat.handlers.ArchitectWorkflow",
                return_value=mock_workflow,
            ),
            patch("src.api.routes.openai_compat.handlers.log_param"),
        ):
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            yield

    @staticmethod
    async def _collect_sse(request) -> list[dict]:
        """Collect and parse all SSE events from a stream."""
        from src.api.routes.openai_compat import _stream_chat_completion

        raw_events: list[str] = []
        async for sse_line in _stream_chat_completion(request):
            raw_events.append(sse_line)

        parsed = []
        for ev in raw_events:
            if ev.startswith("data: ") and not ev.startswith("data: [DONE]"):
                raw = ev.removeprefix("data: ").strip()
                parsed.append(json.loads(raw))
        return parsed

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore")
    async def test_trace_events_before_text_chunks(self):
        """Trace events appear before text delta chunks in the stream."""
        from src.api.routes.openai_compat import (
            ChatCompletionRequest,
            ChatMessage,
        )

        request = ChatCompletionRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Hello world")],
            stream=True,
        )

        completed_state = MagicMock()
        completed_state.last_trace_id = "trace-abc-123"

        stream_events = [
            {"type": "token", "content": "Hi there!"},
        ]

        with self._mock_stream(stream_events, completed_state):
            parsed = await self._collect_sse(request)

        trace_events = [p for p in parsed if p.get("type") == "trace"]
        text_chunks = [
            p
            for p in parsed
            if p.get("object") == "chat.completion.chunk"
            and p.get("choices", [{}])[0].get("delta", {}).get("content")
        ]

        # Trace events should exist (architect start, architect end, complete)
        assert len(trace_events) >= 2, f"Expected trace events, got {trace_events}"

        # Trace events should appear BEFORE text chunks in the stream
        first_trace_idx = parsed.index(trace_events[0])
        first_text_idx = parsed.index(text_chunks[0]) if text_chunks else len(parsed)
        assert first_trace_idx < first_text_idx, "Trace events must come before text chunks"

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore")
    async def test_no_trace_events_for_background_request(self):
        """Background requests (title gen) should not emit trace events."""
        from src.api.routes.openai_compat import (
            ChatCompletionRequest,
            ChatMessage,
        )

        request = ChatCompletionRequest(
            model="test-model",
            messages=[
                ChatMessage(role="system", content="Generate a title for this conversation."),
                ChatMessage(role="user", content="Hello world"),
            ],
            stream=True,
        )

        completed_state = MagicMock()
        completed_state.last_trace_id = None

        stream_events = [
            {"type": "token", "content": "Chat Title"},
        ]

        with self._mock_stream(stream_events, completed_state):
            parsed = await self._collect_sse(request)

        trace_events = [p for p in parsed if p.get("type") == "trace"]
        assert len(trace_events) == 0, (
            f"Background requests should not emit traces, got {trace_events}"
        )

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore")
    async def test_trace_events_include_tool_agent(self):
        """When tools are used, trace events include the delegated agent."""
        from src.api.routes.openai_compat import (
            ChatCompletionRequest,
            ChatMessage,
        )

        request = ChatCompletionRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="Analyze energy")],
            stream=True,
        )

        completed_state = MagicMock()
        completed_state.last_trace_id = "trace-xyz"

        stream_events = [
            {"type": "tool_start", "tool": "consult_data_science_team"},
            {"type": "tool_end", "tool": "consult_data_science_team"},
            {"type": "token", "content": "Here are the results"},
        ]

        with self._mock_stream(stream_events, completed_state):
            parsed = await self._collect_sse(request)

        trace_events = [p for p in parsed if p.get("type") == "trace"]
        agents = [e.get("agent") for e in trace_events if e.get("agent")]
        assert "data_science_team" in agents
        assert "architect" in agents

        # Complete event has both agents
        complete = next(e for e in trace_events if e["event"] == "complete")
        assert "architect" in complete["agents"]
        assert "data_science_team" in complete["agents"]
