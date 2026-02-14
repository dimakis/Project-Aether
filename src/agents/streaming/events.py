"""Stream event types for the streaming pipeline.

StreamEvent is the shared event type yielded by stream_conversation()
and consumed by the SSE layer in openai_compat.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.graph.state import ConversationState


class StreamEvent(dict[str, Any]):
    """A typed dict for streaming events from the workflow.

    Attributes:
        type: Event type (token, tool_start, tool_end, state, approval_required,
              agent_start, agent_end, status, delegation, trace_id)
        content: Text content (for token events)
        tool: Tool name (for tool events)
        agent: Agent name (for tool events)
        result: Tool result (for tool_end events)
        state: Final conversation state (for state events)
    """

    def __init__(
        self,
        type: str,
        content: str | None = None,
        tool: str | None = None,
        agent: str | None = None,
        result: str | None = None,
        state: ConversationState | None = None,
        **kwargs: object,
    ):
        super().__init__(
            type=type,
            content=content,
            tool=tool,
            agent=agent,
            result=result,
            state=state,
            **kwargs,
        )
