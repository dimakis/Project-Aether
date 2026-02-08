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

from src.agents import ArchitectWorkflow, StreamEvent
from src.agents.model_context import model_context
from src.dal import ConversationRepository, MessageRepository
from src.graph.state import ConversationState
from src.storage import get_session
from src.tracing import start_experiment_run, log_param
from src.tracing.context import session_context

router = APIRouter(tags=["OpenAI Compatible"])


# --- Agent mapping for tool calls (module-level for reuse in streaming) ---

TOOL_AGENT_MAP: dict[str, str] = {
    # DS Team (single delegation tool routes to specialists internally)
    "consult_data_science_team": "data_science_team",
    # Librarian
    "discover_entities": "librarian",
    # System / utility tools
    "create_insight_schedule": "system",
    "seek_approval": "system",
    # HA query tools (stay on architect)
    "get_entity_state": "architect",
    "list_entities_by_domain": "architect",
    "search_entities": "architect",
    "get_domain_summary": "architect",
    "list_automations": "architect",
    "render_template": "architect",
    "get_ha_logs": "architect",
    "check_ha_config": "architect",
}


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
    from src.llm_pricing import get_model_pricing

    discovery = get_model_discovery()
    models = await discovery.discover_all()

    data: list[ModelInfo] = []
    for model in models:
        pricing = get_model_pricing(model.id)
        data.append(
            ModelInfo(
                id=model.id,
                owned_by=model.provider,
                input_cost_per_1m=pricing["input_per_1m"] if pricing else None,
                output_cost_per_1m=pricing["output_per_1m"] if pricing else None,
            )
        )

    return ModelsResponse(data=data)


