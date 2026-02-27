"""Structured job event helpers for the global activity SSE stream.

Thin wrappers around :func:`publish_activity` that emit standardized
``type: "job"`` events.  All helpers are fire-and-forget with zero DB
cost — they only push to the in-memory SSE broadcast.

Event format::

    {
        "type": "job",
        "event": "start" | "agent_start" | "status" | "agent_end" | "complete" | "failed",
        "job_id": "...",
        "job_type": "chat" | "optimization" | "analysis" | "schedule" | "webhook" | "evaluation",
        "title": "...",
        "agent": "...",
        "message": "...",
        "ts": 1234567890.0,
    }
"""

from __future__ import annotations

import logging
import time
from typing import Literal

logger = logging.getLogger(__name__)

JobType = Literal["chat", "optimization", "analysis", "schedule", "webhook", "evaluation"]


def _publish(event: dict[str, object]) -> None:
    """Publish to the global activity stream, swallowing import/runtime errors."""
    try:
        from src.api.routes.activity_stream import publish_activity

        publish_activity(event)
    except Exception:
        logger.debug("Failed to publish job event", exc_info=True)


def emit_job_start(job_id: str, job_type: JobType, title: str) -> None:
    """Emit a job start event."""
    _publish(
        {
            "type": "job",
            "event": "start",
            "job_id": job_id,
            "job_type": job_type,
            "title": title,
            "ts": time.time(),
        }
    )


def emit_job_agent(job_id: str, agent: str, event: Literal["start", "end"]) -> None:
    """Emit an agent lifecycle event within a job."""
    _publish(
        {
            "type": "job",
            "event": f"agent_{event}",
            "job_id": job_id,
            "agent": agent,
            "ts": time.time(),
        }
    )


def emit_job_status(job_id: str, message: str) -> None:
    """Emit a free-form status update for a job."""
    _publish(
        {
            "type": "job",
            "event": "status",
            "job_id": job_id,
            "message": message,
            "ts": time.time(),
        }
    )


def emit_job_complete(job_id: str) -> None:
    """Emit a job completion event."""
    _publish(
        {
            "type": "job",
            "event": "complete",
            "job_id": job_id,
            "ts": time.time(),
        }
    )


def emit_job_failed(job_id: str, error: str) -> None:
    """Emit a job failure event."""
    _publish(
        {
            "type": "job",
            "event": "failed",
            "job_id": job_id,
            "error": error,
            "ts": time.time(),
        }
    )
