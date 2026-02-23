"""Workflow compiler (Feature 29).

Validates a ``WorkflowDefinition``, resolves node references from a
``NodeManifest``, and compiles the result into a LangGraph ``StateGraph``.

Validation catches:
- Unknown node function references
- Orphan nodes (not connected by any edge)
- Unknown state type references
- Edge references to undefined nodes
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.graph.workflows.definition import WorkflowDefinition  # noqa: TC001
from src.graph.workflows.manifest import NodeManifest  # noqa: TC001

logger = logging.getLogger(__name__)


def _get_default_state_type_map() -> dict[str, type]:
    """Build the default state type map (lazy, cached)."""
    from src.graph.state import (
        AnalysisState,
        ConversationState,
        DashboardState,
        DiscoveryState,
        OrchestratorState,
        ReviewState,
    )

    return {
        "ConversationState": ConversationState,
        "AnalysisState": AnalysisState,
        "DiscoveryState": DiscoveryState,
        "DashboardState": DashboardState,
        "ReviewState": ReviewState,
        "OrchestratorState": OrchestratorState,
    }


class CompilationError(Exception):
    """Raised when a WorkflowDefinition fails validation or compilation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Workflow compilation failed: {'; '.join(errors)}")


class WorkflowCompiler:
    """Compiles declarative WorkflowDefinitions into LangGraph StateGraphs."""

    def __init__(
        self,
        manifest: NodeManifest,
        state_type_map: dict[str, type] | None = None,
    ) -> None:
        self.manifest = manifest
        self._state_type_map = state_type_map

    def validate(self, defn: WorkflowDefinition) -> list[str]:
        """Validate a workflow definition without compiling.

        Checks: state type, node functions, duplicate IDs, edge targets,
        conditional edge targets, orphan nodes, and cycles.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []

        type_map = self._state_type_map or _get_default_state_type_map()
        if defn.state_type not in type_map:
            errors.append(
                f"Unknown state type '{defn.state_type}'. Available: {', '.join(type_map.keys())}"
            )

        # Duplicate node ID detection
        seen_ids: set[str] = set()
        for node in defn.nodes:
            if node.id in seen_ids:
                errors.append(f"Duplicate node ID '{node.id}'")
            seen_ids.add(node.id)

        node_ids = seen_ids
        special = {"__start__", "__end__"}

        for node in defn.nodes:
            if node.function not in self.manifest:
                errors.append(f"Node '{node.id}' references unknown function '{node.function}'")

        # Edge validation + connectivity tracking
        connected_nodes: set[str] = set()
        adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}

        for edge in defn.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)
            for ref in (edge.source, edge.target):
                if ref not in node_ids and ref not in special:
                    errors.append(f"Edge references undefined node '{ref}'")
            if edge.source in node_ids and edge.target in node_ids:
                adjacency[edge.source].append(edge.target)

        for ce in defn.conditional_edges:
            connected_nodes.add(ce.source)
            for cond_val, target in ce.conditions.items():
                connected_nodes.add(target)
                if target not in node_ids and target not in special:
                    errors.append(
                        f"Conditional edge from '{ce.source}' references "
                        f"undefined target '{target}' (condition '{cond_val}')"
                    )
                if ce.source in node_ids and target in node_ids:
                    adjacency[ce.source].append(target)
            if ce.default and ce.default not in node_ids and ce.default not in special:
                errors.append(
                    f"Conditional edge from '{ce.source}' has invalid default '{ce.default}'"
                )

        # Orphan detection
        orphans = node_ids - connected_nodes
        for orphan in orphans:
            errors.append(f"Node '{orphan}' is not connected by any edge (orphan)")

        # Cycle detection (DFS)
        cycle_nodes = self._detect_cycles(adjacency)
        if cycle_nodes:
            errors.append(f"Cycle detected involving nodes: {', '.join(sorted(cycle_nodes))}")

        return errors

    @staticmethod
    def _detect_cycles(adjacency: dict[str, list[str]]) -> set[str]:
        """Detect cycles in the graph using DFS. Returns nodes involved in cycles."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(adjacency, WHITE)
        cycle_nodes: set[str] = set()

        def _dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in adjacency.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    cycle_nodes.add(node)
                    cycle_nodes.add(neighbor)
                    return True
                if color[neighbor] == WHITE and _dfs(neighbor):
                    cycle_nodes.add(node)
                    return True
            color[node] = BLACK
            return False

        for node in adjacency:
            if color[node] == WHITE:
                _dfs(node)

        return cycle_nodes

    def compile(self, defn: WorkflowDefinition) -> StateGraph:
        """Validate and compile a WorkflowDefinition into a StateGraph.

        Args:
            defn: The declarative workflow definition.

        Returns:
            An uncompiled StateGraph ready for checkpointer attachment.

        Raises:
            CompilationError: If validation fails.
        """
        errors = self.validate(defn)
        if errors:
            raise CompilationError(errors)

        type_map = self._state_type_map or _get_default_state_type_map()
        state_cls = type_map.get(defn.state_type)
        if state_cls is None:
            raise CompilationError([f"Unknown state type '{defn.state_type}'"])

        graph: StateGraph = StateGraph(state_cls)

        for node in defn.nodes:
            entry = self.manifest.get(node.function)
            if entry is None:
                raise CompilationError(
                    [f"Node '{node.id}' function '{node.function}' not in manifest"]
                )
            graph.add_node(node.id, entry.function)

        for edge in defn.edges:
            source = START if edge.source == "__start__" else edge.source
            target = END if edge.target == "__end__" else edge.target
            graph.add_edge(source, target)

        for ce in defn.conditional_edges:
            path_map: dict[str, str] = {}
            for condition_val, target_id in ce.conditions.items():
                path_map[condition_val] = END if target_id == "__end__" else target_id

            def _make_router(cond_edge: Any) -> Any:
                """Create a routing function for a conditional edge."""
                conditions = cond_edge.conditions
                default = END if cond_edge.default == "__end__" else cond_edge.default
                field_name = getattr(cond_edge, "routing_field", "decision")

                def _route(state: Any) -> str:
                    decision = getattr(state, field_name, None)
                    return conditions.get(str(decision or ""), default)

                return _route

            graph.add_conditional_edges(ce.source, _make_router(ce), path_map)

        return graph
