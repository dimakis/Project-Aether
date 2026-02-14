"""Utility functions for OpenAI-compatible API."""

from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

if TYPE_CHECKING:
    from src.api.routes.openai_compat.schemas import ChatMessage

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


def _convert_to_langchain_messages(messages: list[ChatMessage]) -> list[BaseMessage]:
    """Convert OpenAI messages to LangChain format."""
    lc_messages: list[BaseMessage] = []

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


def _strip_thinking_tags(content: str | list[Any]) -> str:
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
    closed_pattern = "|".join(rf"<{tag}>[\s\S]*?</{tag}>" for tag in thinking_tags)
    text = re.sub(closed_pattern, "", text, flags=re.IGNORECASE)

    # Second: strip unclosed tags  <tag>...$ (no closing tag found)
    unclosed_pattern = "|".join(rf"<{tag}>[\s\S]*$" for tag in thinking_tags)
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
    messages: list[Any],
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
    events.append(
        {
            "type": "trace",
            "agent": "architect",
            "event": "start",
            "ts": _ts(),
        }
    )

    # 2. Walk messages looking for AIMessage tool_calls and ToolMessage results
    from langchain_core.messages import AIMessage as _AI
    from langchain_core.messages import ToolMessage as _TM

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
                        events.append(
                            {
                                "type": "trace",
                                "agent": active_delegated,
                                "event": "end",
                                "ts": _ts(),
                            }
                        )

                    # Start new delegated agent if not already active
                    if active_delegated != target_agent:
                        events.append(
                            {
                                "type": "trace",
                                "agent": target_agent,
                                "event": "start",
                                "ts": _ts(),
                            }
                        )
                        active_delegated = target_agent
                        delegated_agents.add(target_agent)

                # Emit tool_call event (under current agent)
                events.append(
                    {
                        "type": "trace",
                        "agent": target_agent or "architect",
                        "event": "tool_call",
                        "tool": tool_name,
                        "ts": _ts(),
                    }
                )

        elif isinstance(msg, _TM):
            # Tool result - emit tool_result event
            current_agent = active_delegated or "architect"
            events.append(
                {
                    "type": "trace",
                    "agent": current_agent,
                    "event": "tool_result",
                    "ts": _ts(),
                }
            )

    # End any remaining delegated agent
    if active_delegated:
        events.append(
            {
                "type": "trace",
                "agent": active_delegated,
                "event": "end",
                "ts": _ts(),
            }
        )

    # 3. Architect end
    events.append(
        {
            "type": "trace",
            "agent": "architect",
            "event": "end",
            "ts": _ts(),
        }
    )

    # 4. Complete event listing all agents involved
    all_agents = ["architect", *sorted(delegated_agents)]
    events.append(
        {
            "type": "trace",
            "event": "complete",
            "agents": all_agents,
            "ts": _ts(),
        }
    )

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
