"""A2A streaming event translator (Phase 4).

Translates A2A protocol events (TaskStatusUpdateEvent,
TaskArtifactUpdateEvent) into the StreamEvent dicts that the
existing SSE handler understands.

Used by the gateway when DEPLOYMENT_MODE=distributed to proxy
streaming responses from a remote Architect service back to
the frontend.
"""

from __future__ import annotations

import logging
from typing import Any

from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
)

from src.agents.streaming.events import StreamEvent

logger = logging.getLogger(__name__)


def translate_a2a_event(event: Any) -> StreamEvent | None:
    """Translate an A2A event into a StreamEvent.

    Args:
        event: An A2A TaskStatusUpdateEvent, TaskArtifactUpdateEvent,
               or unknown type.

    Returns:
        A StreamEvent dict, or None if the event type is unrecognized.
    """
    if isinstance(event, TaskStatusUpdateEvent):
        return _translate_status(event)
    if isinstance(event, TaskArtifactUpdateEvent):
        return _translate_artifact(event)
    return None


def _translate_status(event: TaskStatusUpdateEvent) -> StreamEvent:
    """Translate a task status update."""
    state = event.status.state if event.status else TaskState.unknown

    if state == TaskState.working:
        return StreamEvent(type="status", content="Agent working...")
    if state == TaskState.completed:
        return StreamEvent(type="state")
    if state == TaskState.failed:
        msg = ""
        if event.status and event.status.message:
            msg = str(event.status.message)
        return StreamEvent(type="error", content=msg or "Agent execution failed")
    if state == TaskState.input_required:
        return StreamEvent(type="approval_required", content="Input required")

    return StreamEvent(type="status", content=f"Agent status: {state}")


def _translate_artifact(event: TaskArtifactUpdateEvent) -> StreamEvent:
    """Translate a task artifact update.

    Handles three artifact formats:
    - TextPart: token content from streaming LLM output
    - DataPart with ``type`` key: forwarded StreamEvent (tool/agent/thinking events)
    - DataPart without ``type``: legacy tool result
    """
    if not event.artifact or not event.artifact.parts:
        return StreamEvent(type="status", content="Empty artifact received")

    for part in event.artifact.parts:
        inner = part.root if hasattr(part, "root") else part

        if hasattr(inner, "text") and inner.text:
            return StreamEvent(type="token", content=str(inner.text))

        if hasattr(inner, "data") and isinstance(inner.data, dict):
            data = inner.data
            if "type" in data:
                return StreamEvent(**{k: v for k, v in data.items() if v is not None})
            return StreamEvent(
                type="_tool_result",
                result=str(data),
                content=str(data),
            )

    return StreamEvent(type="status", content="Unrecognized artifact format")
