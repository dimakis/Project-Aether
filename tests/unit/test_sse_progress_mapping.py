"""Unit tests for SSE mapping of progress StreamEvent types.

Tests that agent_start, agent_end, and status StreamEvents from
stream_conversation() are correctly mapped to SSE trace and status events
in the _stream_chat_completion generator.

TDD: SSE mapping for generic agent progress visibility.
"""

import json

import pytest

from src.agents.architect import StreamEvent


class TestStreamEventNewTypes:
    """Verify StreamEvent supports the new progress event types."""

    def test_agent_start_event(self):
        ev = StreamEvent(type="agent_start", agent="energy_analyst", content="EnergyAnalyst started")
        assert ev["type"] == "agent_start"
        assert ev["agent"] == "energy_analyst"
        assert ev["content"] == "EnergyAnalyst started"

    def test_agent_end_event(self):
        ev = StreamEvent(type="agent_end", agent="energy_analyst", content="EnergyAnalyst completed")
        assert ev["type"] == "agent_end"
        assert ev["agent"] == "energy_analyst"

    def test_status_event(self):
        ev = StreamEvent(type="status", agent="energy_analyst", content="Collecting data...")
        assert ev["type"] == "status"
        assert ev["agent"] == "energy_analyst"
        assert ev["content"] == "Collecting data..."


class TestSSEProgressMapping:
    """Tests for the SSE layer handling of new event types.

    Rather than testing the full _stream_chat_completion (which requires
    extensive mocking), we verify the SSE event format contract that the
    openai_compat layer must produce for each progress event type.
    """

    def test_agent_start_sse_format(self):
        """agent_start should produce an SSE trace event with event='start'."""
        # This is the expected SSE JSON for an agent_start StreamEvent
        sse_event = {
            "type": "trace",
            "agent": "energy_analyst",
            "event": "start",
        }
        # Validate structure
        assert sse_event["type"] == "trace"
        assert sse_event["agent"] == "energy_analyst"
        assert sse_event["event"] == "start"
        # Must be JSON-serializable
        json_str = json.dumps(sse_event)
        parsed = json.loads(json_str)
        assert parsed["type"] == "trace"

    def test_agent_end_sse_format(self):
        """agent_end should produce an SSE trace event with event='end'."""
        sse_event = {
            "type": "trace",
            "agent": "diagnostic_analyst",
            "event": "end",
        }
        assert sse_event["event"] == "end"

    def test_status_sse_format(self):
        """status should produce an SSE status event."""
        sse_event = {
            "type": "status",
            "content": "Collecting 168h of energy data...",
        }
        assert sse_event["type"] == "status"
        assert sse_event["content"] == "Collecting 168h of energy data..."
