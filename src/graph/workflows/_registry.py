"""Workflow registry - central lookup for all workflow builders."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from langgraph.graph import StateGraph

from src.graph.workflows.analysis import build_analysis_graph
from src.graph.workflows.conversation import build_conversation_graph
from src.graph.workflows.dashboard import build_dashboard_graph
from src.graph.workflows.discovery import build_discovery_graph, build_simple_discovery_graph
from src.graph.workflows.optimization import build_optimization_graph
from src.graph.workflows.review import build_review_graph
from src.graph.workflows.team_analysis import build_team_analysis_graph

# Registry of available workflows
WORKFLOW_REGISTRY = {
    "discovery": build_discovery_graph,
    "discovery_simple": build_simple_discovery_graph,
    "conversation": build_conversation_graph,
    "analysis": build_analysis_graph,
    "optimization": build_optimization_graph,
    "team_analysis": build_team_analysis_graph,
    "dashboard": build_dashboard_graph,
    "review": build_review_graph,
}


def get_workflow(name: str, **kwargs: object) -> StateGraph:
    """Get a workflow graph by name.

    Args:
        name: Workflow name
        **kwargs: Arguments to pass to the builder

    Returns:
        Configured StateGraph

    Raises:
        ValueError: If workflow name is not found
    """
    if name not in WORKFLOW_REGISTRY:
        available = ", ".join(WORKFLOW_REGISTRY.keys())
        raise ValueError(f"Unknown workflow '{name}'. Available: {available}")

    return cast("Any", WORKFLOW_REGISTRY[name](**kwargs))  # type: ignore[no-any-return, operator]
