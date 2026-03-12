"""Tests for HAEventStream persistent WebSocket subscription.

Feature 35: Real-Time HA Event Stream.
Covers connection, authentication, subscription, reconnection with
exponential backoff, event dispatch, and graceful shutdown.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.ha.event_stream import (
    _BACKOFF_BASE,
    _BACKOFF_FACTOR,
    _BACKOFF_MAX,
    HAEventStream,
)

WS_URL = "ws://homeassistant.local:8123/api/websocket"
TOKEN = "test-token-abc123"


class _AsyncCtx:
    """Wrap an object for ``async with ws_connect(...) as ws``."""

    def __init__(self, obj: Any) -> None:
        self._obj = obj

    async def __aenter__(self) -> Any:
        return self._obj

    async def __aexit__(self, *args: Any) -> None:
        pass


def _make_ws(
    messages: list[dict[str, Any]],
    *,
    hang_after: int | None = None,
) -> AsyncMock:
    """Mock WebSocket that yields predefined messages then optionally hangs.

    Args:
        messages: Responses to return from recv().
        hang_after: After this many recv() calls, block forever (simulates disconnect).
    """
    call_count = 0

    async def _recv() -> str:
        nonlocal call_count
        call_count += 1
        idx = call_count - 1
        if hang_after is not None and call_count > hang_after:
            await asyncio.sleep(999)
            return "{}"
        if idx < len(messages):
            return json.dumps(messages[idx])
        raise ConnectionError("Connection closed")

    ws = AsyncMock()
    ws.recv = _recv
    ws.send = AsyncMock()

    async def _aiter_impl(_self: object = None) -> Any:
        """Make ``async for msg in ws`` work by delegating to recv()."""
        while True:
            try:
                yield await _recv()
            except (ConnectionError, asyncio.CancelledError):
                return

    ws.__aiter__ = _aiter_impl
    return ws


class TestHAEventStreamConnect:
    """Connection and authentication tests."""

    @pytest.mark.asyncio
    async def test_connect_authenticate_subscribe(self) -> None:
        """Happy path: auth -> subscribe -> receive event -> dispatch."""
        received: list[dict[str, Any]] = []

        async def handler(event: dict[str, Any]) -> None:
            received.append(event)

        event_msg = {
            "type": "event",
            "event": {
                "event_type": "state_changed",
                "data": {"entity_id": "light.living_room", "new_state": {"state": "on"}},
            },
        }

        ws = _make_ws(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_ok", "ha_version": "2025.1.0"},
                {"id": 1, "type": "result", "success": True},
                event_msg,
            ]
        )

        stream = HAEventStream(WS_URL, TOKEN, handler=handler)

        with patch("src.ha.event_stream.ws_connect", return_value=_AsyncCtx(ws)):
            task = asyncio.create_task(stream.run())
            await asyncio.sleep(0.05)
            await stream.stop()
            await asyncio.sleep(0.01)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        auth_call = ws.send.call_args_list[0]
        auth_msg = json.loads(auth_call[0][0])
        assert auth_msg["type"] == "auth"
        assert auth_msg["access_token"] == TOKEN

        sub_call = ws.send.call_args_list[1]
        sub_msg = json.loads(sub_call[0][0])
        assert sub_msg["type"] == "subscribe_events"
        assert sub_msg["event_type"] == "state_changed"

        assert len(received) >= 1
        assert received[0]["event_type"] == "state_changed"

    @pytest.mark.asyncio
    async def test_subscribe_failure_triggers_reconnect(self) -> None:
        """Subscribe failure should trigger reconnect with backoff."""
        handler = AsyncMock()
        sleep_calls: list[float] = []

        async def _fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)
            raise asyncio.CancelledError

        ws = _make_ws(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_ok", "ha_version": "2025.1.0"},
                {"id": 1, "type": "result", "success": False, "error": {"message": "fail"}},
            ]
        )

        stream = HAEventStream(WS_URL, TOKEN, handler=handler)

        with (
            patch("src.ha.event_stream.ws_connect", return_value=_AsyncCtx(ws)),
            patch("asyncio.sleep", side_effect=_fake_sleep),
        ):
            task = asyncio.create_task(stream.run())
            with contextlib.suppress(asyncio.CancelledError):
                await task

        assert len(sleep_calls) >= 1
        assert sleep_calls[0] == _BACKOFF_BASE


class TestHAEventStreamReconnect:
    """Exponential backoff reconnection tests."""

    @pytest.mark.asyncio
    async def test_backoff_doubles_on_failure(self) -> None:
        """Backoff should increase: 1s -> 2s -> 4s."""
        handler = AsyncMock()
        stream = HAEventStream(WS_URL, TOKEN, handler=handler)

        sleep_calls: list[float] = []

        async def _fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)
            if len(sleep_calls) >= 3:
                raise asyncio.CancelledError

        with (
            patch(
                "src.ha.event_stream.ws_connect",
                side_effect=ConnectionError("refused"),
            ),
            patch("asyncio.sleep", side_effect=_fake_sleep),
        ):
            task = asyncio.create_task(stream.run())
            with contextlib.suppress(asyncio.CancelledError):
                await task

        assert len(sleep_calls) >= 3
        assert sleep_calls[0] == _BACKOFF_BASE
        assert sleep_calls[1] == _BACKOFF_BASE * _BACKOFF_FACTOR
        assert sleep_calls[2] == _BACKOFF_BASE * _BACKOFF_FACTOR * _BACKOFF_FACTOR

    @pytest.mark.asyncio
    async def test_backoff_capped_at_max(self) -> None:
        """Backoff should never exceed _BACKOFF_MAX (60s)."""
        handler = AsyncMock()
        stream = HAEventStream(WS_URL, TOKEN, handler=handler)

        sleep_calls: list[float] = []

        async def _fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)
            if len(sleep_calls) >= 10:
                raise asyncio.CancelledError

        with (
            patch(
                "src.ha.event_stream.ws_connect",
                side_effect=ConnectionError("refused"),
            ),
            patch("asyncio.sleep", side_effect=_fake_sleep),
        ):
            task = asyncio.create_task(stream.run())
            with contextlib.suppress(asyncio.CancelledError):
                await task

        assert len(sleep_calls) >= 7  # enough to hit ceiling
        for delay in sleep_calls:
            assert delay <= _BACKOFF_MAX

    @pytest.mark.asyncio
    async def test_backoff_resets_on_successful_connect(self) -> None:
        """After a successful connection, backoff resets to base."""
        handler = AsyncMock()
        stream = HAEventStream(WS_URL, TOKEN, handler=handler)
        assert stream._backoff == _BACKOFF_BASE

        stream._backoff = 32.0

        ws = _make_ws(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_ok", "ha_version": "2025.1.0"},
                {"id": 1, "type": "result", "success": True},
            ]
        )

        with patch("src.ha.event_stream.ws_connect", return_value=_AsyncCtx(ws)):
            task = asyncio.create_task(stream.run())
            await asyncio.sleep(0.05)
            await stream.stop()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        assert stream._backoff == _BACKOFF_BASE


class TestHAEventStreamLifecycle:
    """Start/stop lifecycle tests."""

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self) -> None:
        """stop() should cancel the background task."""
        handler = AsyncMock()
        stream = HAEventStream(WS_URL, TOKEN, handler=handler)
        entered = asyncio.Event()
        _real_sleep = asyncio.sleep

        async def _blocking_sleep(delay: float) -> None:
            entered.set()
            await _real_sleep(999)

        with (
            patch(
                "src.ha.event_stream.ws_connect",
                side_effect=ConnectionError("refused"),
            ),
            patch("asyncio.sleep", side_effect=_blocking_sleep),
        ):
            task = stream.start_task()
            assert not task.done()
            await _real_sleep(0.05)
            await asyncio.wait_for(entered.wait(), timeout=2)
            await stream.stop()
            assert stream.is_running is False

    @pytest.mark.asyncio
    async def test_start_task_returns_task(self) -> None:
        """start_task() should return an asyncio.Task."""
        handler = AsyncMock()
        stream = HAEventStream(WS_URL, TOKEN, handler=handler)
        entered = asyncio.Event()
        _real_sleep = asyncio.sleep

        async def _blocking_sleep(delay: float) -> None:
            entered.set()
            await _real_sleep(999)

        with (
            patch(
                "src.ha.event_stream.ws_connect",
                side_effect=ConnectionError("refused"),
            ),
            patch("asyncio.sleep", side_effect=_blocking_sleep),
        ):
            task = stream.start_task()
            assert isinstance(task, asyncio.Task)
            await _real_sleep(0.05)
            await asyncio.wait_for(entered.wait(), timeout=2)
            await stream.stop()

    @pytest.mark.asyncio
    async def test_is_running_property(self) -> None:
        """is_running reflects stream state."""
        handler = AsyncMock()
        stream = HAEventStream(WS_URL, TOKEN, handler=handler)
        assert stream.is_running is False

        entered = asyncio.Event()
        _real_sleep = asyncio.sleep

        async def _blocking_sleep(delay: float) -> None:
            entered.set()
            await _real_sleep(999)

        with (
            patch(
                "src.ha.event_stream.ws_connect",
                side_effect=ConnectionError("refused"),
            ),
            patch("asyncio.sleep", side_effect=_blocking_sleep),
        ):
            stream.start_task()
            await _real_sleep(0.05)
            await asyncio.wait_for(entered.wait(), timeout=2)
            assert stream.is_running is True
            await stream.stop()
            assert stream.is_running is False

    @pytest.mark.asyncio
    async def test_non_event_messages_ignored(self) -> None:
        """Messages that aren't type='event' should be silently ignored."""
        received: list[dict[str, Any]] = []

        async def handler(event: dict[str, Any]) -> None:
            received.append(event)

        ws = _make_ws(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_ok", "ha_version": "2025.1.0"},
                {"id": 1, "type": "result", "success": True},
                {"type": "pong", "id": 2},
                {
                    "type": "event",
                    "event": {"event_type": "state_changed", "data": {"entity_id": "sensor.temp"}},
                },
            ]
        )

        stream = HAEventStream(WS_URL, TOKEN, handler=handler)

        with patch("src.ha.event_stream.ws_connect", return_value=_AsyncCtx(ws)):
            task = asyncio.create_task(stream.run())
            await asyncio.sleep(0.05)
            await stream.stop()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        assert len(received) == 1
        assert received[0]["event_type"] == "state_changed"
