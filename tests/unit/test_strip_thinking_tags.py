"""Unit tests for _strip_thinking_tags and _normalize_content.

Tests the thinking-tag stripping logic used by the OpenAI-compatible
streaming endpoint. Covers closed tags, unclosed tags, list content
(from LangChain providers), and edge cases.
"""

from src.api.routes.openai_compat import _extract_text_content, _strip_thinking_tags

# --- Closed tag pairs (existing behaviour) ---


class TestClosedTagPairs:
    """_strip_thinking_tags should remove complete <tag>...</tag> blocks."""

    def test_single_think_tag(self):
        content = "<think>reasoning here</think>The answer is 42."
        assert _strip_thinking_tags(content) == "The answer is 42."

    def test_single_thinking_tag(self):
        content = "<thinking>some reasoning</thinking>Result."
        assert _strip_thinking_tags(content) == "Result."

    def test_reasoning_tag(self):
        content = "<reasoning>analysis</reasoning>Conclusion."
        assert _strip_thinking_tags(content) == "Conclusion."

    def test_thought_tag(self):
        content = "<thought>hmm</thought>Done."
        assert _strip_thinking_tags(content) == "Done."

    def test_reflection_tag(self):
        content = "<reflection>review</reflection>Final answer."
        assert _strip_thinking_tags(content) == "Final answer."

    def test_multiple_thinking_blocks(self):
        content = "<think>step 1</think>Part A. <think>step 2</think>Part B."
        assert _strip_thinking_tags(content) == "Part A. Part B."

    def test_multiple_tag_types(self):
        content = "<think>a</think>Hello <reasoning>b</reasoning>World"
        assert _strip_thinking_tags(content) == "Hello World"

    def test_case_insensitive(self):
        content = "<Think>reasoning</Think>Result."
        assert _strip_thinking_tags(content) == "Result."

    def test_multiline_thinking_content(self):
        content = "<think>\nLine 1\nLine 2\nLine 3\n</think>\nVisible output."
        assert _strip_thinking_tags(content) == "Visible output."


# --- Unclosed tags (the bug scenario) ---


class TestUnclosedTags:
    """Unclosed thinking tags should be stripped to prevent the
    frontend from consuming all remaining content as 'thinking'."""

    def test_unclosed_think_tag_only(self):
        """Model outputs only an unclosed <think> block — result is empty."""
        content = "<think>reasoning without closing tag"
        assert _strip_thinking_tags(content) == ""

    def test_unclosed_think_tag_with_leading_text(self):
        """Visible text before the unclosed tag should be preserved."""
        content = "Hello World. <think>some reasoning that never closes"
        assert _strip_thinking_tags(content) == "Hello World."

    def test_unclosed_thinking_tag(self):
        content = "<thinking>deep analysis still going"
        assert _strip_thinking_tags(content) == ""

    def test_unclosed_reasoning_tag(self):
        content = "<reasoning>analysis in progress"
        assert _strip_thinking_tags(content) == ""


# --- List content (LangChain provider edge case) ---


class TestListContent:
    """AIMessage.content can be a list of content blocks for some
    LangChain providers (e.g. Anthropic Claude). The function must
    gracefully extract text."""

    def test_list_with_single_text_block(self):
        content = [{"type": "text", "text": "Hello world"}]
        assert _strip_thinking_tags(content) == "Hello world"

    def test_list_with_multiple_text_blocks(self):
        content = [
            {"type": "text", "text": "Part 1."},
            {"type": "text", "text": "Part 2."},
        ]
        # _extract_text_content joins with \n
        assert _strip_thinking_tags(content) == "Part 1.\nPart 2."

    def test_list_with_thinking_in_text_block(self):
        content = [
            {"type": "text", "text": "<think>reasoning</think>The answer."},
        ]
        assert _strip_thinking_tags(content) == "The answer."

    def test_list_with_non_text_blocks_ignored(self):
        content = [
            {"type": "thinking", "thinking": "internal reasoning"},
            {"type": "text", "text": "Visible answer."},
        ]
        assert _strip_thinking_tags(content) == "Visible answer."

    def test_empty_list(self):
        content = []
        assert _strip_thinking_tags(content) == ""


# --- _extract_text_content ---


class TestExtractTextContent:
    """Direct tests for _extract_text_content helper."""

    def test_string_passthrough(self):
        assert _extract_text_content("hello") == "hello"

    def test_none_returns_empty(self):
        assert _extract_text_content(None) == ""

    def test_list_of_strings(self):
        assert _extract_text_content(["a", "b"]) == "a\nb"

    def test_list_of_dicts_with_text_key(self):
        blocks = [{"text": "hello"}, {"text": "world"}]
        assert _extract_text_content(blocks) == "hello\nworld"

    def test_list_of_dicts_with_content_key(self):
        blocks = [{"content": "hello"}]
        assert _extract_text_content(blocks) == "hello"

    def test_mixed_block_types(self):
        blocks = [
            {"type": "text", "text": "visible"},
            {"type": "tool_use", "id": "abc"},
        ]
        # tool_use block has no text/content key → skipped
        assert _extract_text_content(blocks) == "visible"

    def test_fallback_to_str(self):
        assert _extract_text_content(42) == "42"


# --- Edge cases ---


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_string(self):
        assert _strip_thinking_tags("") == ""

    def test_no_thinking_tags(self):
        content = "Just a normal response with no tags."
        assert _strip_thinking_tags(content) == "Just a normal response with no tags."

    def test_content_is_only_whitespace_after_strip(self):
        content = "<think>all thinking</think>   \n  "
        assert _strip_thinking_tags(content) == ""

    def test_angle_brackets_not_thinking_tags(self):
        """Angle brackets that aren't thinking tags should be preserved."""
        content = "Use <div> tags in HTML."
        assert _strip_thinking_tags(content) == "Use <div> tags in HTML."

    def test_nested_angle_brackets_in_thinking(self):
        content = "<think>The user asked about <div> tags</think>Here is the answer."
        assert _strip_thinking_tags(content) == "Here is the answer."
