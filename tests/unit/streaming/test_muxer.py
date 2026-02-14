"""Unit tests for ProgressMuxer — multiplexes N progress queues.

Phase 4 of Feature 31: Streaming Tool Executor Refactor.
"""

import asyncio

import pytest

from src.agents.execution_context import ProgressEvent


class TestProgressMuxer:
    """Tests for ProgressMuxer — multiplexes progress events from N queues."""

    @pytest.mark.asyncio
    async def test_single_queue(self):
        """Events from a single queue should be yielded in order."""
        from src.agents.streaming.muxer import ProgressMuxer

        q = asyncio.Queue()
        q.put_nowait(ProgressEvent(type="agent_start", agent="a", message="start"))
        q.put_nowait(ProgressEvent(type="agent_end", agent="a", message="end"))

        muxer = ProgressMuxer([q])
        events = []
        async for event in muxer.drain_until_done(done_check=lambda: True):
            events.append(event)

        assert len(events) == 2
        assert events[0].type == "agent_start"
        assert events[1].type == "agent_end"

    @pytest.mark.asyncio
    async def test_two_queues_interleaved(self):
        """Events from two queues should be interleaved in arrival order."""
        from src.agents.streaming.muxer import ProgressMuxer

        q1 = asyncio.Queue()
        q2 = asyncio.Queue()

        q1.put_nowait(ProgressEvent(type="agent_start", agent="a", message="a start"))
        q2.put_nowait(ProgressEvent(type="agent_start", agent="b", message="b start"))
        q1.put_nowait(ProgressEvent(type="agent_end", agent="a", message="a end"))
        q2.put_nowait(ProgressEvent(type="agent_end", agent="b", message="b end"))

        muxer = ProgressMuxer([q1, q2])
        events = []
        async for event in muxer.drain_until_done(done_check=lambda: True):
            events.append(event)

        # All 4 events should be collected
        assert len(events) == 4
        agents = [e.agent for e in events]
        assert "a" in agents
        assert "b" in agents

    @pytest.mark.asyncio
    async def test_empty_queues(self):
        """Empty queues with done_check returning True should yield nothing."""
        from src.agents.streaming.muxer import ProgressMuxer

        q = asyncio.Queue()
        muxer = ProgressMuxer([q])
        events = []
        async for event in muxer.drain_until_done(done_check=lambda: True):
            events.append(event)

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_no_queues(self):
        """Muxer with no queues should yield nothing."""
        from src.agents.streaming.muxer import ProgressMuxer

        muxer = ProgressMuxer([])
        events = []
        async for event in muxer.drain_until_done(done_check=lambda: True):
            events.append(event)

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_concurrent_producers(self):
        """Events from concurrent async producers should all be collected."""
        from src.agents.streaming.muxer import ProgressMuxer

        q1 = asyncio.Queue()
        q2 = asyncio.Queue()
        tasks_done = [False, False]

        async def producer(queue, agent_name, task_idx):
            for i in range(3):
                await asyncio.sleep(0.01)
                queue.put_nowait(
                    ProgressEvent(type="status", agent=agent_name, message=f"step {i}")
                )
            tasks_done[task_idx] = True

        t1 = asyncio.create_task(producer(q1, "a", 0))
        t2 = asyncio.create_task(producer(q2, "b", 1))

        muxer = ProgressMuxer([q1, q2])
        events = []
        async for event in muxer.drain_until_done(
            done_check=lambda: all(tasks_done),
            poll_interval=0.02,
        ):
            events.append(event)

        await t1
        await t2

        # Should have all 6 events
        assert len(events) == 6
        a_events = [e for e in events if e.agent == "a"]
        b_events = [e for e in events if e.agent == "b"]
        assert len(a_events) == 3
        assert len(b_events) == 3
