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

from src.api.rate_limit import limiter

from src.agents import ArchitectWorkflow
from src.agents.model_context import model_context
from src.dal import ConversationRepository, MessageRepository
from src.graph.state import ConversationState
from src.storage import get_session
from src.tracing import start_experiment_run, log_param
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
@limiter.limit("10/minute")
async def create_chat_completion(
    request: Request,
    body: ChatCompletionRequest,
):
    """Create a chat completion.

    OpenAI-compatible endpoint for chat completions.
    Supports both streaming and non-streaming modes.

    Rate limited to 10/minute (LLM-backed).
    """
    if body.stream:
        return StreamingResponse(
            _stream_chat_completion(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await _create_chat_completion(body)


async def _create_chat_completion(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse:
    """Process non-streaming chat completion."""
    import mlflow

    async with get_session() as session:
        # Get or create conversation - use stable ID derived from messages
        # This ensures Open WebUI conversations stay grouped in MLflow
        conversation_id = request.conversation_id or _derive_conversation_id(request.messages)

        with session_context(conversation_id):
            # Create MLflow run for full observability (runs + nested traces)
            with start_experiment_run("conversation") as run:
                mlflow.set_tag("endpoint", "chat_completion")
                mlflow.set_tag("session.id", conversation_id)
                mlflow.set_tag("mlflow.trace.session", conversation_id)
                log_param("conversation_id", conversation_id)
                log_param("model", request.model)

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

                log_param("turn", (len(lc_messages) + 1) // 2)
                log_param("type", "continue_conversation")

                # Create state from messages
                state = ConversationState(
                    conversation_id=conversation_id,
                    messages=lc_messages[:-1],  # All but last user message
                )

                # Propagate user's model selection to all delegated agents
                with model_context(
                    model_name=request.model,
                    temperature=request.temperature,
                ):
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

                # Strip thinking/reasoning tags from output
                assistant_content = _strip_thinking_tags(assistant_content)

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
    import mlflow

    completion_id = f"chatcmpl-{uuid4().hex[:8]}"
    created = int(time.time())

    try:
        async with get_session() as session:
            # Use stable ID derived from messages for MLflow session correlation
            conversation_id = request.conversation_id or _derive_conversation_id(request.messages)

            with session_context(conversation_id):
                # Create MLflow run for full observability (runs + nested traces)
                with start_experiment_run("conversation") as run:
                    mlflow.set_tag("endpoint", "chat_completion_stream")
                    mlflow.set_tag("session.id", conversation_id)
                    mlflow.set_tag("mlflow.trace.session", conversation_id)
                    log_param("conversation_id", conversation_id)
                    log_param("model", request.model)

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

                    log_param("turn", (len(lc_messages) + 1) // 2)
                    log_param("type", "continue_conversation")

                    # Create state
                    state = ConversationState(
                        conversation_id=conversation_id,
                        messages=lc_messages[:-1],
                    )

                    # Propagate user's model selection to all delegated agents
                    with model_context(
                        model_name=request.model,
                        temperature=request.temperature,
                    ):
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

                    # Strip thinking/reasoning tags from output
                    assistant_content = _strip_thinking_tags(assistant_content)

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


def _strip_thinking_tags(content: str) -> str:
    """Strip LLM thinking/reasoning tags from response content.

    Many reasoning models (GPT-5, DeepSeek-R1, QwQ, etc.) include
    chain-of-thought in tags like <think>...</think>. These should
    not be sent to the end user as visible output.
    """
    import re
    
    thinking_tags = ["think", "thinking", "reasoning", "thought", "reflection"]
    pattern = "|".join(
        rf"<{tag}>[\s\S]*?</{tag}>"
        for tag in thinking_tags
    )
    cleaned = re.sub(pattern, "", content, flags=re.IGNORECASE)
    return cleaned.strip()


def _format_sse_error(error: str) -> str:
    """Format an error as SSE event."""
    error_data = {
        "error": {
            "message": error,
            "type": "api_error",
        }
    }
    return f"data: {json.dumps(error_data)}\n\n"


def _is_background_request(messages: list[ChatMessage]) -> bool:
    """Detect if this is a background request (title generation, suggestions).

    Open WebUI and similar clients send background requests that shouldn't
    be traced as part of the main conversation.

    Args:
        messages: List of chat messages

    Returns:
        True if this appears to be a background/meta request
    """
    # Check system messages for background task patterns
    background_patterns = [
        "generate a title",
        "generate title",
        "create a title",
        "summarize the conversation",
        "suggest follow-up",
        "generate suggestions",
        "create suggestions",
        "what questions",
        "follow up questions",
    ]
    
    for msg in messages:
        if msg.role == "system" and msg.content:
            content_lower = msg.content.lower()
            for pattern in background_patterns:
                if pattern in content_lower:
                    return True
    
    return False


def _derive_conversation_id(messages: list[ChatMessage]) -> str:
    """Derive a stable conversation ID from message history.

    Open WebUI and other OpenAI-compatible clients don't send a conversation_id.
    Instead of generating a new UUID per request (which fragments MLflow traces),
    we derive a deterministic UUID from the conversation fingerprint.

    Strategy: 
    - For background requests (title gen, suggestions): use random UUID
    - For main conversation: derive UUID from hash of first user message

    Args:
        messages: List of chat messages

    Returns:
        Valid UUID string (deterministic for conversations, random for background)
    """
    # Background requests get random UUIDs (ephemeral, won't clutter MLflow)
    if _is_background_request(messages):
        return str(uuid4())

    # Find the first user message for main conversations
    first_user_content = ""
    for msg in messages:
        if msg.role == "user" and msg.content:
            first_user_content = msg.content
            break

    if not first_user_content:
        return str(uuid4())

    # Create deterministic UUID from hash (UUID v5 style but simpler)
    # Take 32 hex chars from SHA256 and format as UUID
    content_hash = hashlib.sha256(first_user_content.encode()).hexdigest()[:32]
    # Format as UUID: 8-4-4-4-12
    uuid_str = f"{content_hash[:8]}-{content_hash[8:12]}-{content_hash[12:16]}-{content_hash[16:20]}-{content_hash[20:32]}"
    return uuid_str


__all__ = ["router"]
