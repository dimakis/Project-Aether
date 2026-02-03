"""LangGraph workflows for agent orchestration.

Defines the graph structures that connect nodes into complete workflows.
"""

from typing import Any

import mlflow

from src.graph import END, START, StateGraph, create_graph
from src.graph.nodes import (
    fetch_entities_node,
    finalize_discovery_node,
    infer_areas_node,
    infer_devices_node,
    initialize_discovery_node,
    persist_entities_node,
    sync_automations_node,
)
from src.graph.state import DiscoveryState, DiscoveryStatus
from src.tracing import start_experiment_run


def build_discovery_graph(
    mcp_client: Any = None,
    session: Any = None,
) -> StateGraph:
    """Build the entity discovery workflow graph.

    Graph structure:
    ```
    START
      │
      ▼
    initialize
      │
      ▼
    fetch_entities
      │
      ├─────────────┐
      ▼             ▼
    infer_devices  infer_areas
      │             │
      └──────┬──────┘
             ▼
       sync_automations
             │
             ▼
       persist_entities
             │
             ▼
       finalize
             │
             ▼
           END
    ```

    Args:
        mcp_client: Optional MCP client to inject
        session: Optional database session to inject

    Returns:
        Configured StateGraph
    """
    graph = create_graph(DiscoveryState)

    # Define node wrappers that inject dependencies
    async def _initialize(state: DiscoveryState) -> dict[str, Any]:
        return await initialize_discovery_node(state)

    async def _fetch_entities(state: DiscoveryState) -> dict[str, Any]:
        return await fetch_entities_node(state, mcp_client=mcp_client)

    async def _infer_devices(state: DiscoveryState) -> dict[str, Any]:
        return await infer_devices_node(state, mcp_client=mcp_client)

    async def _infer_areas(state: DiscoveryState) -> dict[str, Any]:
        return await infer_areas_node(state, mcp_client=mcp_client)

    async def _sync_automations(state: DiscoveryState) -> dict[str, Any]:
        return await sync_automations_node(state, mcp_client=mcp_client)

    async def _persist_entities(state: DiscoveryState) -> dict[str, Any]:
        return await persist_entities_node(state, session=session, mcp_client=mcp_client)

    async def _finalize(state: DiscoveryState) -> dict[str, Any]:
        return await finalize_discovery_node(state)

    # Add nodes
    graph.add_node("initialize", _initialize)
    graph.add_node("fetch_entities", _fetch_entities)
    graph.add_node("infer_devices", _infer_devices)
    graph.add_node("infer_areas", _infer_areas)
    graph.add_node("sync_automations", _sync_automations)
    graph.add_node("persist_entities", _persist_entities)
    graph.add_node("finalize", _finalize)

    # Define edges
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "fetch_entities")

    # Parallel inference (conceptually - LangGraph handles sequentially)
    graph.add_edge("fetch_entities", "infer_devices")
    graph.add_edge("infer_devices", "infer_areas")

    # Continue to automation sync
    graph.add_edge("infer_areas", "sync_automations")
    graph.add_edge("sync_automations", "persist_entities")
    graph.add_edge("persist_entities", "finalize")
    graph.add_edge("finalize", END)

    return graph


async def run_discovery_workflow(
    mcp_client: Any = None,
    session: Any = None,
    initial_state: DiscoveryState | None = None,
) -> DiscoveryState:
    """Execute the discovery workflow.

    Args:
        mcp_client: Optional MCP client
        session: Optional database session
        initial_state: Optional initial state

    Returns:
        Final discovery state
    """
    # Build the graph with injected dependencies
    graph = build_discovery_graph(mcp_client=mcp_client, session=session)

    # Compile the graph
    compiled = graph.compile()

    # Initialize state
    if initial_state is None:
        initial_state = DiscoveryState()

    # Run with MLflow tracking
    with start_experiment_run("discovery_workflow") as run:
        mlflow.set_tag("workflow", "discovery")

        try:
            # Execute the graph
            final_state = await compiled.ainvoke(initial_state)

            # Handle the result
            if isinstance(final_state, dict):
                # Merge into state
                result = initial_state.model_copy(update=final_state)
            else:
                result = final_state

            mlflow.set_tag("status", result.status.value)
            return result

        except Exception as e:
            mlflow.set_tag("status", "failed")
            mlflow.log_param("error", str(e)[:500])
            raise


def build_simple_discovery_graph() -> StateGraph:
    """Build a simplified discovery graph for testing.

    This version doesn't require external dependencies and
    is useful for unit testing the graph structure.

    Returns:
        Simple StateGraph
    """
    graph = create_graph(DiscoveryState)

    async def mock_discover(state: DiscoveryState) -> dict[str, Any]:
        return {
            "status": DiscoveryStatus.COMPLETED,
            "entities_added": 0,
            "entities_updated": 0,
        }

    graph.add_node("discover", mock_discover)
    graph.add_edge(START, "discover")
    graph.add_edge("discover", END)

    return graph


# =============================================================================
# GRAPH REGISTRY
# =============================================================================

# Registry of available workflows
WORKFLOW_REGISTRY = {
    "discovery": build_discovery_graph,
    "discovery_simple": build_simple_discovery_graph,
}


def get_workflow(name: str, **kwargs: Any) -> StateGraph:
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

    return WORKFLOW_REGISTRY[name](**kwargs)
