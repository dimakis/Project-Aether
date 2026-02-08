"""Unit tests for SSE activity stream graceful shutdown.

Tests that the _subscribe() generator exits cleanly when the shutdown
event is signaled, allowing uvicorn to complete its reload cycle.

TDD: SSE stream shutdown for uvicorn reload support.

Coordination uses asyncio.Event instead of fixed sleeps to avoid
flaky timing under CI load.
"""

import asyncio

import pytest

import src.api.routes.activity_stream as _mod
from src.api.routes.activity_stream import (
    _subscribers,
    publish_activity,
    signal_shutdown,
)


async def _wait_for_subscriber(timeout: float = 2.0) -> None:
    """Wait until at least one subscriber queue is registered.

    Uses a tight yield loop instead of a fixed sleep, so it resolves
    as soon as the generator adds itself to _subscribers.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while len(_subscribers) == 0:
        if asyncio.get_event_loop().time() > deadline:
            raise TimeoutError("Subscriber never registered")  # pragma: no cover
        await asyncio.sleep(0)


class TestActivityStreamShutdown:
    """Tests that SSE streams close when shutdown is signaled."""

    def setup_method(self):
        """Reset module state between tests."""
        _mod._shutting_down = False
        _subscribers.clear()

    @pytest.mark.asyncio
    async def test_subscribe_exits_on_shutdown_signal(self):
        """_subscribe() should exit promptly when signal_shutdown() is called."""
        from src.api.routes.activity_stream import _subscribe

        gen = _subscribe()

        async def fire_shutdown():
            await _wait_for_subscriber()
            signal_shutdown()

        shutdown_task = asyncio.create_task(fire_shutdown())

        items = []
        async for item in gen:
            items.append(item)  # pragma: no cover - should not yield

        await shutdown_task

        # Generator should have exited without yielding anything
        assert items == []

    @pytest.mark.asyncio
    async def test_subscribe_yields_events_before_shutdown(self):
        """Events published before shutdown should still be yielded."""
        from src.api.routes.activity_stream import _subscribe

        gen = _subscribe()
        event_consumed = asyncio.Event()

        async def consume():
            items_inner = []
            async for item in gen:
                items_inner.append(item)
                event_consumed.set()
            return items_inner

        async def publish_then_shutdown():
            await _wait_for_subscriber()
            publish_activity({"type": "test", "msg": "hello"})
            # Wait until the consumer has processed the event
            await asyncio.wait_for(event_consumed.wait(), timeout=2.0)
            signal_shutdown()

        consumer_task = asyncio.create_task(consume())
        publisher_task = asyncio.create_task(publish_then_shutdown())

        await publisher_task
        items = await consumer_task

        # Should have received the one event before shutdown
        assert len(items) == 1
        assert "hello" in items[0]

    @pytest.mark.asyncio
    async def test_subscriber_removed_on_shutdown(self):
        """After shutdown, the subscriber queue should be removed from the set."""
        from src.api.routes.activity_stream import _subscribe

        gen = _subscribe()

        async def fire_shutdown():
            await _wait_for_subscriber()
            signal_shutdown()

        task = asyncio.create_task(fire_shutdown())

        async for _ in gen:
            pass  # pragma: no cover

        await task

        # Subscriber should be cleaned up
        assert len(_subscribers) == 0

    @pytest.mark.asyncio
    async def test_shutdown_is_idempotent(self):
        """Calling signal_shutdown() multiple times should not error."""
        signal_shutdown()
        signal_shutdown()
        assert _mod._shutting_down is True

    @pytest.mark.asyncio
    async def test_subscribe_exits_immediately_if_already_shutdown(self):
        """If shutdown was already signaled, _subscribe() should exit immediately."""
        from src.api.routes.activity_stream import _subscribe

        signal_shutdown()

        items = []
        async for item in _subscribe():
            items.append(item)  # pragma: no cover

        assert items == []
