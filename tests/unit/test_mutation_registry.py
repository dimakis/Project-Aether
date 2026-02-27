"""Unit tests for the mutation registry.

Tests the fail-safe whitelist approach: read-only tools are
explicitly listed; everything else is treated as mutating.
"""

from __future__ import annotations

import pytest

from src.tools.mutation_registry import (
    READ_ONLY_TOOLS,
    is_mutating_tool,
    register_read_only_tool,
)


class TestReadOnlyTools:
    """Tests for the READ_ONLY_TOOLS frozenset."""

    @pytest.mark.parametrize(
        "tool_name",
        ["get_entity_state", "web_search", "seek_approval"],
    )
    def test_contains_expected_tools(self, tool_name: str) -> None:
        assert tool_name in READ_ONLY_TOOLS


class TestIsMutatingTool:
    """Tests for is_mutating_tool()."""

    @pytest.mark.parametrize(
        "tool_name",
        ["get_entity_state", "web_search", "seek_approval", "render_template"],
    )
    def test_returns_false_for_read_only_tools(self, tool_name: str) -> None:
        assert is_mutating_tool(tool_name) is False

    def test_returns_true_for_unknown_tool(self) -> None:
        """Unknown tools are fail-safe treated as mutating."""
        assert is_mutating_tool("call_service") is True
        assert is_mutating_tool("totally_new_tool") is True


class TestRegisterReadOnlyTool:
    """Tests for register_read_only_tool()."""

    def test_adds_new_tool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dynamically registered tool becomes read-only."""
        import src.tools.mutation_registry as mod

        original = mod.READ_ONLY_TOOLS
        monkeypatch.setattr(mod, "READ_ONLY_TOOLS", frozenset(original))

        register_read_only_tool("my_custom_reader")
        assert not is_mutating_tool("my_custom_reader")

        monkeypatch.setattr(mod, "READ_ONLY_TOOLS", original)
