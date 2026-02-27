"""Chat completion handlers (non-streaming and streaming)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastapi import HTTPException
from langchain_core.messages import AIMessage
from sqlalchemy.exc import SQLAlchemyError

from src.agents import ArchitectWorkflow
from src.agents.model_context import model_context
from src.api.routes.openai_compat.schemas import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)
from src.api.routes.openai_compat.streaming_filter import _StreamingTagFilter
from src.api.routes.openai_compat.utils import (
    TOOL_AGENT_MAP,
    _convert_to_langchain_messages,
    _derive_conversation_id,
    _extract_text_content,
    _format_sse_error,
    _is_background_request,
    _strip_thinking_tags,
)
from src.graph.state import ConversationState
from src.storage import get_session
from src.tracing import log_param, start_experiment_run
from src.tracing.context import session_context

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_log = logging.getLogger(__name__)

# Fallback if DB settings aren't available yet (first request before migration).
_FALLBACK_STREAM_TIMEOUT = 900  # 15 minutes


def _make_token_chunk(completion_id: str, created: int, model: str, tok: str) -> str:
    """Build an SSE line for a single token delta."""
    return (
        "data: "
        + json.dumps(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": tok},
                        "finish_reason": None,
                    }
                ],
            }
        )
        + "\n\n"
    )


def _should_use_distributed() -> bool:
    """Check if the gateway should delegate to remote A2A services."""
    from src.settings import get_settings

    return get_settings().deployment_mode == "distributed"


def _create_distributed_client() -> A2ARemoteClient:
    """Create an A2ARemoteClient pointing at the Architect service."""
    from src.agents.a2a_client import A2ARemoteClient
    from src.settings import get_settings

    return A2ARemoteClient(base_url=get_settings().architect_service_url)


if TYPE_CHECKING:
    from src.agents.a2a_client import A2ARemoteClient


async def _create_chat_completion(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | dict[str, Any]:
    """Process non-streaming chat completion."""
    import mlflow

    async with get_session() as session:
        # Get or create conversation - use stable ID derived from messages
        # This ensures Open WebUI conversations stay grouped in MLflow
        conversation_id = request.conversation_id or _derive_conversation_id(request.messages)

        with session_context(conversation_id):
            # Create MLflow run for full observability (runs + nested traces)
            with start_experiment_run("conversation"):
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
                    messages=lc_messages[:-1],  # type: ignore[arg-type]
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
                    for msg in reversed(list(state.messages)):  # type: ignore[assignment]
                        if isinstance(msg, AIMessage):
                            assistant_content = str(msg.content)
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
        result: dict[str, Any] = response.model_dump()
        if trace_id:
            result["trace_id"] = trace_id
        return result


async def _stream_chat_completion(
    request: ChatCompletionRequest,
) -> AsyncGenerator[str, None]:
    """Generate streaming chat completion (SSE format).

    Yields Server-Sent Events in the OpenAI format:
    data: {"id": "...", "object": "chat.completion.chunk", ...}

    MLflow tracing is handled by the workflow layer (stream_conversation
    creates its own trace via start_span). The handler only iterates the
    generator and yields SSE events.
    """
    completion_id = f"chatcmpl-{uuid4().hex[:8]}"
    created = int(time.time())

    # Resolve stream timeout from DB settings (cached, fast path)
    try:
        from src.dal.app_settings import get_chat_setting

        stream_timeout = await get_chat_setting("stream_timeout_seconds")
        stream_timeout = int(stream_timeout) if stream_timeout else _FALLBACK_STREAM_TIMEOUT
    except Exception:
        stream_timeout = _FALLBACK_STREAM_TIMEOUT

    try:
        async with asyncio.timeout(stream_timeout), get_session() as session:
            # Use stable ID derived from messages for conversation grouping
            conversation_id = request.conversation_id or _derive_conversation_id(request.messages)

            # Set session context for MLflow trace correlation — all spans
            # within this request will share the same session ID.
            from src.tracing.context import set_session_id

            set_session_id(conversation_id)

            # Convert messages and extract user message
            lc_messages = _convert_to_langchain_messages(request.messages)

            user_message = ""
            for msg in reversed(request.messages):
                if msg.role == "user" and msg.content:
                    user_message = msg.content
                    break

            if not user_message:
                yield _format_sse_error("No user message found")
                return

            # Create state and apply agent routing (Feature 30)
            from src.agents.routing import (
                DEFAULT_AGENT,
                apply_routing_to_state,
                resolve_agent_routing,
            )

            state = ConversationState(
                conversation_id=conversation_id,
                messages=lc_messages[:-1],  # type: ignore[arg-type]
            )
            routing = resolve_agent_routing(
                agent=request.agent,
                workflow_preset=request.workflow_preset,
                disabled_agents=request.disabled_agents,
            )
            apply_routing_to_state(state, routing)

            # Distributed mode: delegate to remote Architect via A2A streaming
            if _should_use_distributed():
                a2a_client = _create_distributed_client()
                _log.info(
                    "Distributed mode: streaming from remote Architect at %s",
                    a2a_client.base_url,
                )
                try:
                    tag_filter = _StreamingTagFilter()
                    agents_seen: list[str] = ["architect"]
                    stream_started = False

                    async for event in a2a_client.stream(state):
                        event_type = event.get("type")

                        if not stream_started:
                            stream_started = True
                            yield f"data: {json.dumps({'type': 'trace', 'agent': 'architect', 'event': 'start', 'ts': time.time()})}\n\n"

                        if event_type == "token":
                            raw = event.get("content", "")
                            for ft in tag_filter.feed(raw):
                                if not ft.text:
                                    continue
                                if ft.is_thinking:
                                    yield f"data: {json.dumps({'type': 'thinking', 'content': ft.text})}\n\n"
                                else:
                                    yield _make_token_chunk(
                                        completion_id, created, request.model, ft.text
                                    )

                        elif event_type == "tool_start":
                            tool_name = event.get("tool", "")
                            agent_name = event.get("agent", "architect")
                            if agent_name not in agents_seen:
                                agents_seen.append(agent_name)
                            trace_ev: dict[str, object] = {
                                "type": "trace",
                                "agent": agent_name,
                                "event": "tool_call",
                                "tool": tool_name,
                                "ts": time.time(),
                            }
                            yield f"data: {json.dumps(trace_ev)}\n\n"
                            yield f"data: {json.dumps({'type': 'status', 'content': f'Running {tool_name}...'})}\n\n"

                        elif event_type == "tool_end":
                            tool_name = event.get("tool", "")
                            agent_name = event.get("agent", "architect")
                            result_text = event.get("result", "")
                            if result_text:
                                yield f"data: {json.dumps({'type': 'trace', 'agent': agent_name, 'event': 'tool_result', 'tool': tool_name, 'tool_result': result_text[:200], 'ts': time.time()})}\n\n"
                            yield f"data: {json.dumps({'type': 'status', 'content': ''})}\n\n"

                        elif event_type in ("agent_start", "agent_end"):
                            agent_name = event.get("agent", "")
                            if agent_name:
                                if agent_name not in agents_seen:
                                    agents_seen.append(agent_name)
                                a2a_ev = "start" if event_type == "agent_start" else "end"
                                yield f"data: {json.dumps({'type': 'trace', 'agent': agent_name, 'event': a2a_ev, 'ts': time.time()})}\n\n"

                        elif event_type == "delegation":
                            yield f"data: {json.dumps({'type': 'delegation', 'from': event.get('agent', ''), 'to': event.get('target', ''), 'content': event.get('content', ''), 'ts': time.time()})}\n\n"

                        elif event_type == "thinking":
                            yield f"data: {json.dumps({'type': 'thinking', 'content': event.get('content', '')})}\n\n"

                        elif event_type == "status":
                            content = event.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'type': 'status', 'content': content})}\n\n"

                        elif event_type == "trace_id":
                            tid = event.get("content", "")
                            if tid:
                                yield f"data: {json.dumps({'type': 'metadata', 'trace_id': tid})}\n\n"

                        elif event_type == "approval_required":
                            yield _make_token_chunk(
                                completion_id,
                                created,
                                request.model,
                                event.get("content", "Approval required"),
                            )

                        elif event_type == "error":
                            yield _format_sse_error(event.get("content", "Agent error"))

                    for ft in tag_filter.flush():
                        if not ft.text:
                            continue
                        if ft.is_thinking:
                            yield f"data: {json.dumps({'type': 'thinking', 'content': ft.text})}\n\n"
                        else:
                            yield _make_token_chunk(completion_id, created, request.model, ft.text)

                    if stream_started:
                        yield f"data: {json.dumps({'type': 'trace', 'agent': 'architect', 'event': 'end', 'ts': time.time()})}\n\n"
                        yield f"data: {json.dumps({'type': 'trace', 'event': 'complete', 'agents': agents_seen, 'ts': time.time()})}\n\n"

                    final_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield f"data: {json.dumps({'type': 'metadata', 'conversation_id': conversation_id})}\n\n"

                    await session.commit()
                    yield "data: [DONE]\n\n"
                except Exception:
                    _log.exception("Distributed streaming failed")
                    yield _format_sse_error(
                        "Distributed streaming failed. Check server logs for details."
                    )
                return

            # Monolith mode: resolve agent and run in-process
            # When needs_orchestrator is True, classify intent and plan response.
            effective_agent = routing.active_agent
            if routing.needs_orchestrator:
                from src.agents.orchestrator import OrchestratorAgent

                orchestrator = OrchestratorAgent(model_name=request.model)
                classification = await orchestrator.classify_intent(
                    user_message,
                    await orchestrator._get_available_agents(),
                )
                plan = await orchestrator.plan_response(user_message, classification)

                effective_agent = plan.target_agent
                state.active_agent = effective_agent
                yield f"data: {json.dumps({'type': 'routing', 'agent': effective_agent, 'confidence': classification.get('confidence', 0), 'reasoning': classification.get('reasoning', '')})}\n\n"

                if plan.response_type == "clarify" and plan.clarification_options:
                    options_data = [
                        {"title": opt.title, "description": opt.description}
                        for opt in plan.clarification_options
                    ]
                    yield f"data: {json.dumps({'type': 'clarification_options', 'options': options_data})}\n\n"

                # For now, only the architect has a full streaming workflow.
                # Other agents fall back to the architect workflow until they
                # have their own streaming implementation.
                if effective_agent != "architect":
                    effective_agent = DEFAULT_AGENT
                    state.active_agent = effective_agent

            with model_context(
                model_name=request.model,
                temperature=request.temperature,
            ):
                from src.storage import get_committing_session

                workflow = ArchitectWorkflow(
                    model_name=request.model,
                    temperature=request.temperature,
                    session_factory=get_committing_session,
                )

                is_background = _is_background_request(request.messages)
                tool_calls_used: list[str] = []
                final_state: ConversationState | None = None
                trace_id: str | None = None
                tag_filter = _StreamingTagFilter()

                # --- Emit job start for the global activity panel ---
                if not is_background:
                    from src.jobs import emit_job_start as _emit_job_start

                    _emit_job_start(conversation_id, "chat", user_message[:80])

                # --- Agent lifecycle tracking for the activity panel ---
                agent_stack: list[str] = []
                agents_seen: list[str] = ["architect"]  # type: ignore[no-redef]
                stream_started = False

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
                        # Separate visible content from thinking
                        for ft in tag_filter.feed(raw_token):
                            if not ft.text:
                                continue
                            if ft.is_thinking:
                                yield f"data: {json.dumps({'type': 'thinking', 'content': ft.text})}\n\n"
                            else:
                                yield _make_token_chunk(
                                    completion_id, created, request.model, ft.text
                                )

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
                            if target != "architect" and (
                                not agent_stack or agent_stack[-1] != target
                            ):
                                # Start new delegated agent (push onto stack)
                                yield f"data: {json.dumps({'type': 'trace', 'agent': target, 'event': 'start', 'ts': time.time()})}\n\n"
                                agent_stack.append(target)
                                if target not in agents_seen:
                                    agents_seen.append(target)

                            tool_trace: dict[str, object] = {
                                "type": "trace",
                                "agent": target,
                                "event": "tool_call",
                                "tool": tool_name,
                                "ts": time.time(),
                            }
                            tool_args = event.get("args", "")
                            if tool_args:
                                tool_trace["tool_args"] = tool_args[:200]
                            yield f"data: {json.dumps(tool_trace)}\n\n"
                            # Status event for UI
                            status_ev = {
                                "type": "status",
                                "content": f"Running {tool_name}...",
                            }
                            yield f"data: {json.dumps(status_ev)}\n\n"

                    elif event_type == "tool_end":
                        if not is_background:
                            # --- Agent lifecycle: pop the tool-level agent ---
                            tool_name = event.get("tool", "")
                            target = TOOL_AGENT_MAP.get(tool_name, "architect")
                            if agent_stack and agent_stack[-1] == target:
                                agent_stack.pop()
                                yield f"data: {json.dumps({'type': 'trace', 'agent': target, 'event': 'end', 'ts': time.time()})}\n\n"
                            elif agent_stack:
                                while agent_stack and agent_stack[-1] != target:
                                    popped = agent_stack.pop()
                                    yield f"data: {json.dumps({'type': 'trace', 'agent': popped, 'event': 'end', 'ts': time.time()})}\n\n"
                                if agent_stack and agent_stack[-1] == target:
                                    agent_stack.pop()
                                    yield f"data: {json.dumps({'type': 'trace', 'agent': target, 'event': 'end', 'ts': time.time()})}\n\n"

                            # Emit tool_result trace event for the activity feed
                            tool_result = event.get("result", "")
                            if tool_result:
                                result_ev: dict[str, object] = {
                                    "type": "trace",
                                    "agent": target,
                                    "event": "tool_result",
                                    "tool": tool_name,
                                    "tool_result": tool_result[:200],
                                    "ts": time.time(),
                                }
                                yield f"data: {json.dumps(result_ev)}\n\n"

                            # Emit proposal_created event when seek_approval
                            # successfully created a proposal
                            if tool_name == "seek_approval" and (
                                "submitted" in tool_result.lower()
                                or "proposal for your approval" in tool_result.lower()
                            ):
                                yield f"data: {json.dumps({'type': 'proposal_created', 'content': tool_result})}\n\n"

                            status_ev = {
                                "type": "status",
                                "content": "",  # Clear status
                            }
                            yield f"data: {json.dumps(status_ev)}\n\n"

                    elif event_type == "agent_start":
                        agent_name = event.get("agent", "")
                        if not is_background and agent_name:
                            yield f"data: {json.dumps({'type': 'trace', 'agent': agent_name, 'event': 'start', 'ts': time.time()})}\n\n"
                            agent_stack.append(agent_name)
                            if agent_name not in agents_seen:
                                agents_seen.append(agent_name)
                            from src.jobs import emit_job_agent as _eja

                            _eja(conversation_id, agent_name, "start")

                    elif event_type == "agent_end":
                        agent_name = event.get("agent", "")
                        if not is_background and agent_name:
                            yield f"data: {json.dumps({'type': 'trace', 'agent': agent_name, 'event': 'end', 'ts': time.time()})}\n\n"
                            if agent_stack and agent_stack[-1] == agent_name:
                                agent_stack.pop()
                            from src.jobs import emit_job_agent as _eja

                            _eja(conversation_id, agent_name, "end")

                    elif event_type == "delegation":
                        if not is_background:
                            from_agent = event.get("agent", "")
                            to_agent = event.get("target", "")
                            content = event.get("content", "")
                            yield f"data: {json.dumps({'type': 'delegation', 'from': from_agent, 'to': to_agent, 'content': content, 'ts': time.time()})}\n\n"

                    elif event_type == "status":
                        status_content = event.get("content", "")
                        if not is_background and status_content:
                            yield f"data: {json.dumps({'type': 'status', 'content': status_content})}\n\n"

                    elif event_type == "state":
                        final_state = event.get("state")

                    elif event_type == "approval_required":
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
                        yield _make_token_chunk(completion_id, created, request.model, ft.text)

            # --- Agent lifecycle: complete event ---
            if stream_started and not is_background:
                while agent_stack:
                    popped = agent_stack.pop()
                    yield f"data: {json.dumps({'type': 'trace', 'agent': popped, 'event': 'end', 'ts': time.time()})}\n\n"
                yield f"data: {json.dumps({'type': 'trace', 'agent': 'architect', 'event': 'end', 'ts': time.time()})}\n\n"
                yield f"data: {json.dumps({'type': 'trace', 'event': 'complete', 'agents': agents_seen, 'ts': time.time()})}\n\n"
                from src.jobs import emit_job_complete as _ejc

                _ejc(conversation_id)

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

            metadata: dict[str, object] = {
                "type": "metadata",
                "conversation_id": conversation_id,
                "job_id": conversation_id,
            }
            if trace_id:
                metadata["trace_id"] = trace_id
            if tool_calls_used:
                metadata["tool_calls"] = list(set(tool_calls_used))
            yield f"data: {json.dumps(metadata)}\n\n"

            # Commit before [DONE] so failures surface as SSE errors.
            # Do NOT wrap in asyncio.wait_for — the outer asyncio.timeout
            # already guards against a hung commit and using both would make
            # it impossible to distinguish a commit-specific timeout from
            # the stream-level timeout (both raise TimeoutError).
            try:
                await session.commit()
            except (OSError, SQLAlchemyError) as commit_err:
                _log.warning("session.commit() failed: %s", commit_err)
                yield _format_sse_error(f"Database error: {commit_err}")

            yield "data: [DONE]\n\n"

    except TimeoutError:
        _log.error("Stream timed out after %ds", stream_timeout)
        yield _format_sse_error(
            f"Stream timed out after {stream_timeout}s. "
            "You can increase this in Settings > Chat & Streaming."
        )
    except Exception:
        _log.exception("Unhandled error in streaming handler")
        yield _format_sse_error("An internal error occurred. Check server logs for details.")
