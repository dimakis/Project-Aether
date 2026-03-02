"""Discovery workflow - entity discovery and sync.

Extracts entities from Home Assistant, infers devices/areas,
syncs automations, and persists results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.ha.client import HAClient

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
from src.tracing import start_experiment_run, trace_with_uri


def build_discovery_graph(
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
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
        ha_client: Optional HA client to inject
        session: Optional database session to inject

    Returns:
        Configured StateGraph
    """
    from src.tracing import traced_node

    graph = create_graph(DiscoveryState)

    # Define node wrappers that inject dependencies
    async def _initialize(state: DiscoveryState) -> dict[str, object]:
        return await initialize_discovery_node(state)

    async def _fetch_entities(state: DiscoveryState) -> dict[str, object]:
        return await fetch_entities_node(state, ha_client=ha_client)

    async def _infer_devices(state: DiscoveryState) -> dict[str, object]:
        return await infer_devices_node(state, ha_client=ha_client)

    async def _infer_areas(state: DiscoveryState) -> dict[str, object]:
        return await infer_areas_node(state, ha_client=ha_client)

    async def _sync_automations(state: DiscoveryState) -> dict[str, object]:
        return await sync_automations_node(state, ha_client=ha_client)

    async def _persist_entities(state: DiscoveryState) -> dict[str, object]:
        return await persist_entities_node(state, session=session, ha_client=ha_client)

    async def _finalize(state: DiscoveryState) -> dict[str, object]:
        return await finalize_discovery_node(state)

    # Add nodes (traced for MLflow per-node spans)
    graph.add_node("initialize", traced_node("initialize", _initialize))
    graph.add_node("fetch_entities", traced_node("fetch_entities", _fetch_entities))
    graph.add_node("infer_devices", traced_node("infer_devices", _infer_devices))
    graph.add_node("infer_areas", traced_node("infer_areas", _infer_areas))
    graph.add_node("sync_automations", traced_node("sync_automations", _sync_automations))
    graph.add_node("persist_entities", traced_node("persist_entities", _persist_entities))
    graph.add_node("finalize", traced_node("finalize", _finalize))

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


@trace_with_uri(name="workflow.run_discovery", span_type="CHAIN")
async def run_discovery_workflow(
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
    initial_state: DiscoveryState | None = None,
) -> DiscoveryState:
    """Execute the discovery workflow.

    Starts a trace session for correlation across all operations.

    Args:
        ha_client: Optional HA client
        session: Optional database session
        initial_state: Optional initial state

    Returns:
        Final discovery state
    """
    # Start a trace session for this workflow (inherit parent session if one exists)
    from src.tracing.context import get_session_id, session_context

    # Build the graph with injected dependencies
    graph = build_discovery_graph(ha_client=ha_client, session=session)

    # Compile the graph
    compiled = graph.compile()

    # Initialize state
    if initial_state is None:
        initial_state = DiscoveryState()

    # Run with MLflow tracking and session context
    import mlflow

    with (
        session_context(get_session_id()) as session_id,
        start_experiment_run("discovery_workflow"),
    ):
        mlflow.update_current_trace(
            tags={
                "workflow": "discovery",
                **({"mlflow.trace.session": session_id} if session_id else {}),
            }
        )
        mlflow.set_tag("workflow", "discovery")
        mlflow.set_tag("session.id", session_id)

        try:
            # Execute the graph
            final_state = await compiled.ainvoke(initial_state)  # type: ignore[arg-type]

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

    async def mock_discover(state: DiscoveryState) -> dict[str, object]:
        return {
            "status": DiscoveryStatus.COMPLETED,
            "entities_added": 0,
            "entities_updated": 0,
        }

    graph.add_node("discover", mock_discover)
    graph.add_edge(START, "discover")
    graph.add_edge("discover", END)

    return graph
