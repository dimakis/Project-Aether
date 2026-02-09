"""Unit tests for agent execution context propagation.

Tests the ExecutionContext, ProgressEvent, context manager, and emit_progress helper.

TDD: Execution context infrastructure for generic agent progress/session/task propagation.
"""

import asyncio
import time

import pytest

from src.agents.execution_context import (
    ExecutionContext,
    ProgressEvent,
    clear_execution_context,
    emit_progress,
    execution_context,
    get_execution_context,
    set_execution_context,
)


class TestProgressEvent:
    """Tests for the ProgressEvent dataclass."""

    def test_default_timestamp(self):
        """ProgressEvent should auto-populate ts from time.time()."""
        before = time.time()
        event = ProgressEvent(type="status", agent="energy_analyst", message="test")
        after = time.time()
        assert before <= event.ts <= after

    def test_explicit_values(self):
        """ProgressEvent should store provided values."""
        event = ProgressEvent(
            type="agent_start",
            agent="diagnostic_analyst",
            message="DiagnosticAnalyst started",
            ts=1000.0,
        )
        assert event.type == "agent_start"
        assert event.agent == "diagnostic_analyst"
        assert event.message == "DiagnosticAnalyst started"
        assert event.ts == 1000.0

    def test_valid_types(self):
        """ProgressEvent type must be one of the allowed literals."""
        # These should work without error
        for t in ("agent_start", "agent_end", "status"):
            event = ProgressEvent(type=t, agent="test", message="msg")
            assert event.type == t


class TestExecutionContext:
    """Tests for the ExecutionContext dataclass."""

    def test_default_values(self):
        """ExecutionContext should have sensible defaults."""
        ctx = ExecutionContext()
        assert ctx.progress_queue is None
        assert ctx.session_factory is None
        assert ctx.conversation_id is None
        assert ctx.task_label is None
        assert ctx.tool_timeout == 30.0
        assert ctx.analysis_timeout == 180.0

    def test_with_values(self):
        """ExecutionContext should store provided values."""
        queue = asyncio.Queue()
        factory = lambda: None  # noqa: E731 — dummy for test

        ctx = ExecutionContext(
            progress_queue=queue,
            session_factory=factory,
            conversation_id="conv-123",
            task_label="Diagnostic Analysis",
            tool_timeout=15.0,
            analysis_timeout=300.0,
        )
        assert ctx.progress_queue is queue
        assert ctx.session_factory is factory
        assert ctx.conversation_id == "conv-123"
        assert ctx.task_label == "Diagnostic Analysis"
        assert ctx.tool_timeout == 15.0
        assert ctx.analysis_timeout == 300.0


class TestExecutionContextManager:
    """Tests for the execution_context() async context manager."""

    @pytest.mark.asyncio
    async def test_sets_and_clears_context(self):
        """Context manager should set and restore previous context."""
        assert get_execution_context() is None

        async with execution_context(conversation_id="test-conv") as ctx:
            active = get_execution_context()
            assert active is not None
            assert active.conversation_id == "test-conv"
            assert active is ctx

        # Restored to None
        assert get_execution_context() is None

    @pytest.mark.asyncio
    async def test_nested_contexts(self):
        """Nested context managers should save/restore correctly."""
        async with execution_context(conversation_id="outer"):
            assert get_execution_context().conversation_id == "outer"

            async with execution_context(conversation_id="inner"):
                assert get_execution_context().conversation_id == "inner"

            # Outer restored
            assert get_execution_context().conversation_id == "outer"

        assert get_execution_context() is None

    @pytest.mark.asyncio
    async def test_yields_context_with_queue(self):
        """Context manager should create a progress queue when requested."""
        queue = asyncio.Queue()
        async with execution_context(progress_queue=queue) as ctx:
            assert ctx.progress_queue is queue

    @pytest.mark.asyncio
    async def test_restores_on_exception(self):
        """Context should be restored even if body raises."""
        assert get_execution_context() is None

        with pytest.raises(ValueError):
            async with execution_context(conversation_id="will-fail"):
                assert get_execution_context() is not None
                raise ValueError("test error")

        assert get_execution_context() is None


class TestSetAndClearContext:
    """Tests for set_execution_context and clear_execution_context."""

    def test_set_execution_context(self):
        """set_execution_context should update the active context."""
        try:
            ctx = ExecutionContext(conversation_id="set-test")
            set_execution_context(ctx)
            assert get_execution_context() is ctx
        finally:
            clear_execution_context()

    def test_clear_execution_context(self):
        """clear_execution_context should reset to None."""
        try:
            set_execution_context(ExecutionContext(conversation_id="to-clear"))
            clear_execution_context()
            assert get_execution_context() is None
        finally:
            clear_execution_context()


class TestEmitProgress:
    """Tests for the emit_progress() convenience helper."""

    @pytest.mark.asyncio
    async def test_emit_when_queue_exists(self):
        """emit_progress should put event on queue when context has one."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        async with execution_context(progress_queue=queue):
            emit_progress("agent_start", "energy_analyst", "EnergyAnalyst started")

        assert not queue.empty()
        event = queue.get_nowait()
        assert event.type == "agent_start"
        assert event.agent == "energy_analyst"
        assert event.message == "EnergyAnalyst started"

    @pytest.mark.asyncio
    async def test_emit_without_context_is_noop(self):
        """emit_progress should silently do nothing when no context is active."""
        clear_execution_context()
        # Should not raise
        emit_progress("status", "test", "nothing happens")

    @pytest.mark.asyncio
    async def test_emit_without_queue_is_noop(self):
        """emit_progress should silently do nothing when context has no queue."""
        async with execution_context(conversation_id="no-queue"):
            # No progress_queue set — should not raise
            emit_progress("status", "test", "nothing happens")

    @pytest.mark.asyncio
    async def test_multiple_events_ordered(self):
        """Multiple emit_progress calls should maintain order."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        async with execution_context(progress_queue=queue):
            emit_progress("agent_start", "energy_analyst", "start")
            emit_progress("status", "energy_analyst", "collecting data")
            emit_progress("agent_end", "energy_analyst", "done")

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        assert len(events) == 3
        assert events[0].type == "agent_start"
        assert events[1].type == "status"
        assert events[2].type == "agent_end"
        assert events[0].ts <= events[1].ts <= events[2].ts
