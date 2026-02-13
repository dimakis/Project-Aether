"""Unit tests for the agent communication log.

Tests T3334-T3336: CommunicationEntry model, TeamAnalysis.communication_log,
emit_communication helper, and communication log accumulation.
"""

from __future__ import annotations

from datetime import datetime

# =============================================================================
# T3334: CommunicationEntry model and communication_log on TeamAnalysis
# =============================================================================


class TestCommunicationEntry:
    """Test the CommunicationEntry model."""

    def test_create_entry(self):
        from src.graph.state import CommunicationEntry

        entry = CommunicationEntry(
            from_agent="energy_analyst",
            to_agent="team",
            message_type="finding",
            content="High overnight consumption detected",
        )
        assert entry.from_agent == "energy_analyst"
        assert entry.to_agent == "team"
        assert entry.message_type == "finding"
        assert entry.content == "High overnight consumption detected"
        assert entry.metadata == {}
        assert isinstance(entry.timestamp, datetime)

    def test_entry_with_metadata(self):
        from src.graph.state import CommunicationEntry

        entry = CommunicationEntry(
            from_agent="behavioral_analyst",
            to_agent="energy_analyst",
            message_type="cross_reference",
            content="Confirms activity spike at 2am",
            metadata={"confidence": 0.9, "entities": ["sensor.power"]},
        )
        assert entry.metadata["confidence"] == 0.9

    def test_valid_message_types(self):
        from src.graph.state import CommunicationEntry

        for msg_type in ["finding", "question", "cross_reference", "synthesis", "status"]:
            entry = CommunicationEntry(
                from_agent="a",
                to_agent="b",
                message_type=msg_type,
                content="test",
            )
            assert entry.message_type == msg_type


class TestTeamAnalysisCommunicationLog:
    """Test that TeamAnalysis includes a communication_log field."""

    def test_default_empty_log(self):
        from src.graph.state import TeamAnalysis

        ta = TeamAnalysis(request_id="r1", request_summary="test")
        assert ta.communication_log == []

    def test_add_entries(self):
        from src.graph.state import CommunicationEntry, TeamAnalysis

        ta = TeamAnalysis(request_id="r1", request_summary="test")
        entry = CommunicationEntry(
            from_agent="energy_analyst",
            to_agent="team",
            message_type="finding",
            content="test finding",
        )
        ta.communication_log.append(entry)
        assert len(ta.communication_log) == 1

    def test_entries_are_typed(self):
        from src.graph.state import CommunicationEntry, TeamAnalysis

        ta = TeamAnalysis(
            request_id="r1",
            request_summary="test",
            communication_log=[
                CommunicationEntry(
                    from_agent="a",
                    to_agent="b",
                    message_type="finding",
                    content="x",
                )
            ],
        )
        assert isinstance(ta.communication_log[0], CommunicationEntry)


# =============================================================================
# T3335: emit_communication helper on ExecutionContext
# =============================================================================


class TestEmitCommunication:
    """Test the emit_communication function."""

    def test_emit_appends_to_context(self):
        from src.agents.execution_context import (
            ExecutionContext,
            emit_communication,
            set_execution_context,
        )

        ctx = ExecutionContext()
        set_execution_context(ctx)

        try:
            emit_communication(
                from_agent="energy_analyst",
                to_agent="team",
                message_type="finding",
                content="Found spike",
            )

            assert len(ctx.communication_log) == 1
            entry = ctx.communication_log[0]
            assert entry["from_agent"] == "energy_analyst"
            assert entry["to_agent"] == "team"
            assert entry["message_type"] == "finding"
            assert entry["content"] == "Found spike"
            assert "timestamp" in entry
        finally:
            set_execution_context(None)

    def test_emit_with_metadata(self):
        from src.agents.execution_context import (
            ExecutionContext,
            emit_communication,
            set_execution_context,
        )

        ctx = ExecutionContext()
        set_execution_context(ctx)

        try:
            emit_communication(
                from_agent="a",
                to_agent="b",
                message_type="cross_reference",
                content="ref",
                metadata={"confidence": 0.8},
            )

            assert ctx.communication_log[0]["metadata"]["confidence"] == 0.8
        finally:
            set_execution_context(None)

    def test_emit_noop_without_context(self):
        """emit_communication should not raise when no context is active."""
        from src.agents.execution_context import emit_communication, set_execution_context

        set_execution_context(None)
        # Should not raise
        emit_communication(
            from_agent="a",
            to_agent="b",
            message_type="finding",
            content="test",
        )

    def test_multiple_emissions(self):
        from src.agents.execution_context import (
            ExecutionContext,
            emit_communication,
            set_execution_context,
        )

        ctx = ExecutionContext()
        set_execution_context(ctx)

        try:
            for i in range(5):
                emit_communication(
                    from_agent=f"agent_{i}",
                    to_agent="team",
                    message_type="finding",
                    content=f"Finding {i}",
                )

            assert len(ctx.communication_log) == 5
            assert ctx.communication_log[2]["from_agent"] == "agent_2"
        finally:
            set_execution_context(None)