@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest):
    """Submit thumbs up/down feedback for a chat response.

    Logs user sentiment against the MLflow trace for model evaluation.
    """
    import mlflow

    if body.sentiment not in ("positive", "negative"):
        raise HTTPException(
            status_code=400,
            detail="sentiment must be 'positive' or 'negative'",
        )

    try:
        mlflow.log_feedback(
            trace_id=body.trace_id,
            name="user_sentiment",
            value=body.sentiment,
            source="human",
        )
    except Exception:
        # mlflow.log_feedback may not be available in older MLflow versions.
        # Fall back to updating the trace tags directly.
        try:
            client = mlflow.MlflowClient()
            client.set_trace_tag(body.trace_id, "user_sentiment", body.sentiment)
        except Exception as e:
            from src.api.utils import sanitize_error

            raise HTTPException(
                status_code=500,
                detail=sanitize_error(e, context="Log feedback"),
            ) from e

    return {"status": "ok"}


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

                # Normalize content (handle list, None, etc.)
                assistant_content = _extract_text_content(assistant_content)

                # Strip thinking/reasoning tags for non-streaming clients
                # (Open WebUI and other external clients that lack thinking-tag UI)
                assistant_content = _strip_thinking_tags(assistant_content)

                if not assistant_content.strip():
                    assistant_content = (
                        "I processed your request but couldn't generate a visible response. "
                        "Please try again."
                    )

                # Capture trace ID from the state (set by _traced_invoke)
                trace_id = state.last_trace_id

                await session.commit()

        response = ChatCompletionResponse(
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
        # Include trace_id as extra metadata in the response
        result = response.model_dump()
        if trace_id:
            result["trace_id"] = trace_id
        return result


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
                        workflow = ArchitectWorkflow(
                            model_name=request.model,
                            temperature=request.temperature,
                        )

                        is_background = _is_background_request(request.messages)
                        tool_calls_used: list[str] = []
                        final_state: ConversationState | None = None
                        full_content = ""
                        trace_id: str | None = None
                        tag_filter = _StreamingTagFilter()

                        # --- Agent lifecycle tracking for the activity panel ---
                        active_delegated: str | None = None
                        agents_seen: list[str] = ["architect"]
                        stream_started = False

                        def _make_token_chunk(tok: str) -> str:
                            """Build an SSE line for a single token delta."""
                            return "data: " + json.dumps({
                                "id": completion_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": request.model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": tok},
                                    "finish_reason": None,
                                }],
                            }) + "\n\n"

                        # --- Real token-by-token streaming ---
                        async for event in workflow.stream_conversation(
                            state=state,
                            user_message=user_message,
                            session=session,
                        ):
                            event_type = event.get("type")

                            # --- Emit architect start on first meaningful event ---
                            if not stream_started and not is_background:
                                stream_started = True
                                yield f"data: {json.dumps({'type': 'trace', 'agent': 'architect', 'event': 'start', 'ts': time.time()})}\n\n"

                            if event_type == "token":
                                raw_token = event.get("content", "")
                                full_content += raw_token
                                # Separate visible content from thinking
                                for ft in tag_filter.feed(raw_token):
                                    if not ft.text:
                                        continue
                                    if ft.is_thinking:
                                        yield f"data: {json.dumps({'type': 'thinking', 'content': ft.text})}\n\n"
                                    else:
                                        yield _make_token_chunk(ft.text)

                            elif event_type == "trace_id":
                                # Early trace_id — emit immediately so
                                # the activity panel can start polling
                                trace_id = event.get("content", "")
                                if trace_id:
                                    early_meta = {
                                        "type": "metadata",
                                        "trace_id": trace_id,
                                    }
                                    yield f"data: {json.dumps(early_meta)}\n\n"

                            elif event_type == "tool_start":
                                tool_name = event.get("tool", "")
                                tool_calls_used.append(tool_name)
                                if not is_background:
                                    target = TOOL_AGENT_MAP.get(tool_name, "architect")

                                    # --- Agent lifecycle: delegate to new agent ---
                                    if target != "architect" and target != active_delegated:
                                        # End previous delegated agent if any
                                        if active_delegated:
                                            yield f"data: {json.dumps({'type': 'trace', 'agent': active_delegated, 'event': 'end', 'ts': time.time()})}\n\n"
                                        # Start new delegated agent
                                        yield f"data: {json.dumps({'type': 'trace', 'agent': target, 'event': 'start', 'ts': time.time()})}\n\n"
                                        active_delegated = target
                                        if target not in agents_seen:
                                            agents_seen.append(target)

                                    trace_ev = {
                                        "type": "trace",
                                        "agent": target,
                                        "event": "tool_call",
                                        "tool": tool_name,
                                        "ts": time.time(),
                                    }
                                    yield f"data: {json.dumps(trace_ev)}\n\n"
                                    # Status event for UI
                                    status_ev = {
                                        "type": "status",
                                        "content": f"Running {tool_name}...",
                                    }
                                    yield f"data: {json.dumps(status_ev)}\n\n"

                            elif event_type == "tool_end":
                                if not is_background:
                                    # --- Agent lifecycle: end delegated agent ---
                                    if active_delegated:
                                        yield f"data: {json.dumps({'type': 'trace', 'agent': active_delegated, 'event': 'end', 'ts': time.time()})}\n\n"
                                        active_delegated = None
                                    status_ev = {
                                        "type": "status",
                                        "content": "",  # Clear status
                                    }
                                    yield f"data: {json.dumps(status_ev)}\n\n"

                            elif event_type == "agent_start":
                                # Progress: a sub-agent has started
                                agent_name = event.get("agent", "")
                                if not is_background and agent_name:
                                    # End previous delegated agent if different
                                    if active_delegated and active_delegated != agent_name:
                                        yield f"data: {json.dumps({'type': 'trace', 'agent': active_delegated, 'event': 'end', 'ts': time.time()})}\n\n"
                                    # Start new delegated agent
                                    yield f"data: {json.dumps({'type': 'trace', 'agent': agent_name, 'event': 'start', 'ts': time.time()})}\n\n"
                                    active_delegated = agent_name
                                    if agent_name not in agents_seen:
                                        agents_seen.append(agent_name)

                            elif event_type == "agent_end":
                                # Progress: a sub-agent has completed
                                agent_name = event.get("agent", "")
                                if not is_background and agent_name:
                                    yield f"data: {json.dumps({'type': 'trace', 'agent': agent_name, 'event': 'end', 'ts': time.time()})}\n\n"
                                    if active_delegated == agent_name:
                                        active_delegated = None

                            elif event_type == "status":
                                # Progress: status message from a sub-agent
                                status_content = event.get("content", "")
                                if not is_background and status_content:
                                    yield f"data: {json.dumps({'type': 'status', 'content': status_content})}\n\n"

                            elif event_type == "state":
                                final_state = event.get("state")

                            elif event_type == "approval_required":
                                # Emit as a text chunk so user sees the approval request
                                approval_text = event.get("content", "Approval required")
                                chunk_data = {
                                    "id": completion_id,
                                    "object": "chat.completion.chunk",
                                    "created": created,
                                    "model": request.model,
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {"content": approval_text},
                                            "finish_reason": None,
                                        }
                                    ],
                                }
                                yield f"data: {json.dumps(chunk_data)}\n\n"

                        # Flush any remaining buffered content from the tag filter
                        for ft in tag_filter.flush():
                            if not ft.text:
                                continue
                            if ft.is_thinking:
                                yield f"data: {json.dumps({'type': 'thinking', 'content': ft.text})}\n\n"
                            else:
                                yield _make_token_chunk(ft.text)

                    # --- Agent lifecycle: complete event ---
                    if stream_started and not is_background:
                        # End any still-active delegated agent
                        if active_delegated:
                            yield f"data: {json.dumps({'type': 'trace', 'agent': active_delegated, 'event': 'end', 'ts': time.time()})}\n\n"
                        # Architect end
                        yield f"data: {json.dumps({'type': 'trace', 'agent': 'architect', 'event': 'end', 'ts': time.time()})}\n\n"
                        # Complete event with all agents
                        yield f"data: {json.dumps({'type': 'trace', 'event': 'complete', 'agents': agents_seen, 'ts': time.time()})}\n\n"

                    # Use final state from stream, or fall back to original
                    state = final_state or state

                    # Capture trace ID from the state (set during streaming)
                    if not trace_id:
                        trace_id = state.last_trace_id

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

                    # Send metadata event with trace_id and tool calls before DONE
                    metadata: dict[str, object] = {
                        "type": "metadata",
                        "conversation_id": conversation_id,
                    }
                    if trace_id:
                        metadata["trace_id"] = trace_id
                    if tool_calls_used:
                        metadata["tool_calls"] = list(set(tool_calls_used))
                    yield f"data: {json.dumps(metadata)}\n\n"

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


