"""OpenAI-compatible API for chat completions.

Provides an OpenAI-compatible `/v1/chat/completions` endpoint
for integration with Open WebUI and other OpenAI-compatible clients.
"""

from src.api.routes.openai_compat.handlers import _create_chat_completion, _stream_chat_completion
from src.api.routes.openai_compat.routes import router
from src.api.routes.openai_compat.schemas import ChatCompletionRequest, ChatMessage
from src.api.routes.openai_compat.utils import (
    TOOL_AGENT_MAP,
    _build_trace_events,
    _convert_to_langchain_messages,
    _derive_conversation_id,
    _extract_text_content,
    _format_sse_error,
    _is_background_request,
    _strip_thinking_tags,
)

__all__ = [
    "TOOL_AGENT_MAP",
    "ChatCompletionRequest",
    "ChatMessage",
    "_build_trace_events",
    "_convert_to_langchain_messages",
    "_create_chat_completion",
    "_derive_conversation_id",
    "_extract_text_content",
    "_format_sse_error",
    "_is_background_request",
    "_stream_chat_completion",
    "_strip_thinking_tags",
    "router",
]
