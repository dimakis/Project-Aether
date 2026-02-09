"""Tests for the dashboard designer workflow.

Validates the LangGraph workflow for the Dashboard Designer agent,
including graph structure, registry, and wrapper class.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBuildDashboardGraph:
    """Tests for build_dashboard_graph function."""

    def test_returns_state_graph(self):
        """build_dashboard_graph returns a StateGraph."""
        from langgraph.graph import StateGraph

        from src.graph.workflows import build_dashboard_graph

        graph = build_dashboard_graph()
        assert isinstance(graph, StateGraph)

    def test_has_dashboard_designer_node(self):
        """Graph includes a 'dashboard_designer' node."""
        from src.graph.workflows import build_dashboard_graph

        graph = build_dashboard_graph()
        assert "dashboard_designer" in graph.nodes


class TestDashboardWorkflowRegistry:
    """Test that the dashboard workflow is registered."""

    def test_registered_in_workflow_registry(self):
        """'dashboard' key exists in WORKFLOW_REGISTRY."""
        from src.graph.workflows import WORKFLOW_REGISTRY

        assert "dashboard" in WORKFLOW_REGISTRY

    def test_get_workflow_returns_dashboard_graph(self):
        """get_workflow('dashboard') returns a valid graph."""
        from src.graph.workflows import get_workflow

        graph = get_workflow("dashboard")
        assert "dashboard_designer" in graph.nodes


class TestDashboardWorkflowClass:
    """Tests for the DashboardWorkflow wrapper class."""

    def test_class_exists(self):
        """DashboardWorkflow class is importable."""
        from src.graph.workflows import DashboardWorkflow

        wf = DashboardWorkflow()
        assert wf is not None

    @pytest.mark.asyncio
    async def test_run_returns_state(self):
        """run() returns a DashboardState-like dict."""
        from src.graph.workflows import DashboardWorkflow

        mock_agent = AsyncMock()
        mock_msg = MagicMock()
        mock_msg.content = "Here's your dashboard."
        mock_msg.tool_calls = []
        mock_agent.invoke = AsyncMock(return_value={"messages": [mock_msg]})

        with patch(
            "src.agents.dashboard_designer.DashboardDesignerAgent",
            return_value=mock_agent,
        ):
            wf = DashboardWorkflow()
            result = await wf.run("Design me an energy dashboard")
            assert "messages" in result or isinstance(result, dict)
