"""LangGraph workflows for agent orchestration.

Defines the graph structures that connect nodes into complete workflows.
"""

from typing import Any, Literal

import mlflow
from langgraph.checkpoint.memory import MemorySaver

from src.graph import END, START, StateGraph, create_graph
from src.graph.nodes import (
    # Discovery nodes
    fetch_entities_node,
    finalize_discovery_node,
    infer_areas_node,
    infer_devices_node,
    initialize_discovery_node,
    persist_entities_node,
    sync_automations_node,
    # Conversation nodes
    approval_gate_node,
    architect_propose_node,
    conversation_error_node,
    developer_deploy_node,
    developer_rollback_node,
    process_approval_node,
)
from src.graph.state import (
    ConversationState,
    ConversationStatus,
    DiscoveryState,
    DiscoveryStatus,
)
from src.tracing import start_experiment_run, trace_with_uri


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


@trace_with_uri(name="workflow.run_discovery", span_type="CHAIN")
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
# CONVERSATION WORKFLOW (User Story 2: Architect/Developer)
# =============================================================================


def build_conversation_graph(
    session: Any = None,
    checkpointer: Any = None,
) -> StateGraph:
    """Build the conversation workflow graph for automation design.

    Graph structure:
    ```
    START
      │
      ▼
    architect_propose  ◄────────┐
      │                        │
      ▼                        │
    [has_proposal?]            │
      │     │                  │
      Y     N──────► END       │
      │                        │
      ▼                        │
    approval_gate (HITL)       │
      │                        │
      ▼                        │
    process_approval           │
      │                        │
      ├── approved ───► deploy │
      │                   │    │
      │                   ▼    │
      │                  END   │
      │                        │
      └── rejected ────────────┘ (refine loop)
    ```

    Constitution: Safety First - HITL approval required before deployment.

    Args:
        session: Database session for persistence
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Configured StateGraph with HITL interrupt
    """
    graph = create_graph(ConversationState)

    # Define node wrappers with injected dependencies
    async def _architect_propose(state: ConversationState) -> dict[str, Any]:
        return await architect_propose_node(state, session=session)

    async def _approval_gate(state: ConversationState) -> dict[str, Any]:
        return await approval_gate_node(state)

    async def _process_approval(state: ConversationState) -> dict[str, Any]:
        # Default to rejection if no explicit approval
        # Real approval happens via external input before resuming
        approved = state.status == ConversationStatus.APPROVED
        return await process_approval_node(
            state,
            approved=approved,
            session=session,
        )

    async def _deploy(state: ConversationState) -> dict[str, Any]:
        if state.approved_items:
            proposal_id = state.approved_items[-1]
            return await developer_deploy_node(state, proposal_id, session=session)
        return {"error": "No approved proposals to deploy"}

    # Add nodes
    graph.add_node("architect_propose", _architect_propose)
    graph.add_node("approval_gate", _approval_gate)
    graph.add_node("process_approval", _process_approval)
    graph.add_node("deploy", _deploy)

    # Define routing
    def route_after_propose(state: ConversationState) -> Literal["approval_gate", "__end__"]:
        """Route based on whether proposal was created."""
        if state.pending_approvals:
            return "approval_gate"
        return END

    def route_after_approval(
        state: ConversationState,
    ) -> Literal["deploy", "architect_propose", "__end__"]:
        """Route based on approval decision."""
        if state.status == ConversationStatus.APPROVED:
            return "deploy"
        elif state.status == ConversationStatus.REJECTED:
            # Allow refinement loop
            return "architect_propose"
        return END

    # Define edges
    graph.add_edge(START, "architect_propose")
    graph.add_conditional_edges("architect_propose", route_after_propose)
    graph.add_edge("approval_gate", "process_approval")
    graph.add_conditional_edges("process_approval", route_after_approval)
    graph.add_edge("deploy", END)

    return graph


