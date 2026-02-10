"""LangGraph workflows for agent orchestration.

Defines the graph structures that connect nodes into complete workflows.
All workflow entry points start a trace session for correlation.

This package re-exports every public name so that existing consumers
(``from src.graph.workflows import X``) continue to work unchanged.
"""

from src.graph.workflows._registry import WORKFLOW_REGISTRY, get_workflow
from src.graph.workflows.analysis import build_analysis_graph, run_analysis_workflow
from src.graph.workflows.conversation import (
    build_conversation_graph,
    compile_conversation_graph,
    resume_after_approval,
    run_conversation_workflow,
)
from src.graph.workflows.dashboard import DashboardWorkflow, build_dashboard_graph
from src.graph.workflows.discovery import (
    build_discovery_graph,
    build_simple_discovery_graph,
    run_discovery_workflow,
)
from src.graph.workflows.optimization import (
    build_optimization_graph,
    run_optimization_workflow,
)
from src.graph.workflows.review import build_review_graph
from src.graph.workflows.team_analysis import (
    TeamAnalysisWorkflow,
    build_team_analysis_graph,
)

__all__ = [
    "WORKFLOW_REGISTRY",
    "DashboardWorkflow",
    "TeamAnalysisWorkflow",
    "build_analysis_graph",
    "build_conversation_graph",
    "build_dashboard_graph",
    "build_discovery_graph",
    "build_optimization_graph",
    "build_review_graph",
    "build_simple_discovery_graph",
    "build_team_analysis_graph",
    "compile_conversation_graph",
    "get_workflow",
    "resume_after_approval",
    "run_analysis_workflow",
    "run_conversation_workflow",
    "run_discovery_workflow",
    "run_optimization_workflow",
]
