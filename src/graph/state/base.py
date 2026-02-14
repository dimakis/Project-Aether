"""Base state models for LangGraph agents."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field

from .enums import AgentRole


class BaseState(BaseModel):
    """Base state model with common fields.

    All graph states should inherit from this to ensure
    consistent tracing and identification.
    """

    run_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this graph run",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this graph run started",
    )
    current_agent: AgentRole | None = Field(
        default=None,
        description="Currently active agent (for tracing)",
    )


class MessageState(BaseState):
    """State model with message history.

    Uses LangGraph's add_messages reducer for proper message handling.
    """

    messages: Annotated[list[AnyMessage], add_messages] = Field(
        default_factory=list,
        description="Conversation message history",
    )
