"""Persistent WebSocket subscription to HA event bus.

Feature 35: Real-Time HA Event Stream.

Maintains a persistent connection to Home Assistant's WebSocket API,
subscribing to state_changed events and dispatching them to a handler.
Reconnects with exponential backoff on connection loss.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import TYPE_CHECKING, Any

from websockets.asyncio.client import connect as ws_connect

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from src.exceptions import HAClientError
from src.ha.websocket import _authenticate

logger = logging.getLogger(__name__)

_BACKOFF_BASE = 1.0
_BACKOFF_MAX = 60.0
_BACKOFF_FACTOR = 2.0


class HAEventStream:
    """Persistent WebSocket subscription to HA state_changed events.

    Usage::

        stream = HAEventStream(ws_url, token, handler=my_handler)
        task = asyncio.create_task(stream.run())
        # ... later ...
        await stream.stop()
    """

    def __init__(
        self,
        ws_url: str,
        token: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        self._ws_url = ws_url
        self._token = token
        self._handler = handler
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._backoff = _BACKOFF_BASE

    async def run(self) -> None:
        """Main event loop with reconnection."""
        self._running = True
        while self._running:
            try:
                await self._connect_and_subscribe()
            except asyncio.CancelledError:
                break
            except Exception:
                if not self._running:
                    break
                logger.warning(
                    "Event stream disconnected, reconnecting in %.1fs",
                    self._backoff,
                )
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * _BACKOFF_FACTOR, _BACKOFF_MAX)

    async def _connect_and_subscribe(self) -> None:
        """Connect, authenticate, subscribe, and process events."""
        async with ws_connect(self._ws_url) as ws:
            await _authenticate(ws, self._token)
            logger.info("Event stream connected and authenticated")
            self._backoff = _BACKOFF_BASE

            subscribe_msg = {
                "id": 1,
                "type": "subscribe_events",
                "event_type": "state_changed",
            }
            await ws.send(json.dumps(subscribe_msg))
            raw = await ws.recv()
            msg = json.loads(raw)
            if not msg.get("success"):
                raise HAClientError("Failed to subscribe to events", tool="event_stream")
            logger.info("Subscribed to state_changed events")

            async for raw_msg in ws:
                if not self._running:
                    break
                try:
                    event = json.loads(raw_msg)
                    if event.get("type") == "event":
                        await self._handler(event.get("event", {}))
                except json.JSONDecodeError:
                    logger.warning("Failed to decode event: %s", raw_msg[:200])
                except Exception:
                    logger.exception("Error processing event")

    async def stop(self) -> None:
        """Stop the event stream."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Event stream stopped")

    def start_task(self) -> asyncio.Task[None]:
        """Start the event stream as a background task."""
        self._task = asyncio.create_task(self.run())
        return self._task

    @property
    def is_running(self) -> bool:
        return self._running


__all__ = ["HAEventStream"]
