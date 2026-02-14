"""Unit tests for StreamEvent in its new streaming package location.

Verifies that StreamEvent can be imported from src.agents.streaming.events
and retains its dict-like behaviour and all event type constructors.
"""

from src.agents.streaming.events import StreamEvent
from src.graph.state import ConversationState


class TestStreamEvent:
    """Verify StreamEvent construction and dict-like behaviour."""

    def test_token_event(self):
        ev = StreamEvent(type="token", content="Hello")
        assert ev["type"] == "token"
        assert ev["content"] == "Hello"
        assert ev["tool"] is None

    def test_tool_start_event(self):
        ev = StreamEvent(type="tool_start", tool="analyze_energy", agent="data_scientist")
        assert ev["type"] == "tool_start"
        assert ev["tool"] == "analyze_energy"
        assert ev["agent"] == "data_scientist"

    def test_tool_end_event(self):
        ev = StreamEvent(type="tool_end", tool="analyze_energy", result="ok")
        assert ev["type"] == "tool_end"
        assert ev["result"] == "ok"

    def test_state_event(self):
        state = ConversationState(messages=[])
        ev = StreamEvent(type="state", state=state)
        assert ev["type"] == "state"
        assert ev["state"] is state

    def test_approval_event(self):
        ev = StreamEvent(type="approval_required", tool="execute_service", content="Need approval")
        assert ev["type"] == "approval_required"
        assert ev["tool"] == "execute_service"
        assert ev["content"] == "Need approval"

    def test_agent_start_event(self):
        ev = StreamEvent(
            type="agent_start", agent="energy_analyst", content="EnergyAnalyst started"
        )
        assert ev["type"] == "agent_start"
        assert ev["agent"] == "energy_analyst"

    def test_agent_end_event(self):
        ev = StreamEvent(type="agent_end", agent="energy_analyst", content="done")
        assert ev["type"] == "agent_end"

    def test_status_event(self):
        ev = StreamEvent(type="status", agent="energy_analyst", content="Collecting data...")
        assert ev["type"] == "status"
        assert ev["content"] == "Collecting data..."

    def test_trace_id_event(self):
        ev = StreamEvent(type="trace_id", content="abc-123")
        assert ev["type"] == "trace_id"
        assert ev["content"] == "abc-123"

    def test_kwargs_forwarded(self):
        ev = StreamEvent(type="tool_start", tool="t", target="some_agent")
        assert ev["target"] == "some_agent"


class TestStreamEventImportBackcompat:
    """Verify backward-compatible import from src.agents.architect still works."""

    def test_import_from_architect(self):
        from src.agents.architect import StreamEvent as ArchStreamEvent

        ev = ArchStreamEvent(type="token", content="hi")
        assert ev["type"] == "token"

    def test_import_from_agents_init(self):
        from src.agents import StreamEvent as InitStreamEvent

        ev = InitStreamEvent(type="token", content="hi")
        assert ev["type"] == "token"
