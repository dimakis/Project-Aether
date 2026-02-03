"""Graph nodes for LangGraph workflows.

Each node is an async function that takes state and returns state updates.
Nodes are composable building blocks for agent workflows.
"""

from datetime import datetime
from typing import Any

import mlflow

from src.graph.state import (
    AgentRole,
    DiscoveryState,
    DiscoveryStatus,
    EntitySummary,
)


# =============================================================================
# LIBRARIAN DISCOVERY NODES
# =============================================================================


async def initialize_discovery_node(state: DiscoveryState) -> dict[str, Any]:
    """Initialize discovery run.

    Sets up the discovery state and logs start time.

    Args:
        state: Current discovery state

    Returns:
        State updates
    """
    return {
        "current_agent": AgentRole.LIBRARIAN,
        "status": DiscoveryStatus.RUNNING,
    }


async def fetch_entities_node(
    state: DiscoveryState,
    mcp_client: Any = None,
) -> dict[str, Any]:
    """Fetch entities from Home Assistant via MCP.

    Args:
        state: Current discovery state
        mcp_client: MCP client for HA communication

    Returns:
        State updates with fetched entities
    """
    from src.mcp import MCPClient, get_mcp_client, parse_entity_list

    mcp: MCPClient = mcp_client or get_mcp_client()

    # Fetch all entities
    raw_entities = await mcp.list_entities(detailed=True)
    entities = parse_entity_list(raw_entities)

    # Convert to EntitySummary
    entity_summaries = [
        EntitySummary(
            entity_id=e.entity_id,
            domain=e.domain,
            name=e.name,
            state=e.state or "unknown",
            area_id=e.area_id,
            device_id=e.device_id,
        )
        for e in entities
    ]

    # Track domains
    domains = list(set(e.domain for e in entity_summaries))

    return {
        "entities_found": entity_summaries,
        "domains_scanned": domains,
    }


async def infer_devices_node(
    state: DiscoveryState,
    mcp_client: Any = None,
) -> dict[str, Any]:
    """Infer devices from entity attributes.

    MCP Gap: No list_devices tool, so we infer from entity attributes.

    Args:
        state: State with fetched entities
        mcp_client: MCP client (unused, but kept for consistency)

    Returns:
        State updates with device count
    """
    # Get unique device IDs from entities
    device_ids = set()
    for entity in state.entities_found:
        if entity.device_id:
            device_ids.add(entity.device_id)

    return {
        "devices_found": len(device_ids),
    }


async def infer_areas_node(
    state: DiscoveryState,
    mcp_client: Any = None,
) -> dict[str, Any]:
    """Infer areas from entity attributes.

    MCP Gap: No list_areas tool, so we infer from entity area_id.

    Args:
        state: State with fetched entities
        mcp_client: MCP client (unused, but kept for consistency)

    Returns:
        State updates with area count
    """
    # Get unique area IDs from entities
    area_ids = set()
    for entity in state.entities_found:
        if entity.area_id:
            area_ids.add(entity.area_id)

    return {
        "areas_found": len(area_ids),
    }


async def sync_automations_node(
    state: DiscoveryState,
    mcp_client: Any = None,
) -> dict[str, Any]:
    """Sync automations from Home Assistant.

    Uses list_automations MCP tool for automation details.

    Args:
        state: Current state
        mcp_client: MCP client

    Returns:
        State updates with automation info
    """
    from src.mcp import get_mcp_client

    mcp = mcp_client or get_mcp_client()

    try:
        # Fetch automations
        automations = await mcp.list_automations()
        automation_count = len(automations) if automations else 0

        # Count scripts and scenes from already-fetched entities
        script_count = sum(1 for e in state.entities_found if e.domain == "script")
        scene_count = sum(1 for e in state.entities_found if e.domain == "scene")

        return {
            "services_found": automation_count + script_count + scene_count,
        }

    except Exception as e:
        # Log but don't fail - automations are optional
        return {
            "errors": state.errors + [f"Automation sync warning: {e}"],
        }


async def persist_entities_node(
    state: DiscoveryState,
    session: Any = None,
    mcp_client: Any = None,
) -> dict[str, Any]:
    """Persist entities to database.

    Args:
        state: State with entities to persist
        session: Database session
        mcp_client: MCP client for sync service

    Returns:
        State updates with sync statistics
    """
    from src.dal import DiscoverySyncService
    from src.mcp import get_mcp_client
    from src.storage import get_session

    mcp = mcp_client or get_mcp_client()

    # Use provided session or create new one
    if session:
        sync_service = DiscoverySyncService(session, mcp)
        discovery = await sync_service.run_discovery(
            triggered_by="graph",
            mlflow_run_id=state.mlflow_run_id,
        )
    else:
        async with get_session() as new_session:
            sync_service = DiscoverySyncService(new_session, mcp)
            discovery = await sync_service.run_discovery(
                triggered_by="graph",
                mlflow_run_id=state.mlflow_run_id,
            )

    return {
        "entities_added": discovery.entities_added,
        "entities_updated": discovery.entities_updated,
        "entities_removed": discovery.entities_removed,
        "status": DiscoveryStatus.COMPLETED,
    }


async def finalize_discovery_node(state: DiscoveryState) -> dict[str, Any]:
    """Finalize discovery and log metrics.

    Args:
        state: Final discovery state

    Returns:
        Final state updates
    """
    # Log metrics to MLflow
    if mlflow.active_run():
        mlflow.log_metrics({
            "entities_found": len(state.entities_found),
            "entities_added": state.entities_added,
            "entities_updated": state.entities_updated,
            "entities_removed": state.entities_removed,
            "devices_found": state.devices_found,
            "areas_found": state.areas_found,
            "domains_count": len(state.domains_scanned),
        })
        mlflow.set_tag("status", state.status.value)

    return {
        "status": DiscoveryStatus.COMPLETED if not state.errors else DiscoveryStatus.FAILED,
    }


# =============================================================================
# SHARED UTILITY NODES
# =============================================================================


async def error_handler_node(
    state: DiscoveryState,
    error: Exception,
) -> dict[str, Any]:
    """Handle errors in graph execution.

    Args:
        state: Current state
        error: The exception that occurred

    Returns:
        State updates with error info
    """
    error_msg = f"{type(error).__name__}: {error}"

    if mlflow.active_run():
        mlflow.set_tag("error", "true")
        mlflow.log_param("error_message", error_msg[:500])

    return {
        "status": DiscoveryStatus.FAILED,
        "errors": state.errors + [error_msg],
    }


async def run_discovery_node(
    state: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Unified discovery node for agent invocation.

    This is called from the LibrarianAgent.invoke method.

    Args:
        state: Current state
        **kwargs: Additional arguments

    Returns:
        State updates
    """
    from src.graph.workflows import run_discovery_workflow

    mcp_client = kwargs.get("mcp_client")
    session = kwargs.get("session")

    result_state = await run_discovery_workflow(
        mcp_client=mcp_client,
        session=session,
    )

    return {
        "entities_found": result_state.entities_found,
        "entities_added": result_state.entities_added,
        "entities_updated": result_state.entities_updated,
        "entities_removed": result_state.entities_removed,
        "devices_found": result_state.devices_found,
        "areas_found": result_state.areas_found,
        "status": result_state.status,
        "errors": result_state.errors,
    }
