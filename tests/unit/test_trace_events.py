"""Unit tests for _build_trace_events helper.

TDD: Tests the extraction of real-time trace events from completed
ConversationState for SSE streaming.
"""

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

    def test_tool_call_to_data_scientist(self):
        """When the Architect calls analyze_energy, Data Scientist events appear."""
        messages = [
            HumanMessage(content="Check my energy"),
            AIMessage(
                content="Let me analyze",
                tool_calls=[{"id": "call_1", "name": "analyze_energy", "args": {}}],
            ),
            ToolMessage(content="Analysis results...", tool_call_id="call_1"),
            AIMessage(content="Here are the results"),
        ]
        tool_calls = ["analyze_energy"]
        events = _build_trace_events(messages, tool_calls)

        # Should include data_scientist events
        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "architect" in agent_names
        assert "data_scientist" in agent_names

        # Complete event should list both agents
        complete = next(e for e in events if e["event"] == "complete")
        assert "architect" in complete["agents"]
        assert "data_scientist" in complete["agents"]

    def test_tool_call_to_custom_analysis(self):
        """run_custom_analysis maps to data_scientist agent."""
        messages = [
            HumanMessage(content="Analyze HVAC"),
            AIMessage(
                content="Running analysis",
                tool_calls=[{"id": "call_1", "name": "run_custom_analysis", "args": {}}],
            ),
            ToolMessage(content="Results", tool_call_id="call_1"),
            AIMessage(content="Done"),
        ]
        events = _build_trace_events(messages, ["run_custom_analysis"])

        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "data_scientist" in agent_names

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
                    {"id": "call_1", "name": "analyze_energy", "args": {}},
                    {"id": "call_2", "name": "create_insight_schedule", "args": {}},
                ],
            ),
            ToolMessage(content="Analysis done", tool_call_id="call_1"),
            ToolMessage(content="Schedule created", tool_call_id="call_2"),
            AIMessage(content="All done"),
        ]
        events = _build_trace_events(
            messages, ["analyze_energy", "create_insight_schedule"]
        )

        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "data_scientist" in agent_names
        assert "system" in agent_names

        complete = next(e for e in events if e["event"] == "complete")
        assert "architect" in complete["agents"]
        assert "data_scientist" in complete["agents"]
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

    def test_diagnose_issue_maps_to_data_scientist(self):
        """diagnose_issue maps to data_scientist agent."""
        messages = [
            HumanMessage(content="Why is sensor broken?"),
            AIMessage(
                content="Investigating",
                tool_calls=[{"id": "c1", "name": "diagnose_issue", "args": {}}],
            ),
            ToolMessage(content="Diagnosis", tool_call_id="c1"),
            AIMessage(content="Found the issue"),
        ]
        events = _build_trace_events(messages, ["diagnose_issue"])

        agent_names = [e.get("agent") for e in events if e.get("agent")]
        assert "data_scientist" in agent_names
