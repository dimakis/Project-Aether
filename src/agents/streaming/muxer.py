"""Progress muxer — multiplex N progress queues into a single stream.

Enables parallel read-only tool execution by merging progress events from
multiple concurrent tool queues into a single ordered event stream using
asyncio non-blocking queue draining.

Feature 31, Phase 2 (optional): Parallel tool execution support.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from src.agents.execution_context import ProgressEvent


class ProgressMuxer:
    """Multiplex progress events from N asyncio queues.

    Drains all queues in a non-blocking round-robin fashion, yielding
    events as they arrive. The caller provides a ``done_check`` callable
    that returns True when all tool tasks have completed.

    Usage::

        q1, q2 = asyncio.Queue(), asyncio.Queue()
        muxer = ProgressMuxer([q1, q2])
        async for event in muxer.drain_until_done(done_check=lambda: all_tasks_done):
            yield StreamEvent(type=event.type, agent=event.agent, ...)
    """

    def __init__(self, queues: list[asyncio.Queue[ProgressEvent]]) -> None:
        self._queues = queues

    async def drain_until_done(
        self,
        *,
        done_check: Callable[[], bool],
        poll_interval: float = 0.05,
    ) -> AsyncGenerator[ProgressEvent, None]:
        """Drain all queues until done_check returns True and queues are empty.

        Args:
            done_check: Callable returning True when all tasks are complete.
            poll_interval: Seconds between polling cycles when queues are empty.

        Yields:
            ProgressEvent instances in arrival order.
        """
        if not self._queues:
            return

        while True:
            # Non-blocking drain of all queues
            drained_any = False
            for q in self._queues:
                while not q.empty():
                    try:
                        event = q.get_nowait()
                        yield event
                        drained_any = True
                    except asyncio.QueueEmpty:
                        break

            # If all tasks are done and queues are empty, we're finished
            if done_check() and not drained_any:
                # Final drain to catch any events added between check and drain
                for q in self._queues:
                    while not q.empty():
                        try:
                            yield q.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                return

            if not drained_any:
                await asyncio.sleep(poll_interval)
