"""Streaming event types for the Architect workflow.

Re-exports StreamEvent from the canonical streaming module for backward compatibility.
"""

from src.agents.streaming.events import StreamEvent

__all__ = ["StreamEvent"]
