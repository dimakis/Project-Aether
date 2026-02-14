"""Unit tests for ToolCallParser.

Tests that ToolCallParser correctly parses raw tool call buffers into
typed ParsedToolCall dataclasses with JSON-decoded args and mutating
classification.
"""


class TestParsedToolCall:
    """Tests for the ParsedToolCall dataclass."""

    def test_construction(self):
        from src.agents.streaming.parser import ParsedToolCall

        tc = ParsedToolCall(
            name="get_entity_state",
            args={"entity_id": "light.kitchen"},
            id="call-1",
            is_mutating=False,
        )
        assert tc.name == "get_entity_state"
        assert tc.args == {"entity_id": "light.kitchen"}
        assert tc.id == "call-1"
        assert tc.is_mutating is False


class TestParseToolCalls:
    """Tests for parse_tool_calls() — the extracted tool call parsing logic."""

    def test_valid_single_tool_call(self):
        from src.agents.streaming.parser import parse_tool_calls

        buffer = [{"name": "get_entity_state", "args": '{"entity_id": "light.x"}', "id": "call-1"}]
        result = parse_tool_calls(buffer, is_mutating_fn=lambda _: False)
        assert len(result) == 1
        assert result[0].name == "get_entity_state"
        assert result[0].args == {"entity_id": "light.x"}
        assert result[0].id == "call-1"
        assert result[0].is_mutating is False

    def test_empty_name_skipped(self):
        """Tool calls with empty name (truncated output) should be skipped."""
        from src.agents.streaming.parser import parse_tool_calls

        buffer = [{"name": "", "args": '{"x": 1}', "id": "call-1"}]
        result = parse_tool_calls(buffer, is_mutating_fn=lambda _: False)
        assert len(result) == 0

    def test_malformed_json_skipped(self):
        """Tool calls with unparseable JSON args should be skipped."""
        from src.agents.streaming.parser import parse_tool_calls

        buffer = [
            {"name": "seek_approval", "args": '{"truncated": "yes', "id": "call-1"},
        ]
        result = parse_tool_calls(buffer, is_mutating_fn=lambda _: False)
        assert len(result) == 0

    def test_empty_args_defaults_to_empty_dict(self):
        """Tool calls with empty args string should get empty dict."""
        from src.agents.streaming.parser import parse_tool_calls

        buffer = [{"name": "list_automations", "args": "", "id": "call-1"}]
        result = parse_tool_calls(buffer, is_mutating_fn=lambda _: False)
        assert len(result) == 1
        assert result[0].args == {}

    def test_mutating_classification(self):
        """Tools should be classified as mutating via the provided function."""
        from src.agents.streaming.parser import parse_tool_calls

        def is_mutating(name: str) -> bool:
            return name == "execute_service"

        buffer = [
            {"name": "get_entity_state", "args": "{}", "id": "call-1"},
            {"name": "execute_service", "args": '{"action": "on"}', "id": "call-2"},
        ]
        result = parse_tool_calls(buffer, is_mutating_fn=is_mutating)
        assert len(result) == 2
        assert result[0].is_mutating is False
        assert result[1].is_mutating is True

    def test_multiple_tool_calls(self):
        """Multiple valid tool calls should all be parsed."""
        from src.agents.streaming.parser import parse_tool_calls

        buffer = [
            {"name": "get_entity_state", "args": '{"entity_id": "a"}', "id": "call-1"},
            {"name": "list_entities_by_domain", "args": '{"domain": "light"}', "id": "call-2"},
            {"name": "search_entities", "args": '{"query": "temp"}', "id": "call-3"},
        ]
        result = parse_tool_calls(buffer, is_mutating_fn=lambda _: False)
        assert len(result) == 3
        assert result[0].name == "get_entity_state"
        assert result[1].name == "list_entities_by_domain"
        assert result[2].name == "search_entities"

    def test_mixed_valid_and_invalid(self):
        """Valid tool calls are kept; invalid ones (empty name, bad JSON) are dropped."""
        from src.agents.streaming.parser import parse_tool_calls

        buffer = [
            {"name": "get_entity_state", "args": '{"entity_id": "a"}', "id": "call-1"},
            {"name": "", "args": "{}", "id": "call-2"},  # empty name
            {"name": "bad_args", "args": "{truncated", "id": "call-3"},  # bad JSON
            {"name": "search_entities", "args": '{"q": "x"}', "id": "call-4"},
        ]
        result = parse_tool_calls(buffer, is_mutating_fn=lambda _: False)
        assert len(result) == 2
        assert result[0].name == "get_entity_state"
        assert result[1].name == "search_entities"

    def test_empty_buffer(self):
        """Empty buffer should return empty list."""
        from src.agents.streaming.parser import parse_tool_calls

        result = parse_tool_calls([], is_mutating_fn=lambda _: False)
        assert result == []
