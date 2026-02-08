"""Unit tests for SSE activity stream graceful shutdown.

Tests that the _subscribe() generator exits cleanly when the shutdown
event is signaled, allowing uvicorn to complete its reload cycle.

TDD: SSE stream shutdown for uvicorn reload support.
"""

import asyncio

import pytest

import src.api.routes.activity_stream as _mod
from src.api.routes.activity_stream import (
    _subscribers,
    publish_activity,
    signal_shutdown,
)


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
        # Schedule shutdown after a short delay
        async def fire_shutdown():
            await asyncio.sleep(0.05)
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

        async def publish_then_shutdown():
            await asyncio.sleep(0.02)
            publish_activity({"type": "test", "msg": "hello"})
            await asyncio.sleep(0.05)
            signal_shutdown()

        task = asyncio.create_task(publish_then_shutdown())

        items = []
        async for item in gen:
            items.append(item)

        await task

        # Should have received the one event before shutdown
        assert len(items) == 1
        assert "hello" in items[0]

    @pytest.mark.asyncio
    async def test_subscriber_removed_on_shutdown(self):
        """After shutdown, the subscriber queue should be removed from the set."""
        from src.api.routes.activity_stream import _subscribe

        gen = _subscribe()

        async def fire_shutdown():
            await asyncio.sleep(0.02)
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
