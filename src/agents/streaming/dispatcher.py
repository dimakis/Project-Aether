"""Tool dispatcher — execute tool calls with progress draining and timeouts.

Encapsulates the ~90-line nested async flow from stream_conversation that
manages per-tool execution_context, progress_queue, deadline tracking, and
SSE event forwarding.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import TYPE_CHECKING, Any

from src.agents.execution_context import ProgressEvent, execution_context
from src.agents.streaming.events import StreamEvent
from src.settings import ANALYSIS_TOOLS, get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.agents.streaming.parser import ParsedToolCall

logger = logging.getLogger(__name__)


async def dispatch_tool_calls(
    *,
    tool_calls: list[ParsedToolCall],
    tool_lookup: dict[str, Any],
    conversation_id: str,
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None,
) -> AsyncGenerator[StreamEvent, None]:
    """Execute parsed tool calls, yielding streaming events.

    For each tool call:
    - Mutating tools yield ``approval_required`` and skip execution.
    - Read-only tools yield ``tool_start``, forward progress events from the
      execution context's queue while the tool runs, then yield ``tool_end``.
    - Timeout and exception handling produce error ``tool_end`` events.

    After all tools are dispatched, yields a final ``_dispatch_result`` event
    containing ``tool_results`` (id -> result string), ``full_tool_calls``
    (dicts for AIMessage), and ``proposal_summaries``.

    Args:
        tool_calls: Parsed tool calls from ToolCallParser.
        tool_lookup: Map of tool name to tool object (must have ``ainvoke``).
        conversation_id: Conversation ID for execution context.
        session_factory: Optional callable returning an async session context
            manager.  Threaded into :class:`ExecutionContext` so tools like
            ``consult_data_science_team`` can persist reports/insights.

    Yields:
        StreamEvent dicts during execution and one ``_dispatch_result`` at end.
    """
    tool_results: dict[str, str] = {}
    full_tool_calls: list[dict[str, Any]] = []
    proposal_summaries: list[str] = []

    for tc in tool_calls:
        full_tool_calls.append({"name": tc.name, "args": tc.args, "id": tc.id})

        # Mutating tools require human approval — skip execution
        if tc.is_mutating:
            yield StreamEvent(
                type="approval_required",
                tool=tc.name,
                content=f"Approval needed: {tc.name}({tc.args})",
            )
            tool_results[tc.id] = "Requires user approval"
            continue

        # Include truncated args so the activity panel can show what's being called
        args_summary = str(tc.args)[:200] if tc.args else ""
        yield StreamEvent(type="tool_start", tool=tc.name, agent="architect", args=args_summary)

        tool = tool_lookup.get(tc.name)
        if not tool:
            tool_results[tc.id] = f"Tool {tc.name} not found"
            yield StreamEvent(type="tool_end", tool=tc.name, result=f"Tool {tc.name} not found")
            continue

        # Execute tool with progress draining
        async for event in _execute_single_tool(
            tool=tool,
            tool_name=tc.name,
            tool_call_id=tc.id,
            args=tc.args,
            conversation_id=conversation_id,
            session_factory=session_factory,
        ):
            if event["type"] == "_tool_result":
                # Internal event — collect result
                tool_results[tc.id] = event["result_str"]
                if event.get("is_proposal"):
                    proposal_summaries.append(event["result_str"])
            else:
                yield event

    # Yield final dispatch result for the orchestrator
    yield StreamEvent(
        type="_dispatch_result",
        tool_results=tool_results,
        full_tool_calls=full_tool_calls,
        proposal_summaries=proposal_summaries,
    )


def _progress_to_stream_event(event: ProgressEvent) -> StreamEvent:
    """Convert a ProgressEvent to a StreamEvent, passing target as kwarg."""
    kwargs: dict[str, Any] = {}
    if event.target:
        kwargs["target"] = event.target
    return StreamEvent(
        type=event.type,
        agent=event.agent,
        content=event.message,
        **kwargs,
    )


async def _execute_single_tool(
    *,
    tool: Any,
    tool_name: str,
    tool_call_id: str,
    args: dict[str, Any],
    conversation_id: str,
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None,
) -> AsyncGenerator[StreamEvent, None]:
    """Execute a single tool with progress queue draining and timeout.

    Yields progress events (agent_start, agent_end, status, delegation)
    as they arrive, then yields tool_end with the result. On timeout or
    exception, yields an error tool_end.

    At the end, yields a ``_tool_result`` internal event for the dispatcher
    to collect.

    Args:
        tool: Tool object with ``ainvoke(args)`` method.
        tool_name: Name of the tool.
        tool_call_id: ID of the tool call.
        args: Arguments to pass to the tool.
        conversation_id: Conversation ID for execution context.
        session_factory: Optional session factory for execution context.

    Yields:
        StreamEvent dicts.
    """
    settings = get_settings()
    timeout = (
        settings.analysis_tool_timeout_seconds
        if tool_name in ANALYSIS_TOOLS
        else settings.tool_timeout_seconds
    )

    progress_queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()
    async with execution_context(
        progress_queue=progress_queue,
        session_factory=session_factory,
        conversation_id=conversation_id,
        tool_timeout=float(settings.tool_timeout_seconds),
        analysis_timeout=float(settings.analysis_tool_timeout_seconds),
    ):
        tool_task = asyncio.create_task(tool.ainvoke(args))
        deadline = time.monotonic() + float(timeout)
        timed_out = False

        try:
            while not tool_task.done():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                queue_get = asyncio.ensure_future(progress_queue.get())
                done_set, _ = await asyncio.wait(
                    {tool_task, queue_get},
                    timeout=min(0.5, remaining),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if queue_get in done_set:
                    event = queue_get.result()
                    yield _progress_to_stream_event(event)
                else:
                    queue_get.cancel()

            if timed_out:
                tool_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await tool_task
                result_str = f"Error: Tool {tool_name} timed out after {timeout}s"
                yield StreamEvent(type="tool_end", tool=tool_name, result=result_str)
                yield StreamEvent(type="_tool_result", result_str=result_str)
            else:
                # Drain remaining progress events after tool completes
                while not progress_queue.empty():
                    event = progress_queue.get_nowait()
                    yield _progress_to_stream_event(event)

                result = tool_task.result()
                result_str = str(result)
                yield StreamEvent(type="tool_end", tool=tool_name, result=result_str[:500])

                # Track proposal creations — authoritative check is tool name,
                # string match on result is a secondary signal for the frontend.
                is_proposal = tool_name == "seek_approval"
                if is_proposal:
                    logger.info(
                        "seek_approval invoked — result (first 200 chars): %s",
                        result_str[:200],
                    )
                yield StreamEvent(
                    type="_tool_result",
                    result_str=result_str,
                    is_proposal=is_proposal,
                )

        except Exception as e:
            if not tool_task.done():
                tool_task.cancel()
            result_str = f"Error: {e}"
            yield StreamEvent(type="tool_end", tool=tool_name, result=result_str)
            yield StreamEvent(type="_tool_result", result_str=result_str)
