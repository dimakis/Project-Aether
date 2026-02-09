"""Unit tests for BaseAgent auto-emit of progress events via execution context.

Tests that BaseAgent.trace_span() automatically emits agent_start/agent_end
progress events to the active execution context's queue.

TDD: BaseAgent lifecycle hooks for generic agent progress emission.
"""

import asyncio

import pytest

from src.agents import BaseAgent
from src.agents.execution_context import (
    ProgressEvent,
    clear_execution_context,
    execution_context,
)
from src.graph.state import AgentRole, BaseState


class StubAgent(BaseAgent):
    """Concrete BaseAgent subclass for testing."""

    async def invoke(self, state, **kwargs):
        async with self.trace_span("test_op", state):
            pass
        return {"status": "ok"}


class FailingAgent(BaseAgent):
    """Agent whose invoke raises inside trace_span."""

    async def invoke(self, state, **kwargs):
        async with self.trace_span("failing_op", state):
            raise RuntimeError("deliberate failure")
        return {}  # pragma: no cover


class TestBaseAgentAutoEmit:
    """Tests that trace_span emits progress events to execution context."""

    @pytest.fixture
    def agent(self):
        return StubAgent(role=AgentRole.ENERGY_ANALYST, name="EnergyAnalyst")

    @pytest.fixture
    def failing_agent(self):
        return FailingAgent(role=AgentRole.DIAGNOSTIC_ANALYST, name="DiagnosticAnalyst")

    @pytest.fixture
    def state(self):
        return BaseState(current_agent=AgentRole.ENERGY_ANALYST)

    @pytest.mark.asyncio
    async def test_emits_start_and_end_on_success(self, agent, state):
        """trace_span should emit agent_start then agent_end on success."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        async with execution_context(progress_queue=queue):
            await agent.invoke(state)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        # Should have exactly 2 events: start + end
        assert len(events) == 2
        assert events[0].type == "agent_start"
        assert events[0].agent == "energy_analyst"
        assert "EnergyAnalyst" in events[0].message

        assert events[1].type == "agent_end"
        assert events[1].agent == "energy_analyst"
        assert "EnergyAnalyst" in events[1].message

    @pytest.mark.asyncio
    async def test_emits_start_and_end_on_error(self, failing_agent, state):
        """trace_span should emit agent_start + agent_end even on exception."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        async with execution_context(progress_queue=queue):
            with pytest.raises(RuntimeError, match="deliberate failure"):
                await failing_agent.invoke(state)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        assert len(events) == 2
        assert events[0].type == "agent_start"
        assert events[0].agent == "diagnostic_analyst"

        assert events[1].type == "agent_end"
        assert events[1].agent == "diagnostic_analyst"

    @pytest.mark.asyncio
    async def test_no_emit_without_execution_context(self, agent, state):
        """trace_span should not raise when no execution context is active."""
        clear_execution_context()
        # Should not raise — emit_progress is a noop without context
        await agent.invoke(state)

    @pytest.mark.asyncio
    async def test_no_emit_without_queue(self, agent, state):
        """trace_span should not raise when context has no queue."""
        async with execution_context(conversation_id="no-queue"):
            # No progress_queue — should not raise
            await agent.invoke(state)

    @pytest.mark.asyncio
    async def test_timestamps_ordered(self, agent, state):
        """Start event ts should be <= end event ts."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        async with execution_context(progress_queue=queue):
            await agent.invoke(state)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        assert events[0].ts <= events[1].ts
