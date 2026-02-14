"""Unit tests for StreamConsumer.

Tests that StreamConsumer correctly consumes an astream async iterator,
yields token StreamEvents, and returns the accumulated tool call buffer.
"""

import pytest
from langchain_core.messages import AIMessageChunk

from tests.unit.streaming.conftest import async_iter, make_tool_call_chunk


class TestStreamConsumer:
    """Tests for consume_stream() — the extracted stream consumption logic."""

    @pytest.mark.asyncio
    async def test_token_chunks_yield_events(self):
        """Text chunks should yield StreamEvent(type='token')."""
        from src.agents.streaming.consumer import consume_stream

        chunks = [
            AIMessageChunk(content="Hello"),
            AIMessageChunk(content=" world"),
            AIMessageChunk(content="!"),
        ]

        events = []
        async for event in consume_stream(async_iter(chunks)):
            events.append(event)

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 3
        assert token_events[0]["content"] == "Hello"
        assert token_events[1]["content"] == " world"
        assert token_events[2]["content"] == "!"

    @pytest.mark.asyncio
    async def test_empty_content_ignored(self):
        """Empty content chunks should not yield token events."""
        from src.agents.streaming.consumer import consume_stream

        chunks = [
            AIMessageChunk(content=""),
            AIMessageChunk(content="Real"),
            AIMessageChunk(content=""),
        ]

        events = []
        async for event in consume_stream(async_iter(chunks)):
            events.append(event)

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 1
        assert token_events[0]["content"] == "Real"

    @pytest.mark.asyncio
    async def test_tool_call_chunks_accumulated(self):
        """Tool call chunks should be accumulated into the buffer."""
        from src.agents.streaming.consumer import consume_stream

        chunks = [
            make_tool_call_chunk("get_entity_state", '{"entity_id":', "call-1"),
            make_tool_call_chunk("", ' "light.kitchen"}', "", index=0),
        ]
        # The second chunk has no name/id — it appends args to index 0

        events = []
        async for event in consume_stream(async_iter(chunks)):
            events.append(event)

        # No token events (tool call chunks have empty content)
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 0

        # The last event should be the result
        result_events = [e for e in events if e["type"] == "_consume_result"]
        assert len(result_events) == 1
        result = result_events[0]
        assert result["collected_content"] == ""
        assert len(result["tool_calls_buffer"]) == 1
        assert result["tool_calls_buffer"][0]["name"] == "get_entity_state"
        assert result["tool_calls_buffer"][0]["args"] == '{"entity_id": "light.kitchen"}'
        assert result["tool_calls_buffer"][0]["id"] == "call-1"

    @pytest.mark.asyncio
    async def test_mixed_tokens_and_tool_chunks(self):
        """Tokens before tool chunks should be yielded, tool chunks accumulated."""
        from src.agents.streaming.consumer import consume_stream

        chunks = [
            AIMessageChunk(content="Let me check"),
            make_tool_call_chunk("get_entity_state", '{"entity_id": "light.x"}', "call-1"),
        ]

        events = []
        async for event in consume_stream(async_iter(chunks)):
            events.append(event)

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 1
        assert token_events[0]["content"] == "Let me check"

        result_events = [e for e in events if e["type"] == "_consume_result"]
        assert len(result_events) == 1
        assert len(result_events[0]["tool_calls_buffer"]) == 1

    @pytest.mark.asyncio
    async def test_empty_stream(self):
        """An empty stream should yield only the result with empty content."""
        from src.agents.streaming.consumer import consume_stream

        events = []
        async for event in consume_stream(async_iter([])):
            events.append(event)

        result_events = [e for e in events if e["type"] == "_consume_result"]
        assert len(result_events) == 1
        assert result_events[0]["collected_content"] == ""
        assert result_events[0]["tool_calls_buffer"] == []

    @pytest.mark.asyncio
    async def test_tool_chunks_skip_token_when_colocated(self):
        """When a chunk has both content and tool_call_chunks, skip content."""
        from src.agents.streaming.consumer import consume_stream

        # Some models emit content alongside tool_call_chunks (partial JSON leak)
        chunk = AIMessageChunk(content="partial json")
        chunk.tool_call_chunks = [
            {"name": "get_entity_state", "args": "{}", "id": "call-1", "index": 0}
        ]

        events = []
        async for event in consume_stream(async_iter([chunk])):
            events.append(event)

        # Token should be suppressed
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 0

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_by_index(self):
        """Multiple tool calls with different indices should be tracked separately."""
        from src.agents.streaming.consumer import consume_stream

        chunk = AIMessageChunk(content="")
        chunk.tool_call_chunks = [
            {"name": "get_entity_state", "args": '{"entity_id": "a"}', "id": "call-1", "index": 0},
            {
                "name": "list_entities_by_domain",
                "args": '{"domain": "light"}',
                "id": "call-2",
                "index": 1,
            },
        ]

        events = []
        async for event in consume_stream(async_iter([chunk])):
            events.append(event)

        result_events = [e for e in events if e["type"] == "_consume_result"]
        assert len(result_events) == 1
        buffer = result_events[0]["tool_calls_buffer"]
        assert len(buffer) == 2
        assert buffer[0]["name"] == "get_entity_state"
        assert buffer[1]["name"] == "list_entities_by_domain"
