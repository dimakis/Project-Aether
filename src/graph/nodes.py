"""Graph nodes for LangGraph workflows.

Each node is an async function that takes state and returns state updates.
Nodes are composable building blocks for agent workflows.
"""

from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from src.graph.state import (
    AgentRole,
    AnalysisState,
    ConversationState,
    ConversationStatus,
    DiscoveryState,
    DiscoveryStatus,
    EntitySummary,
    HITLApproval,
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
    # Log metrics to MLflow (lazy import to avoid early loading)
    import mlflow
    
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

    # Lazy import to avoid early loading
    import mlflow
    
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


# =============================================================================
# CONVERSATION NODES (User Story 2: Architect/Developer)
# =============================================================================


async def architect_propose_node(
    state: ConversationState,
    session: Any = None,
) -> dict[str, Any]:
    """Architect agent processes user message and proposes automation.

    Args:
        state: Current conversation state
        session: Database session

    Returns:
        State updates with response and any proposals
    """
    from src.agents import ArchitectAgent

    agent = ArchitectAgent()
    return await agent.invoke(state, session=session)


async def architect_refine_node(
    state: ConversationState,
    feedback: str,
    proposal_id: str,
    session: Any = None,
) -> dict[str, Any]:
    """Refine an existing proposal based on feedback.

    Args:
        state: Current conversation state
        feedback: User feedback
        proposal_id: ID of proposal to refine
        session: Database session

    Returns:
        State updates with refined proposal
    """
    from src.agents import ArchitectAgent

    agent = ArchitectAgent()
    return await agent.refine_proposal(state, feedback, proposal_id, session)


async def approval_gate_node(
    state: ConversationState,
) -> dict[str, Any]:
    """HITL approval gate - pauses for human approval.

    Constitution: Safety First - All automations require human approval.

    This node is configured with interrupt_before in the workflow,
    allowing the user to approve or reject pending proposals.

    Args:
        state: Current conversation state with pending approvals

    Returns:
        State updates (minimal - state managed by interrupt)
    """
    # This node is a checkpoint for HITL approval
    # The actual approval happens externally, then the graph resumes

    if not state.pending_approvals:
        # Nothing to approve, continue
        return {"status": ConversationStatus.ACTIVE}

    # Mark as waiting for approval
    return {
        "status": ConversationStatus.WAITING_APPROVAL,
        "current_agent": None,  # Human is now in control
    }


async def process_approval_node(
    state: ConversationState,
    approved: bool,
    approved_by: str = "user",
    rejection_reason: str | None = None,
    session: Any = None,
) -> dict[str, Any]:
    """Process approval or rejection of pending proposals.

    Args:
        state: Current conversation state
        approved: Whether the proposal was approved
        approved_by: Who approved (for audit)
        rejection_reason: Why it was rejected (if applicable)
        session: Database session

    Returns:
        State updates
    """
    from src.dal import ProposalRepository

    if not state.pending_approvals:
        return {"status": ConversationStatus.ACTIVE}

    updates: dict[str, Any] = {}
    approved_ids: list[str] = []
    rejected_ids: list[str] = []

    for approval in state.pending_approvals:
        if approved:
            approval.approved = True
            approval.approved_by = approved_by
            approval.approved_at = datetime.utcnow()
            approved_ids.append(approval.id)

            # Persist to DB if session available
            if session:
                repo = ProposalRepository(session)
                await repo.approve(approval.id, approved_by)
        else:
            approval.approved = False
            approval.rejection_reason = rejection_reason
            rejected_ids.append(approval.id)

            # Persist to DB if session available
            if session:
                repo = ProposalRepository(session)
                await repo.reject(approval.id, rejection_reason or "User rejected")

    if approved:
        updates["status"] = ConversationStatus.APPROVED
        updates["approved_items"] = state.approved_items + approved_ids
        updates["messages"] = [
            AIMessage(content="Your automation has been approved! Ready to deploy.")
        ]
    else:
        updates["status"] = ConversationStatus.REJECTED
        updates["rejected_items"] = state.rejected_items + rejected_ids
        updates["messages"] = [
            AIMessage(
                content=f"The automation was rejected. "
                f"Reason: {rejection_reason or 'Not specified'}. "
                f"Would you like to refine it?"
            )
        ]

    # Clear pending approvals
    updates["pending_approvals"] = []

    return updates


async def developer_deploy_node(
    state: ConversationState,
    proposal_id: str,
    session: Any = None,
) -> dict[str, Any]:
    """Deploy an approved automation.

    Args:
        state: Current conversation state
        proposal_id: ID of approved proposal to deploy
        session: Database session

    Returns:
        State updates with deployment result
    """
    from src.agents import DeveloperAgent

    agent = DeveloperAgent()
    return await agent.invoke(state, session=session, proposal_id=proposal_id)


async def developer_rollback_node(
    state: ConversationState,
    proposal_id: str,
    session: Any = None,
) -> dict[str, Any]:
    """Rollback a deployed automation.

    Args:
        state: Current conversation state
        proposal_id: ID of deployed proposal to rollback
        session: Database session

    Returns:
        State updates with rollback result
    """
    from src.agents import DeveloperAgent

    agent = DeveloperAgent()
    result = await agent.rollback_automation(proposal_id, session)

    if result.get("error"):
        return {
            "messages": [AIMessage(content=f"Rollback failed: {result['error']}")],
        }

    return {
        "messages": [
            AIMessage(
                content=f"Automation has been rolled back and disabled. "
                f"Note: {result.get('note', 'Manual cleanup may be needed.')}"
            )
        ],
        "status": ConversationStatus.COMPLETED,
    }


async def conversation_error_node(
    state: ConversationState,
    error: Exception,
) -> dict[str, Any]:
    """Handle errors in conversation workflow.

    Args:
        state: Current state
        error: The exception that occurred

    Returns:
        State updates with error info
    """
    error_msg = f"{type(error).__name__}: {error}"

    return {
        "status": ConversationStatus.FAILED,
        "messages": [
            AIMessage(
                content=f"I encountered an error: {error_msg}. "
                "Please try again or rephrase your request."
            )
        ],
    }


# =============================================================================
# DATA SCIENTIST ANALYSIS NODES (User Story 3: Energy Optimization)
# =============================================================================


async def collect_energy_data_node(
    state: AnalysisState,
    mcp_client: Any = None,
) -> dict[str, Any]:
    """Collect energy data from Home Assistant.

    Fetches energy sensor history and prepares data for analysis.

    Args:
        state: Current analysis state
        mcp_client: MCP client for HA communication

    Returns:
        State updates with collected energy data
    """
    from src.graph.state import AnalysisState
    from src.mcp import EnergyHistoryClient, get_mcp_client

    mcp = mcp_client or get_mcp_client()
    energy_client = EnergyHistoryClient(mcp)

    # Discover energy sensors if not specified
    entity_ids = state.entity_ids
    if not entity_ids:
        sensors = await energy_client.get_energy_sensors()
        entity_ids = [s["entity_id"] for s in sensors[:20]]

    # Get aggregated energy data
    energy_data = await energy_client.get_aggregated_energy(
        entity_ids,
        hours=state.time_range_hours,
    )

    return {
        "entity_ids": entity_ids,
        "messages": [
            AIMessage(
                content=f"Collected data from {len(entity_ids)} energy sensors "
                f"over {state.time_range_hours} hours. "
                f"Total consumption: {energy_data.get('total_kwh', 0):.2f} kWh"
            )
        ],
    }


async def generate_script_node(
    state: AnalysisState,
    session: Any = None,
) -> dict[str, Any]:
    """Generate analysis script using Data Scientist agent.

    Uses LLM to generate a Python script for energy analysis.

    Args:
        state: Current analysis state with energy data
        session: Optional database session

    Returns:
        State updates with generated script
    """
    from src.agents import DataScientistAgent
    from src.mcp import EnergyHistoryClient, get_mcp_client

    agent = DataScientistAgent()

    # Get energy data for script generation
    mcp = get_mcp_client()
    energy_client = EnergyHistoryClient(mcp)
    energy_data = await energy_client.get_aggregated_energy(
        state.entity_ids,
        hours=state.time_range_hours,
    )

    # Generate script
    script = await agent._generate_script(state, energy_data)

    return {
        "generated_script": script,
        "messages": [
            AIMessage(content=f"Generated analysis script ({script.count(chr(10)) + 1} lines)")
        ],
    }


async def execute_sandbox_node(
    state: AnalysisState,
) -> dict[str, Any]:
    """Execute analysis script in sandboxed environment.

    Constitution: Isolation - runs in gVisor sandbox.

    Args:
        state: State with generated script

    Returns:
        State updates with execution results
    """
    from src.graph.state import ScriptExecution
    from src.mcp import EnergyHistoryClient, get_mcp_client
    from src.sandbox.runner import SandboxRunner

    if not state.generated_script:
        return {
            "messages": [AIMessage(content="No script to execute")],
        }

    # Get fresh energy data for execution
    mcp = get_mcp_client()
    energy_client = EnergyHistoryClient(mcp)
    energy_data = await energy_client.get_aggregated_energy(
        state.entity_ids,
        hours=state.time_range_hours,
    )

    # Execute in sandbox
    import json
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(energy_data, f, default=str)
        data_path = Path(f.name)

    try:
        sandbox = SandboxRunner()
        started_at = datetime.utcnow()
        result = await sandbox.run(state.generated_script, data_path=data_path)
        completed_at = datetime.utcnow()

        execution = ScriptExecution(
            script_content=state.generated_script[:5000],
            started_at=started_at,
            completed_at=completed_at,
            stdout=result.stdout[:5000],
            stderr=result.stderr[:2000],
            exit_code=result.exit_code,
            sandbox_policy=result.policy_name,
            timed_out=result.timed_out,
        )

        status_msg = "completed successfully" if result.success else f"failed (exit code {result.exit_code})"

        return {
            "script_executions": [execution],
            "messages": [
                AIMessage(
                    content=f"Script execution {status_msg} in {result.duration_seconds:.2f}s"
                )
            ],
        }

    finally:
        try:
            data_path.unlink()
        except Exception:
            pass


async def extract_insights_node(
    state: AnalysisState,
    session: Any = None,
) -> dict[str, Any]:
    """Extract insights from script execution output.

    Parses JSON output and persists insights to database.

    Args:
        state: State with script execution results
        session: Database session for persistence

    Returns:
        State updates with extracted insights
    """
    from src.agents import DataScientistAgent
    from src.dal import InsightRepository
    from src.sandbox.runner import SandboxResult
    from src.storage.entities.insight import InsightStatus, InsightType

    if not state.script_executions:
        return {"messages": [AIMessage(content="No execution results to extract from")]}

    # Get latest execution
    execution = state.script_executions[-1]

    # Calculate duration if timestamps available
    duration = 0.0
    if execution.completed_at and execution.started_at:
        duration = (execution.completed_at - execution.started_at).total_seconds()

    # Create SandboxResult for insight extraction
    result = SandboxResult(
        success=execution.exit_code == 0,
        exit_code=execution.exit_code or 0,
        stdout=execution.stdout or "",
        stderr=execution.stderr or "",
        duration_seconds=duration,
        policy_name=execution.sandbox_policy,
        timed_out=execution.timed_out,
    )

    # Extract insights using agent
    agent = DataScientistAgent()
    insights = agent._extract_insights(result, state)
    recommendations = agent._extract_recommendations(result)

    # Persist if session available
    if session and insights:
        repo = InsightRepository(session)
        for insight_data in insights:
            try:
                insight_type = InsightType(insight_data.get("type", "energy_optimization"))
            except ValueError:
                insight_type = InsightType.ENERGY_OPTIMIZATION

            await repo.create(
                type=insight_type,
                title=insight_data.get("title", "Analysis Result"),
                description=insight_data.get("description", ""),
                evidence=insight_data.get("evidence", {}),
                confidence=insight_data.get("confidence", 0.5),
                impact=insight_data.get("impact", "medium"),
                entities=insight_data.get("entities", state.entity_ids),
                mlflow_run_id=state.mlflow_run_id,
            )

    return {
        "insights": insights,
        "recommendations": recommendations,
        "messages": [
            AIMessage(
                content=f"Extracted {len(insights)} insights and {len(recommendations)} recommendations"
            )
        ],
    }


async def analysis_error_node(
    state: AnalysisState,
    error: Exception,
) -> dict[str, Any]:
    """Handle errors in analysis workflow.

    Args:
        state: Current state
        error: The exception that occurred

    Returns:
        State updates with error info
    """
    error_msg = f"{type(error).__name__}: {error}"

    return {
        "insights": [
            {
                "type": "error",
                "title": "Analysis Failed",
                "description": error_msg,
                "confidence": 0.0,
                "impact": "low",
                "evidence": {"error": str(error)},
                "entities": state.entity_ids,
            }
        ],
        "messages": [
            AIMessage(
                content=f"Analysis encountered an error: {error_msg}. "
                "Please check your entity selection and try again."
            )
        ],
    }
