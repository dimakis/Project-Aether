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


def register_dynamic_workflow(name: str, builder: object) -> None:
    """Register a dynamic workflow builder at runtime.

    Args:
        name: Workflow name (used as lookup key).
        builder: A callable that returns a StateGraph when called.
    """
    WORKFLOW_REGISTRY[name] = builder  # type: ignore[assignment]


def unregister_dynamic_workflow(name: str) -> None:
    """Remove a dynamic workflow from the registry."""
    WORKFLOW_REGISTRY.pop(name, None)


def compile_and_register(
    defn: object,
    manifest: object,
) -> None:
    """Compile a WorkflowDefinition and register it in the registry.

    Args:
        defn: A WorkflowDefinition instance.
        manifest: A NodeManifest instance for resolving node functions.

    Raises:
        TypeError: If arguments are not the expected types.
    """
    from src.graph.workflows.compiler import WorkflowCompiler
    from src.graph.workflows.definition import WorkflowDefinition
    from src.graph.workflows.manifest import NodeManifest

    if not isinstance(defn, WorkflowDefinition):
        raise TypeError(f"Expected WorkflowDefinition, got {type(defn).__name__}")
    if not isinstance(manifest, NodeManifest):
        raise TypeError(f"Expected NodeManifest, got {type(manifest).__name__}")

    compiler = WorkflowCompiler(manifest)
    graph = compiler.compile(defn)
    register_dynamic_workflow(defn.name, lambda _defn=defn, _g=graph: _g)


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
