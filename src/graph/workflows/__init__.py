"""LangGraph workflows for agent orchestration.

Defines the graph structures that connect nodes into complete workflows.
All workflow entry points start a trace session for correlation.

Uses lazy imports to avoid loading all workflow implementations at import time.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    "WORKFLOW_REGISTRY": "src.graph.workflows._registry",
    "get_workflow": "src.graph.workflows._registry",
    "build_analysis_graph": "src.graph.workflows.analysis",
    "run_analysis_workflow": "src.graph.workflows.analysis",
    "build_automation_builder_graph": "src.graph.workflows.automation_builder",
    "compile_automation_builder_graph": "src.graph.workflows.automation_builder",
    "CompilationError": "src.graph.workflows.compiler",
    "WorkflowCompiler": "src.graph.workflows.compiler",
    "build_conversation_graph": "src.graph.workflows.conversation",
    "compile_conversation_graph": "src.graph.workflows.conversation",
    "resume_after_approval": "src.graph.workflows.conversation",
    "run_conversation_workflow": "src.graph.workflows.conversation",
    "DashboardWorkflow": "src.graph.workflows.dashboard",
    "build_dashboard_graph": "src.graph.workflows.dashboard",
    "ConditionalEdge": "src.graph.workflows.definition",
    "EdgeDefinition": "src.graph.workflows.definition",
    "NodeDefinition": "src.graph.workflows.definition",
    "WorkflowDefinition": "src.graph.workflows.definition",
    "build_discovery_graph": "src.graph.workflows.discovery",
    "build_simple_discovery_graph": "src.graph.workflows.discovery",
    "run_discovery_workflow": "src.graph.workflows.discovery",
    "NodeManifest": "src.graph.workflows.manifest",
    "NodeManifestEntry": "src.graph.workflows.manifest",
    "get_default_manifest": "src.graph.workflows.manifest",
    "build_optimization_graph": "src.graph.workflows.optimization",
    "run_optimization_workflow": "src.graph.workflows.optimization",
    "build_review_graph": "src.graph.workflows.review",
    "TeamAnalysisWorkflow": "src.graph.workflows.team_analysis",
    "build_team_analysis_graph": "src.graph.workflows.team_analysis",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]
    if name in _EXPORTS:
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr
    raise AttributeError(f"module 'src.graph.workflows' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
    from src.graph.workflows._registry import WORKFLOW_REGISTRY, get_workflow
    from src.graph.workflows.analysis import (
        build_analysis_graph,
        run_analysis_workflow,
    )
    from src.graph.workflows.automation_builder import (
        build_automation_builder_graph,
        compile_automation_builder_graph,
    )
    from src.graph.workflows.compiler import CompilationError, WorkflowCompiler
    from src.graph.workflows.conversation import (
        build_conversation_graph,
        compile_conversation_graph,
        resume_after_approval,
        run_conversation_workflow,
    )
    from src.graph.workflows.dashboard import (
        DashboardWorkflow,
        build_dashboard_graph,
    )
    from src.graph.workflows.definition import (
        ConditionalEdge,
        EdgeDefinition,
        NodeDefinition,
        WorkflowDefinition,
    )
    from src.graph.workflows.discovery import (
        build_discovery_graph,
        build_simple_discovery_graph,
        run_discovery_workflow,
    )
    from src.graph.workflows.manifest import (
        NodeManifest,
        NodeManifestEntry,
        get_default_manifest,
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
    "CompilationError",
    "ConditionalEdge",
    "DashboardWorkflow",
    "EdgeDefinition",
    "NodeDefinition",
    "NodeManifest",
    "NodeManifestEntry",
    "TeamAnalysisWorkflow",
    "WorkflowCompiler",
    "WorkflowDefinition",
    "build_analysis_graph",
    "build_automation_builder_graph",
    "build_conversation_graph",
    "build_dashboard_graph",
    "build_discovery_graph",
    "build_optimization_graph",
    "build_review_graph",
    "build_simple_discovery_graph",
    "build_team_analysis_graph",
    "compile_automation_builder_graph",
    "compile_conversation_graph",
    "get_default_manifest",
    "get_workflow",
    "resume_after_approval",
    "run_analysis_workflow",
    "run_conversation_workflow",
    "run_discovery_workflow",
    "run_optimization_workflow",
]