def _extract_text_content(content: Any) -> str:
    """Normalize AIMessage.content to a plain string.

    LangChain's AIMessage.content can be:
    - str: normal text (most common)
    - list: structured content blocks, e.g. [{"type": "text", "text": "..."}]
    - None: empty response

    Args:
        content: Raw content from AIMessage

    Returns:
        Plain text string (may be empty)
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content") or ""
                if text:
                    parts.append(str(text))
        return "\n".join(parts)
    # Fallback: coerce to string
    return str(content)


# ─── Incremental thinking-tag filter for streaming ─────────────────────────

_THINKING_TAGS = ["think", "thinking", "reasoning", "thought", "reflection"]
_OPEN_TAGS = {f"<{t}>" for t in _THINKING_TAGS}
_CLOSE_TAGS = {f"</{t}>" for t in _THINKING_TAGS}
_MAX_TAG_LEN = max(len(t) for t in _OPEN_TAGS | _CLOSE_TAGS)


class FilteredToken:
    """A token emitted by ``_StreamingTagFilter`` with metadata."""

    __slots__ = ("text", "is_thinking")

    def __init__(self, text: str, *, is_thinking: bool = False) -> None:
        self.text = text
        self.is_thinking = is_thinking


class _StreamingTagFilter:
    """Incremental filter that separates thinking content from visible output.

    Feed token strings via ``feed()`` and iterate the yielded ``FilteredToken``
    items. Each item has ``text`` (the content) and ``is_thinking`` (whether it
    came from inside a thinking tag).

    Content outside thinking tags is yielded immediately, except for a small
    look-ahead buffer to detect tag boundaries.
    """

    def __init__(self) -> None:
        self._buf = ""
        self._suppressing = False

    # noinspection PyMethodMayBeStatic
    def _is_open_tag(self, text: str) -> str | None:
        low = text.lower()
        for tag in _OPEN_TAGS:
            if low.startswith(tag):
                return tag
        return None

    def _is_close_tag(self, text: str) -> str | None:
        low = text.lower()
        for tag in _CLOSE_TAGS:
            if low.startswith(tag):
                return tag
        return None

    def feed(self, token: str) -> list[FilteredToken]:
        """Feed a token and return list of ``FilteredToken`` items to emit."""
        self._buf += token
        out: list[FilteredToken] = []

        while self._buf:
            if self._suppressing:
                # Look for a closing tag in the buffer
                close = self._is_close_tag(self._buf)
                if close:
                    # Emit accumulated thinking content before the close tag
                    thought_text = self._buf[:self._buf.lower().index(close.lower())] if close.lower() in self._buf.lower() else ""
                    # Actually, the close tag sits at index 0 since we already
                    # consumed the open tag.  Emit the buffered thinking content.
                    self._buf = self._buf[len(close):]
                    self._suppressing = False
                    continue

                # Check if buffer *could* start with a partial close tag
                could_be_close = any(
                    self._buf.lower().startswith(t[:len(self._buf)])
                    for t in _CLOSE_TAGS
                    if len(self._buf) < len(t)
                )
                if could_be_close:
                    break  # Wait for more data

                # Not a close tag — emit the first char as thinking content
                out.append(FilteredToken(self._buf[0], is_thinking=True))
                self._buf = self._buf[1:]
                continue

            # --- Not suppressing ---

            # Check for an opening tag
            open_tag = self._is_open_tag(self._buf)
            if open_tag:
                self._buf = self._buf[len(open_tag):]
                self._suppressing = True
                continue

            # Could this be the start of an opening tag?  (e.g. "<thi")
            if "<" in self._buf:
                lt_pos = self._buf.index("<")
                # Emit everything before the '<'
                if lt_pos > 0:
                    out.append(FilteredToken(self._buf[:lt_pos]))
                    self._buf = self._buf[lt_pos:]

                # Check if the remainder could still become a thinking tag
                remainder = self._buf.lower()
                could_be_open = any(
                    t.startswith(remainder) for t in _OPEN_TAGS
                )
                if could_be_open and len(self._buf) < _MAX_TAG_LEN:
                    break  # Wait for more data

                # Not a thinking tag — emit the '<' and continue
                out.append(FilteredToken(self._buf[0]))
                self._buf = self._buf[1:]
                continue

            # No '<' at all — emit the entire buffer
            out.append(FilteredToken(self._buf))
            self._buf = ""

        return out

    def flush(self) -> list[FilteredToken]:
        """Flush any remaining buffered content (call at end of stream)."""
        if self._suppressing:
            # Still inside a thinking tag at end — emit as thinking
            if self._buf:
                result = [FilteredToken(self._buf, is_thinking=True)]
                self._buf = ""
                return result
            return []
        result = [FilteredToken(self._buf)] if self._buf else []
        self._buf = ""
        return result


def _strip_thinking_tags(content: str | list) -> str:
    """Strip LLM thinking/reasoning tags from response content.

    Many reasoning models (GPT-5, DeepSeek-R1, QwQ, etc.) include
    chain-of-thought in tags like <think>...</think>. These should
    not be sent to the end user as visible output.

    Handles:
    - Closed tag pairs: <think>...</think>
    - Unclosed tags: <think>... (model truncated or streaming artefact)
    - List content: [{"type": "text", "text": "..."}] from some providers
    """
    import re

    text = _extract_text_content(content)

    thinking_tags = ["think", "thinking", "reasoning", "thought", "reflection"]

    # First: strip closed tag pairs  <tag>...</tag>
    closed_pattern = "|".join(
        rf"<{tag}>[\s\S]*?</{tag}>"
        for tag in thinking_tags
    )
    text = re.sub(closed_pattern, "", text, flags=re.IGNORECASE)

    # Second: strip unclosed tags  <tag>...$ (no closing tag found)
    unclosed_pattern = "|".join(
        rf"<{tag}>[\s\S]*$"
        for tag in thinking_tags
    )
    text = re.sub(unclosed_pattern, "", text, flags=re.IGNORECASE)

    return text.strip()


def _format_sse_error(error: str) -> str:
    """Format an error as SSE event."""
    error_data = {
        "error": {
            "message": error,
            "type": "api_error",
        }
    }
    return f"data: {json.dumps(error_data)}\n\n"


def _build_trace_events(
    messages: list,
    tool_calls_used: list[str],
) -> list[dict[str, Any]]:
    """Build a sequence of trace events from completed workflow state.

    Emitted before text chunks so the UI can show real-time agent activity.
    Each event has: type, agent, event, (optional) tool, ts, and (optional) agents.

    Mapping rules:
    - analyze_energy, run_custom_analysis, diagnose_issue -> data_science_team
    - create_insight_schedule, seek_approval, execute_service -> system
    - Everything else stays under architect (no separate agent events)

    Args:
        messages: LangChain messages from the completed ConversationState.
        tool_calls_used: Deduplicated list of tool names invoked.

    Returns:
        Ordered list of trace event dicts ready for SSE emission.
    """
    events: list[dict[str, Any]] = []
    base_ts = time.time()
    offset = 0.0

    def _ts() -> float:
        nonlocal offset
        offset += 0.05
        return base_ts + offset

    # 1. Architect always starts
    events.append({
        "type": "trace",
        "agent": "architect",
        "event": "start",
        "ts": _ts(),
    })

    # 2. Walk messages looking for AIMessage tool_calls and ToolMessage results
    from langchain_core.messages import AIMessage as _AI, ToolMessage as _TM

    # Track which delegated agents were encountered
    delegated_agents: set[str] = set()
    # Track which delegated agents are currently "active" (started but not ended)
    active_delegated: str | None = None

    for msg in messages:
        if isinstance(msg, _AI) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get("name", "")
                if not tool_name:
                    continue

                target_agent = TOOL_AGENT_MAP.get(tool_name)

                if target_agent:
                    # End any previous delegated agent
                    if active_delegated and active_delegated != target_agent:
                        events.append({
                            "type": "trace",
                            "agent": active_delegated,
                            "event": "end",
                            "ts": _ts(),
                        })

                    # Start new delegated agent if not already active
                    if active_delegated != target_agent:
                        events.append({
                            "type": "trace",
                            "agent": target_agent,
                            "event": "start",
                            "ts": _ts(),
                        })
                        active_delegated = target_agent
                        delegated_agents.add(target_agent)

                # Emit tool_call event (under current agent)
                events.append({
                    "type": "trace",
                    "agent": target_agent or "architect",
                    "event": "tool_call",
                    "tool": tool_name,
                    "ts": _ts(),
                })

        elif isinstance(msg, _TM):
            # Tool result - emit tool_result event
            current_agent = active_delegated or "architect"
            events.append({
                "type": "trace",
                "agent": current_agent,
                "event": "tool_result",
                "ts": _ts(),
            })

    # End any remaining delegated agent
    if active_delegated:
        events.append({
            "type": "trace",
            "agent": active_delegated,
            "event": "end",
            "ts": _ts(),
        })

    # 3. Architect end
    events.append({
        "type": "trace",
        "agent": "architect",
        "event": "end",
        "ts": _ts(),
    })

    # 4. Complete event listing all agents involved
    all_agents = ["architect"] + sorted(delegated_agents)
    events.append({
        "type": "trace",
        "event": "complete",
        "agents": all_agents,
        "ts": _ts(),
    })

    return events


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
