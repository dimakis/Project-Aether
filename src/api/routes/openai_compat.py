"""OpenAI-compatible API for chat completions.

Provides an OpenAI-compatible `/v1/chat/completions` endpoint
for integration with Open WebUI and other OpenAI-compatible clients.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from src.agents import ArchitectWorkflow
from src.dal import ConversationRepository, MessageRepository
from src.graph.state import ConversationState
from src.storage import get_session
from src.tracing.context import session_context

router = APIRouter(tags=["OpenAI Compatible"])


# --- Request/Response Models ---


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


class ModelsResponse(BaseModel):
    """List models response."""

    object: str = "list"
    data: list[ModelInfo]


# --- Endpoints ---


@router.get("/models")
async def list_models() -> ModelsResponse:
    """List available LLM models.

    Dynamically discovers available models from:
    - Ollama (local models - if running)
    - Configured provider (openrouter, openai, google)
    
    Results are cached for 5 minutes.
    All models power the Architect agent with Home Assistant tools.
    """
    from src.api.services.model_discovery import get_model_discovery
    
    discovery = get_model_discovery()
    models = await discovery.discover_all()
    
    return ModelsResponse(
        data=[
            ModelInfo(
                id=model.id,
                owned_by=model.provider,
            )
            for model in models
        ]
    )


@router.post("/chat/completions", response_model=None)
async def create_chat_completion(
    request: ChatCompletionRequest,
):
    """Create a chat completion.

    OpenAI-compatible endpoint for chat completions.
    Supports both streaming and non-streaming modes.
    """
    if request.stream:
        return StreamingResponse(
            _stream_chat_completion(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await _create_chat_completion(request)


async def _create_chat_completion(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse:
    """Process non-streaming chat completion."""
    async with get_session() as session:
        # Get or create conversation - use stable ID derived from messages
        # This ensures Open WebUI conversations stay grouped in MLflow
        conversation_id = request.conversation_id or _derive_conversation_id(request.messages)

        with session_context(conversation_id):
            # Convert OpenAI messages to LangChain messages
            lc_messages = _convert_to_langchain_messages(request.messages)

            # Extract last user message
            user_message = ""
            for msg in reversed(request.messages):
                if msg.role == "user" and msg.content:
                    user_message = msg.content
                    break

            if not user_message:
                raise HTTPException(status_code=400, detail="No user message found")

            # Create state from messages
            state = ConversationState(
                conversation_id=conversation_id,
                messages=lc_messages[:-1],  # All but last user message
            )

            # Process with Architect (using requested LLM model)
            workflow = ArchitectWorkflow(
                model_name=request.model,
                temperature=request.temperature,
            )
            state = await workflow.continue_conversation(
                state=state,
                user_message=user_message,
                session=session,
            )

            # Get response
            assistant_content = ""
            if state.messages:
                for msg in reversed(state.messages):
                    if isinstance(msg, AIMessage):
                        assistant_content = msg.content
                        break

            await session.commit()

        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=assistant_content or "I'm processing your request...",
                    ),
                    finish_reason="stop",
                )
            ],
        )


async def _stream_chat_completion(
    request: ChatCompletionRequest,
) -> AsyncGenerator[str, None]:
    """Generate streaming chat completion (SSE format).

    Yields Server-Sent Events in the OpenAI format:
    data: {"id": "...", "object": "chat.completion.chunk", ...}
    """
    completion_id = f"chatcmpl-{uuid4().hex[:8]}"
    created = int(time.time())

    try:
        async with get_session() as session:
            # Use stable ID derived from messages for MLflow session correlation
            conversation_id = request.conversation_id or _derive_conversation_id(request.messages)

            with session_context(conversation_id):
                # Convert messages
                lc_messages = _convert_to_langchain_messages(request.messages)

                # Extract last user message
                user_message = ""
                for msg in reversed(request.messages):
                    if msg.role == "user" and msg.content:
                        user_message = msg.content
                        break

                if not user_message:
                    yield _format_sse_error("No user message found")
                    return

                # Create state
                state = ConversationState(
                    conversation_id=conversation_id,
                    messages=lc_messages[:-1],
                )

                # Process with Architect (using requested LLM model)
                workflow = ArchitectWorkflow(
                    model_name=request.model,
                    temperature=request.temperature,
                )
                state = await workflow.continue_conversation(
                    state=state,
                    user_message=user_message,
                    session=session,
                )

                # Get response content
                assistant_content = ""
                if state.messages:
                    for msg in reversed(state.messages):
                        if isinstance(msg, AIMessage):
                            assistant_content = msg.content
                            break

                # Stream the response in chunks
                # In a real implementation, we'd use the LLM's streaming capability
                # For now, we simulate streaming by chunking the response
                chunk_size = 10  # Characters per chunk

                for i in range(0, len(assistant_content), chunk_size):
                    chunk = assistant_content[i : i + chunk_size]

                    chunk_data = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": chunk},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for realistic streaming

                # Send final chunk with finish_reason
                final_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

                await session.commit()

    except Exception as e:
        yield _format_sse_error(str(e))


def _convert_to_langchain_messages(messages: list[ChatMessage]) -> list[Any]:
    """Convert OpenAI messages to LangChain format."""
    lc_messages = []

    for msg in messages:
        if msg.role == "system":
            lc_messages.append(SystemMessage(content=msg.content or ""))
        elif msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content or ""))
        elif msg.role == "assistant":
            if msg.tool_calls:
                lc_messages.append(
                    AIMessage(
                        content=msg.content or "",
                        tool_calls=msg.tool_calls,
                    )
                )
            else:
                lc_messages.append(AIMessage(content=msg.content or ""))
        elif msg.role == "tool":
            lc_messages.append(
                ToolMessage(
                    content=msg.content or "",
                    tool_call_id=msg.tool_call_id or "",
                )
            )

    return lc_messages


def _format_sse_error(error: str) -> str:
    """Format an error as SSE event."""
    error_data = {
        "error": {
            "message": error,
            "type": "api_error",
        }
    }
    return f"data: {json.dumps(error_data)}\n\n"


def _derive_conversation_id(messages: list[ChatMessage]) -> str:
    """Derive a stable conversation ID from message history.

    Open WebUI and other OpenAI-compatible clients don't send a conversation_id.
    Instead of generating a new UUID per request (which fragments MLflow traces),
    we derive a deterministic ID from the conversation fingerprint.

    Strategy: Hash the first user message content. This groups all messages
    in the same conversation under one MLflow session.

    Args:
        messages: List of chat messages

    Returns:
        Deterministic conversation ID (conv-<hash>)
    """
    # Find the first user message
    first_user_content = ""
    for msg in messages:
        if msg.role == "user" and msg.content:
            first_user_content = msg.content
            break

    if not first_user_content:
        # Fallback: use system message or generate new
        for msg in messages:
            if msg.role == "system" and msg.content:
                first_user_content = msg.content
                break

    if not first_user_content:
        return str(uuid4())

    # Create stable hash from first message
    content_hash = hashlib.sha256(first_user_content.encode()).hexdigest()[:12]
    return f"conv-{content_hash}"


__all__ = ["router"]
