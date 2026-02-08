"""Global activity SSE stream.

Provides a Server-Sent Events endpoint that broadcasts system activity
events (LLM call start/end, agent activations) to all connected frontend
clients. This allows the activity panel to react to ANY LLM call in the
system, not just chat streaming.

Architecture:
    src/llm.py  -->  publish_activity()  -->  asyncio.Queue per client
                                          -->  SSE endpoint reads queue
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])

# ─── In-process broadcast ─────────────────────────────────────────────────────

_subscribers: set[asyncio.Queue] = set()


def publish_activity(event: dict) -> None:
    """Publish an activity event to all connected SSE clients.

    Safe to call from any async or sync context (fire-and-forget).
    """
    event.setdefault("ts", time.time())
    data = json.dumps(event)
    dead: list[asyncio.Queue] = []
    for q in _subscribers:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.discard(q)


async def _subscribe() -> AsyncGenerator[str, None]:
    """Subscribe to activity events as an SSE stream."""
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.add(q)
    try:
        while True:
            data = await q.get()
            yield f"data: {data}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _subscribers.discard(q)


@router.get("/stream")
async def activity_stream():
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
