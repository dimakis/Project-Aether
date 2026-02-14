"""Streaming module — decomposed components for stream_conversation.

Provides modular, independently testable components for LLM token streaming,
tool call parsing, tool execution with progress draining, and proposal tracking.

Feature 31: Streaming Tool Executor Refactor.
"""

from src.agents.streaming.consumer import ConsumeResult, consume_stream
from src.agents.streaming.dispatcher import dispatch_tool_calls
from src.agents.streaming.events import StreamEvent
from src.agents.streaming.parser import ParsedToolCall, parse_tool_calls
from src.agents.streaming.proposals import extract_inline_proposals, generate_fallback_events

__all__ = [
    "ConsumeResult",
    "ParsedToolCall",
    "StreamEvent",
    "consume_stream",
    "dispatch_tool_calls",
    "extract_inline_proposals",
    "generate_fallback_events",
    "parse_tool_calls",
]
