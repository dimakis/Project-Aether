"""Tests for the config review workflow graph (Feature 28).

Validates LangGraph workflow structure, node connectivity,
and workflow registry integration.
"""


class TestBuildReviewGraph:
    """Tests for build_review_graph function."""

    def test_returns_state_graph(self):
        """build_review_graph returns a StateGraph."""
        from langgraph.graph import StateGraph

        from src.graph.workflows import build_review_graph

        graph = build_review_graph()
        assert isinstance(graph, StateGraph)

    def test_has_all_required_nodes(self):
        """Graph includes all review workflow nodes."""
        from src.graph.workflows import build_review_graph

        graph = build_review_graph()
        expected_nodes = {
            "resolve_targets",
            "fetch_configs",
            "gather_context",
            "consult_ds_team",
            "architect_synthesize",
            "create_review_proposals",
        }
        for node_name in expected_nodes:
            assert node_name in graph.nodes, f"Missing node: {node_name}"

    def test_node_count(self):
        """Graph has exactly the expected number of nodes."""
        from src.graph.workflows import build_review_graph

        graph = build_review_graph()
        # 6 workflow nodes (START/END are special)
        assert len(graph.nodes) == 6


class TestReviewWorkflowRegistry:
    """Test that the review workflow is registered."""

    def test_registered_in_workflow_registry(self):
        """'review' key exists in WORKFLOW_REGISTRY."""
        from src.graph.workflows import WORKFLOW_REGISTRY

        assert "review" in WORKFLOW_REGISTRY

    def test_get_workflow_returns_review_graph(self):
        """get_workflow('review') returns a valid graph."""
        from src.graph.workflows import get_workflow

        graph = get_workflow("review")
        assert "resolve_targets" in graph.nodes
        assert "create_review_proposals" in graph.nodes
