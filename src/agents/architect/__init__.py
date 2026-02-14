"""Architect agent package.

Re-exports the public API for backwards compatibility:
- ``ArchitectAgent`` -- the core agent
- ``ArchitectWorkflow`` -- conversation orchestration
- ``StreamEvent`` -- streaming event type
"""

from src.agents.architect.agent import ArchitectAgent
from src.agents.architect.stream_event import StreamEvent
from src.agents.architect.workflow import ArchitectWorkflow

__all__ = [
    "ArchitectAgent",
    "ArchitectWorkflow",
    "StreamEvent",
]
