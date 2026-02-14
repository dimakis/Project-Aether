"""Pydantic request/response models for OpenAI-compatible API."""

import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A chat message in OpenAI format."""

    role: str = Field(..., description="Message role: system, user, assistant, tool")
    content: str | None = Field(default=None, description="Message content")
    name: str | None = Field(default=None, description="Optional name for the message author")
    tool_calls: list[dict[str, Any]] | None = Field(default=None, description="Tool calls")
    tool_call_id: str | None = Field(default=None, description="Tool call ID for tool responses")


class ChatCompletionRequest(BaseModel):
    """OpenAI chat completion request."""

    model: str = Field(default="architect", description="Model to use (always architect)")
    messages: list[ChatMessage] = Field(..., description="Conversation messages")
    temperature: float | None = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = Field(default=False, description="Whether to stream responses")
    user: str | None = Field(default=None, description="User identifier")
    # Extra fields for conversation context
    conversation_id: str | None = Field(default=None, description="Existing conversation ID")


class ChatChoice(BaseModel):
    """A chat completion choice."""

    index: int
    message: ChatMessage
    finish_reason: str | None = None


class ChatChoiceDelta(BaseModel):
    """A streaming chat completion delta."""

    index: int
    delta: dict[str, Any]
    finish_reason: str | None = None


class Usage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI chat completion response."""

    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid4().hex[:8]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "architect"
    choices: list[ChatChoice]
    usage: Usage = Field(default_factory=Usage)


class ModelInfo(BaseModel):
    """Model information."""

    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "aether"
    input_cost_per_1m: float | None = None
    output_cost_per_1m: float | None = None


class ModelsResponse(BaseModel):
    """List models response."""

    object: str = "list"
    data: list[ModelInfo]


class FeedbackRequest(BaseModel):
    """Request body for submitting feedback on a trace."""

    trace_id: str = Field(..., description="MLflow trace ID to attach feedback to")
    sentiment: str = Field(..., description="Feedback sentiment: 'positive' or 'negative'")
