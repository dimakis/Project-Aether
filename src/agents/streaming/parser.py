"""Tool call parser — decode raw tool call buffers into typed dataclasses.

Pure-function extraction of the JSON decoding + buffer merging logic from
stream_conversation. Classifies each tool call as mutating or read-only
via a caller-provided predicate.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedToolCall:
    """A parsed and validated tool call.

    Attributes:
        name: Tool function name.
        args: JSON-decoded arguments dict.
        id: Tool call ID from the LLM.
        is_mutating: Whether this tool can mutate Home Assistant state.
    """

    name: str
    args: dict[str, Any]
    id: str
    is_mutating: bool


def parse_tool_calls(
    buffer: list[dict[str, str]],
    *,
    is_mutating_fn: Callable[[str], bool],
) -> list[ParsedToolCall]:
    """Parse raw tool call buffers into typed ParsedToolCall instances.

    Skips tool calls with:
    - Empty name (truncated LLM output due to max_tokens)
    - Unparseable JSON args (truncated or malformed)

    Args:
        buffer: Raw tool call buffers from StreamConsumer, each with
            ``name``, ``args`` (JSON string), and ``id`` keys.
        is_mutating_fn: Predicate that returns True if the tool name
            represents a mutating operation requiring HITL approval.

    Returns:
        List of successfully parsed tool calls.
    """
    result: list[ParsedToolCall] = []

    for tc_buf in buffer:
        tool_name = tc_buf["name"]
        tool_call_id = tc_buf["id"]

        # Skip truncated tool calls (empty name = output token limit hit)
        if not tool_name:
            logger.warning(
                "Skipping tool call with empty name (likely truncated LLM output due to max_tokens)"
            )
            continue

        # Parse JSON args
        try:
            args = json.loads(tc_buf["args"]) if tc_buf["args"] else {}
        except json.JSONDecodeError:
            logger.warning(
                "Skipping tool call '%s': args JSON could not be parsed "
                "(likely truncated LLM output). Raw args: %s",
                tool_name,
                tc_buf["args"][:200] if tc_buf["args"] else "(empty)",
            )
            continue

        result.append(
            ParsedToolCall(
                name=tool_name,
                args=args,
                id=tool_call_id,
                is_mutating=is_mutating_fn(tool_name),
            )
        )

    return result
