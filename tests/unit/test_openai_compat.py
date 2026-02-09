"""Unit tests for OpenAI-compatible endpoint utility functions.

Covers _convert_to_langchain_messages, _derive_conversation_id,
_format_sse_error, and _is_background_request from openai_compat.py.
"""

import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.api.routes.openai_compat import (
    ChatMessage,
    _convert_to_langchain_messages,
    _derive_conversation_id,
    _format_sse_error,
    _is_background_request,
)

# ---------------------------------------------------------------------------
# _convert_to_langchain_messages
# ---------------------------------------------------------------------------


class TestConvertToLangchainMessages:
    """Verify OpenAI-format messages are correctly mapped to LangChain types."""

    def test_system_message(self):
        msgs = [ChatMessage(role="system", content="You are helpful.")]
        result = _convert_to_langchain_messages(msgs)

        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are helpful."

    def test_user_message(self):
        msgs = [ChatMessage(role="user", content="Hello")]
        result = _convert_to_langchain_messages(msgs)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Hello"

    def test_assistant_message(self):
        msgs = [ChatMessage(role="assistant", content="Hi there")]
        result = _convert_to_langchain_messages(msgs)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "Hi there"

    def test_assistant_with_tool_calls(self):
        tool_calls = [{"id": "call_1", "name": "get_weather", "args": {"city": "London"}}]
        msgs = [ChatMessage(role="assistant", content="Let me check", tool_calls=tool_calls)]
        result = _convert_to_langchain_messages(msgs)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert len(result[0].tool_calls) == 1
        assert result[0].tool_calls[0]["name"] == "get_weather"

    def test_tool_message(self):
        msgs = [ChatMessage(role="tool", content="72°F", tool_call_id="call_123")]
        result = _convert_to_langchain_messages(msgs)

        assert len(result) == 1
        assert isinstance(result[0], ToolMessage)
        assert result[0].content == "72°F"
        assert result[0].tool_call_id == "call_123"

    def test_none_content_defaults_to_empty_string(self):
        msgs = [ChatMessage(role="user", content=None)]
        result = _convert_to_langchain_messages(msgs)

        assert result[0].content == ""

    def test_full_conversation(self):
        msgs = [
            ChatMessage(role="system", content="You are an assistant."),
            ChatMessage(role="user", content="What's the weather?"),
            ChatMessage(role="assistant", content="Checking..."),
            ChatMessage(role="user", content="In London"),
        ]
        result = _convert_to_langchain_messages(msgs)

        assert len(result) == 4
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], HumanMessage)
        assert isinstance(result[2], AIMessage)
        assert isinstance(result[3], HumanMessage)

    def test_empty_list(self):
        assert _convert_to_langchain_messages([]) == []

    def test_unknown_role_is_skipped(self):
        msgs = [ChatMessage(role="function", content="result")]
        result = _convert_to_langchain_messages(msgs)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# _derive_conversation_id
# ---------------------------------------------------------------------------

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class TestDeriveConversationId:
    """_derive_conversation_id should produce deterministic IDs for
    conversations and random IDs for background requests."""

    def test_deterministic_for_same_user_message(self):
        msgs = [ChatMessage(role="user", content="Hello")]
        id1 = _derive_conversation_id(msgs)
        id2 = _derive_conversation_id(msgs)

        assert id1 == id2
        assert UUID_REGEX.match(id1)

    def test_different_for_different_user_messages(self):
        msgs1 = [ChatMessage(role="user", content="Hello")]
        msgs2 = [ChatMessage(role="user", content="Goodbye")]

        assert _derive_conversation_id(msgs1) != _derive_conversation_id(msgs2)

    def test_uses_first_user_message_only(self):
        msgs = [
            ChatMessage(role="user", content="First"),
            ChatMessage(role="assistant", content="Reply"),
            ChatMessage(role="user", content="Second"),
        ]
        expected = _derive_conversation_id([ChatMessage(role="user", content="First")])
        assert _derive_conversation_id(msgs) == expected

    def test_background_request_gets_random_uuid(self):
        msgs = [
            ChatMessage(role="system", content="Generate a title for the conversation."),
            ChatMessage(role="user", content="Hello"),
        ]
        id1 = _derive_conversation_id(msgs)
        id2 = _derive_conversation_id(msgs)

        # Background requests get different UUIDs each time
        assert id1 != id2

    def test_no_user_message_gets_random_uuid(self):
        msgs = [ChatMessage(role="system", content="System only")]
        id1 = _derive_conversation_id(msgs)
        id2 = _derive_conversation_id(msgs)

        assert id1 != id2

    def test_returns_valid_uuid_format(self):
        msgs = [ChatMessage(role="user", content="test")]
        result = _derive_conversation_id(msgs)
        assert UUID_REGEX.match(result)


# ---------------------------------------------------------------------------
# _format_sse_error
# ---------------------------------------------------------------------------


class TestFormatSseError:
    """_format_sse_error should produce valid SSE-formatted error events."""

    def test_starts_with_data_prefix(self):
        result = _format_sse_error("something went wrong")
        assert result.startswith("data: ")

    def test_ends_with_double_newline(self):
        result = _format_sse_error("error")
        assert result.endswith("\n\n")

    def test_contains_valid_json(self):
        result = _format_sse_error("test error")
        # Strip "data: " prefix and trailing newlines
        json_str = result.removeprefix("data: ").strip()
        parsed = json.loads(json_str)

        assert "error" in parsed
        assert parsed["error"]["message"] == "test error"
        assert parsed["error"]["type"] == "api_error"


# ---------------------------------------------------------------------------
# _is_background_request
# ---------------------------------------------------------------------------


class TestIsBackgroundRequest:
    """_is_background_request should detect title generation and
    suggestion requests that shouldn't be traced."""

    def test_title_generation_detected(self):
        msgs = [
            ChatMessage(role="system", content="Generate a title for this conversation."),
            ChatMessage(role="user", content="Hello"),
        ]
        assert _is_background_request(msgs) is True

    def test_suggestion_generation_detected(self):
        msgs = [
            ChatMessage(role="system", content="Generate suggestions for follow up questions."),
            ChatMessage(role="user", content="Hello"),
        ]
        assert _is_background_request(msgs) is True

    def test_normal_conversation_not_detected(self):
        msgs = [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="Turn on the lights"),
        ]
        assert _is_background_request(msgs) is False

    def test_empty_messages_not_detected(self):
        assert _is_background_request([]) is False

    def test_case_insensitive_matching(self):
        msgs = [
            ChatMessage(role="system", content="GENERATE A TITLE for this."),
        ]
        assert _is_background_request(msgs) is True
