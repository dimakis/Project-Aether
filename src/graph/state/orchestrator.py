"""Orchestrator state for main graph."""

from typing import Any

from pydantic import Field

from .base import MessageState


class OrchestratorState(MessageState):
    """State for the main orchestrator graph.

    Routes requests to the appropriate sub-graph (discovery, conversation, analysis).
    """

    # Routing
    intent: str | None = Field(
        default=None,
        description="Detected user intent",
    )
    target_graph: str | None = Field(
        default=None,
        description="Sub-graph to invoke (discovery, conversation, analysis)",
    )

    # Sub-graph results
    discovery_result: dict[str, Any] | None = None
    conversation_result: dict[str, Any] | None = None
    analysis_result: dict[str, Any] | None = None

    # Error handling
    error: str | None = None
    error_traceback: str | None = None