def compile_conversation_graph(
    session: Any = None,
    thread_id: str | None = None,
) -> Any:
    """Compile the conversation graph with HITL interrupt.

    Constitution: Safety First - interrupt_before at approval_gate
    ensures human approval before any deployment.

    Args:
        session: Database session
        thread_id: Optional thread ID for checkpointing

    Returns:
        Compiled graph with checkpointing and HITL interrupts
    """
    # Create checkpointer for state persistence
    checkpointer = MemorySaver()

    # Build graph
    graph = build_conversation_graph(session=session)

    # Compile with interrupt_before at approval gate
    # This pauses execution for HITL approval
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval_gate"],  # HITL: Pause before approval
    )

    return compiled


@trace_with_uri(name="workflow.run_conversation", span_type="CHAIN")
async def run_conversation_workflow(
    user_message: str,
    session: Any = None,
    thread_id: str | None = None,
    existing_state: ConversationState | None = None,
) -> ConversationState:
    """Execute the conversation workflow.

    Args:
        user_message: User's message
        session: Database session
        thread_id: Thread ID for checkpointing
        existing_state: Optional existing state to continue

    Returns:
        Updated conversation state
    """
    from langchain_core.messages import HumanMessage

    # Compile graph
    compiled = compile_conversation_graph(session=session, thread_id=thread_id)

    # Initialize or update state
    if existing_state:
        # Add new user message
        state = existing_state.model_copy()
        state.messages.append(HumanMessage(content=user_message))
    else:
        state = ConversationState(
            messages=[HumanMessage(content=user_message)],
        )

    # Run with MLflow tracking
    with start_experiment_run("conversation_workflow") as run:
        mlflow.set_tag("workflow", "conversation")
        mlflow.set_tag("thread_id", thread_id or state.conversation_id)

        try:
            # Execute the graph
            config = {"configurable": {"thread_id": thread_id or state.conversation_id}}
            final_state = await compiled.ainvoke(state, config=config)

            # Handle the result
            if isinstance(final_state, dict):
                result = state.model_copy(update=final_state)
            else:
                result = final_state

            mlflow.set_tag("status", result.status.value)
            return result

        except Exception as e:
            mlflow.set_tag("status", "failed")
            mlflow.log_param("error", str(e)[:500])
            raise


async def resume_after_approval(
    thread_id: str,
    approved: bool,
    approved_by: str = "user",
    rejection_reason: str | None = None,
    session: Any = None,
) -> ConversationState:
    """Resume conversation workflow after HITL approval decision.

    Args:
        thread_id: Thread ID to resume
        approved: Whether proposal was approved
        approved_by: Who approved
        rejection_reason: Why rejected (if applicable)
        session: Database session

    Returns:
        Updated conversation state after resumption
    """
    from src.dal import ProposalRepository

    # Compile graph with same checkpointer
    compiled = compile_conversation_graph(session=session, thread_id=thread_id)
    config = {"configurable": {"thread_id": thread_id}}

    # Get current state
    state_snapshot = compiled.get_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise ValueError(f"No state found for thread {thread_id}")

    current_state = ConversationState(**state_snapshot.values)

    # Process approvals in database
    if session and current_state.pending_approvals:
        repo = ProposalRepository(session)
        for approval in current_state.pending_approvals:
            if approved:
                await repo.approve(approval.id, approved_by)
            else:
                await repo.reject(approval.id, rejection_reason or "User rejected")

    # Update state with approval decision
    if approved:
        current_state.status = ConversationStatus.APPROVED
        current_state.approved_items.extend(
            [a.id for a in current_state.pending_approvals]
        )
    else:
        current_state.status = ConversationStatus.REJECTED
        current_state.rejected_items.extend(
            [a.id for a in current_state.pending_approvals]
        )

    # Update the state in the graph
    compiled.update_state(config, current_state.model_dump())

    # Resume execution
    final_state = await compiled.ainvoke(None, config=config)

    if isinstance(final_state, dict):
        return current_state.model_copy(update=final_state)
    return final_state


# =============================================================================
# GRAPH REGISTRY
# =============================================================================

# Registry of available workflows
WORKFLOW_REGISTRY = {
    "discovery": build_discovery_graph,
    "discovery_simple": build_simple_discovery_graph,
    "conversation": build_conversation_graph,
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
