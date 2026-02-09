"""Global activity SSE stream.

Provides a Server-Sent Events endpoint that broadcasts system activity
events (LLM call start/end, agent activations) to all connected frontend
clients. This allows the activity panel to react to ANY LLM call in the
system, not just chat streaming.

Architecture:
    src/llm.py  -->  publish_activity()  -->  asyncio.Queue per client
                                          -->  SSE endpoint reads queue

Shutdown:
    Call signal_shutdown() during app shutdown to close all SSE connections
    promptly. Without this, open SSE connections block uvicorn's graceful
    shutdown (and therefore --reload).
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import suppress

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])

# ─── In-process broadcast ─────────────────────────────────────────────────────

_subscribers: set[asyncio.Queue[str | None]] = set()
_shutting_down = False


def signal_shutdown() -> None:
    """Signal all SSE subscribers to close.

    Call this during app shutdown (e.g. from the FastAPI lifespan)
    so that open SSE connections close and uvicorn can complete
    its graceful shutdown / reload cycle.

    Uses a plain boolean + sentinel queue messages instead of asyncio.Event
    to avoid cross-event-loop issues in tests.
    """
    global _shutting_down
    _shutting_down = True
    # Wake all subscribers so they see the flag
    for q in _subscribers:
        with suppress(asyncio.QueueFull):
            q.put_nowait(None)  # sentinel


def publish_activity(event: dict) -> None:
    """Publish an activity event to all connected SSE clients.

    Safe to call from any async or sync context (fire-and-forget).
    """
    event.setdefault("ts", time.time())
    data = json.dumps(event)
    dead: list[asyncio.Queue[str | None]] = []
    for q in _subscribers:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.discard(q)


async def _subscribe() -> AsyncGenerator[str, None]:
    """Subscribe to activity events as an SSE stream.

    Exits cleanly when signal_shutdown() is called, which sets
    _shutting_down=True and pushes a None sentinel into every queue.
    This allows uvicorn to proceed with graceful shutdown / reload.
    """
    q: asyncio.Queue[str | None] = asyncio.Queue(maxsize=200)
    _subscribers.add(q)
    try:
        while not _shutting_down:
            data = await q.get()
            if data is None:
                # Sentinel: shutdown signal
                break
            yield f"data: {data}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _subscribers.discard(q)


@router.get("/stream")
async def activity_stream() -> StreamingResponse:
    """SSE endpoint for global system activity events.

    Events include:
    - LLM call start/end with agent_role and model
    - Agent lifecycle events
    """
    return StreamingResponse(
        _subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
