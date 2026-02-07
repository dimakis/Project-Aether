"""Conversation API schemas.

Pydantic schemas for conversation and message endpoints - User Story 2.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    """Base schema for messages."""

    role: str = Field(max_length=20, description="Message role: user, assistant, system")
    content: str = Field(max_length=50_000, description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a message."""

    pass


class MessageResponse(MessageBase):
    """Schema for message response."""

    id: str = Field(description="Message UUID")
    conversation_id: str = Field(description="Parent conversation ID")
    tool_calls: dict | None = Field(
        default=None,
        description="Tool calls made by assistant",
    )
    tool_results: dict | None = Field(
        default=None,
        description="Results from tool calls",
    )
    tokens_used: int | None = Field(
        default=None,
        description="Token count",
    )
    latency_ms: int | None = Field(
        default=None,
        description="Response latency",
    )
    created_at: datetime = Field(description="Message timestamp")

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""

    title: str | None = Field(
        default=None,
        max_length=255,
        description="Optional conversation title",
    )
    initial_message: str = Field(
        max_length=50_000,
        description="Initial user message to start conversation",
    )
    context: dict | None = Field(
        default=None,
        description="Optional initial context",
    )


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    id: str = Field(description="Conversation UUID")
    agent_id: str = Field(description="Agent handling this conversation")
    user_id: str = Field(description="User identifier")
    title: str | None = Field(description="Conversation title")
    status: str = Field(description="Conversation status")
    context: dict | None = Field(description="Conversation context")
    created_at: datetime = Field(description="When started")
    updated_at: datetime = Field(description="Last activity")

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    """Schema for detailed conversation with messages."""

    messages: list[MessageResponse] = Field(
        default_factory=list,
        description="Conversation messages",
    )
    pending_approvals: list[str] = Field(
        default_factory=list,
        description="IDs of pending approval requests",
    )


class ConversationListResponse(BaseModel):
    """Schema for list of conversations."""

    items: list[ConversationResponse] = Field(description="Conversations")
    total: int = Field(description="Total count")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Current offset")


class ChatRequest(BaseModel):
    """Schema for sending a chat message."""

    message: str = Field(max_length=50_000, description="User message content")
    context: dict | None = Field(
        default=None,
        description="Additional context for this message",
    )


class ChatResponse(BaseModel):
    """Schema for chat response."""

    conversation_id: str = Field(description="Conversation ID")
    message: MessageResponse = Field(description="Assistant's response")
    has_proposal: bool = Field(
        default=False,
        description="Whether a proposal was generated",
    )
    proposal_id: str | None = Field(
        default=None,
        description="ID of generated proposal (if any)",
    )
    status: str = Field(description="Conversation status after this message")


class StreamChunk(BaseModel):
    """Schema for streaming response chunks."""

    type: str = Field(description="Chunk type: text, tool_call, proposal, done")
    content: str | None = Field(
        default=None,
        description="Text content (for text chunks)",
    )
    tool_call: dict | None = Field(
        default=None,
        description="Tool call info (for tool_call chunks)",
    )
    proposal: dict | None = Field(
        default=None,
        description="Proposal info (for proposal chunks)",
    )


# Exports
__all__ = [
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "ConversationCreate",
    "ConversationResponse",
    "ConversationDetailResponse",
    "ConversationListResponse",
    "ChatRequest",
    "ChatResponse",
    "StreamChunk",
]
