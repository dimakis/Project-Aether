"""Stream consumer — consume an LLM astream and yield token events.

Eliminates the duplicated stream consumption block that appeared twice
in the original stream_conversation (initial stream + follow-up stream).

The consumer yields StreamEvent(type="token") for each content chunk and
accumulates tool call chunks by index. After the stream is exhausted, it
yields a final _consume_result event containing the collected content and
tool call buffer for the orchestrator to inspect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.agents.streaming.events import StreamEvent

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator


@dataclass
class ConsumeResult:
    """Result of consuming an LLM stream.

    Attributes:
        collected_content: All text content accumulated from token chunks.
        tool_calls_buffer: Raw tool call buffers accumulated from tool call chunks.
    """

    collected_content: str = ""
    tool_calls_buffer: list[dict[str, str]] = field(default_factory=list)


async def consume_stream(
    astream: AsyncIterator[Any],
) -> AsyncGenerator[StreamEvent, None]:
    """Consume an LLM astream, yielding token events and accumulating tool chunks.

    For each content chunk (without co-located tool_call_chunks), yields a
    ``StreamEvent(type="token")``. Tool call chunks are merged by index into
    a buffer.

    After the stream is exhausted, yields a final internal event
    ``StreamEvent(type="_consume_result")`` carrying ``collected_content``
    and ``tool_calls_buffer`` so the caller can extract the result.

    Args:
        astream: Async iterator of LLM message chunks (e.g. from ``tool_llm.astream()``).

    Yields:
        StreamEvent dicts — ``token`` events during streaming, and one
        ``_consume_result`` event at the end.
    """
    collected_content = ""
    tool_calls_buffer: list[dict[str, str]] = []

    async for chunk in astream:
        has_tool_chunks = hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks

        # Token content — skip when tool call chunks are present in the
        # same chunk to avoid leaking partial JSON from some models
        if chunk.content and not has_tool_chunks:
            token = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            collected_content += token
            yield StreamEvent(type="token", content=token)

        # Tool call chunks (accumulated across multiple stream chunks)
        if has_tool_chunks:
            tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []
            for tc_chunk in tool_call_chunks:
                # Merge into buffer by index
                idx = tc_chunk.get("index", 0)
                while len(tool_calls_buffer) <= idx:
                    tool_calls_buffer.append({"name": "", "args": "", "id": ""})
                buf = tool_calls_buffer[idx]
                if tc_chunk.get("name"):
                    buf["name"] = tc_chunk["name"]
                if tc_chunk.get("args"):
                    buf["args"] += tc_chunk["args"]
                if tc_chunk.get("id"):
                    buf["id"] = tc_chunk["id"]

    # Yield the result as an internal event for the orchestrator
    yield StreamEvent(
        type="_consume_result",
        collected_content=collected_content,
        tool_calls_buffer=tool_calls_buffer,
    )
