"""In-memory log of recent HITL notification action responses.

Used by the HITL test page to show whether the user tapped
Approve or Reject on their phone/watch.  The webhook handler
records actions here, and the test page polls for them.

Only keeps the most recent 50 entries.  Not persisted -- this
is purely a debugging/testing aid.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

_MAX_ENTRIES = 50
_lock = Lock()


@dataclass
class ActionEntry:
    """A recorded notification action."""

    proposal_id: str
    action: str  # "approve" or "reject"
    status: str  # "success", "not_found", "error"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "action": self.action,
            "status": self.status,
            "timestamp": self.timestamp,
        }


_log: deque[ActionEntry] = deque(maxlen=_MAX_ENTRIES)


def record_action(proposal_id: str, action: str, status: str) -> None:
    """Record a notification action for the test UI."""
    with _lock:
        _log.append(ActionEntry(proposal_id=proposal_id, action=action, status=status))


def get_action_for_proposal(proposal_id: str) -> ActionEntry | None:
    """Find the most recent action for a given proposal ID."""
    with _lock:
        for entry in reversed(_log):
            if entry.proposal_id == proposal_id:
                return entry
    return None


def get_recent_actions(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent actions, newest first."""
    with _lock:
        entries = list(_log)
    entries.reverse()
    return [e.to_dict() for e in entries[:limit]]
