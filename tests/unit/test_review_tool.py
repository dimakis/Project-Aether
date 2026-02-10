"""Unit tests for review_config tool (Feature 28).

Tests the tool that triggers the config review workflow.
All workflow and HA dependencies are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.review_tools import review_config


class TestReviewConfigTool:
    """Tests for the review_config tool function."""

    def test_is_langchain_tool(self):
        """review_config is a proper LangChain tool."""
        assert hasattr(review_config, "name")
        assert review_config.name == "review_config"

    def test_has_description(self):
        """review_config has a descriptive docstring for LLM usage."""
        assert review_config.description
        assert "review" in review_config.description.lower()

    @pytest.mark.asyncio
    async def test_single_target_invocation(self):
        """Tool triggers review workflow for a single target."""
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(
            return_value={
                "suggestions": [
                    {
                        "entity_id": "automation.kitchen_lights",
                        "review_notes": [
                            {"change": "test", "rationale": "r", "category": "energy"}
                        ],
                    }
                ],
            }
        )
        mock_graph.compile.return_value = mock_compiled

        with patch("src.graph.workflows.build_review_graph", return_value=mock_graph):
            result = await review_config.ainvoke({"target": "automation.kitchen_lights"})

        assert (
            "review" in result.lower()
            or "suggestion" in result.lower()
            or "automation" in result.lower()
        )
        mock_compiled.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_target_invocation(self):
        """Tool handles 'all_automations' batch target."""
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"suggestions": []})
        mock_graph.compile.return_value = mock_compiled

        with patch("src.graph.workflows.build_review_graph", return_value=mock_graph):
            result = await review_config.ainvoke({"target": "all_automations"})

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_with_focus_parameter(self):
        """Tool passes focus parameter to workflow."""
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"suggestions": []})
        mock_graph.compile.return_value = mock_compiled

        with patch("src.graph.workflows.build_review_graph", return_value=mock_graph):
            await review_config.ainvoke({"target": "automation.kitchen_lights", "focus": "energy"})

        call_args = mock_compiled.ainvoke.call_args[0][0]
        assert call_args["focus"] == "energy"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Tool returns error message on workflow failure."""
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"error": "Failed to fetch configs"})
        mock_graph.compile.return_value = mock_compiled

        with patch("src.graph.workflows.build_review_graph", return_value=mock_graph):
            result = await review_config.ainvoke({"target": "automation.nonexistent"})

        assert "error" in result.lower() or "failed" in result.lower()


class TestReviewToolRegistration:
    """Tests that review_config is in the Architect's tool set."""

    def test_in_architect_tools(self):
        """review_config is included in get_architect_tools()."""
        from src.tools import get_architect_tools

        tools = get_architect_tools()
        tool_names = [t.name for t in tools]
        assert "review_config" in tool_names
