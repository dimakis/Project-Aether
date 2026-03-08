"""Conversation workflow - Architect/Developer HITL loop.

Handles the propose → approve → deploy cycle with
human-in-the-loop interrupts (Constitution: Safety First).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from langgraph.checkpoint.memory import MemorySaver

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from src.graph import END, START, StateGraph, create_graph
from src.graph.nodes import (
    approval_gate_node,
    architect_propose_node,
    developer_deploy_node,
    process_approval_node,
)
from src.graph.state import ConversationState, ConversationStatus
from src.tracing import start_experiment_run, trace_with_uri, traced_node


def build_conversation_graph(
    session: AsyncSession | None = None,
    checkpointer: object | None = None,
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
    async def _architect_propose(state: ConversationState) -> dict[str, object]:
        return await architect_propose_node(state, session=session)

    async def _approval_gate(state: ConversationState) -> dict[str, object]:
        return await approval_gate_node(state)

    async def _process_approval(state: ConversationState) -> dict[str, object]:
        # Default to rejection if no explicit approval
        # Real approval happens via external input before resuming
        approved = state.status == ConversationStatus.APPROVED
        return await process_approval_node(
            state,
            approved=approved,
            session=session,
        )

    async def _deploy(state: ConversationState) -> dict[str, object]:
        if state.approved_items:
            proposal_id = state.approved_items[-1]
            return await developer_deploy_node(state, proposal_id, session=session)
        return {"error": "No approved proposals to deploy"}

    # Add nodes (traced for MLflow per-node spans)
    graph.add_node("architect_propose", traced_node("architect_propose", _architect_propose))
    graph.add_node("approval_gate", traced_node("approval_gate", _approval_gate))
    graph.add_node("process_approval", traced_node("process_approval", _process_approval))
    graph.add_node("deploy", traced_node("deploy", _deploy))

    # Define routing
    def route_after_propose(
        state: ConversationState,
    ) -> Literal["approval_gate", "__end__"]:
        """Route based on whether proposal was created."""
        if state.pending_approvals:
            return "approval_gate"  # type: ignore[return-value]
        return END  # type: ignore[return-value]

    def route_after_approval(
        state: ConversationState,
    ) -> Literal["deploy", "architect_propose", "__end__"]:
        """Route based on approval decision."""
        if state.status == ConversationStatus.APPROVED:
            return "deploy"  # type: ignore[return-value]
        elif state.status == ConversationStatus.REJECTED:
            # Allow refinement loop
            return "architect_propose"  # type: ignore[return-value]
        return END  # type: ignore[return-value]

    # Define edges
    graph.add_edge(START, "architect_propose")
    graph.add_conditional_edges("architect_propose", route_after_propose)
    graph.add_edge("approval_gate", "process_approval")
    graph.add_conditional_edges("process_approval", route_after_approval)
    graph.add_edge("deploy", END)

    return graph


def compile_conversation_graph(
    session: AsyncSession | None = None,
    thread_id: str | None = None,
) -> object:
    """Compile the conversation graph with HITL interrupt.

    Constitution: Safety First - interrupt_before at approval_gate
    ensures human approval before any deployment.

    Args:
        session: Database session
        thread_id: Optional thread ID for checkpointing

    Returns:
        Compiled graph with checkpointing and HITL interrupts
    """
    # Use PostgresCheckpointer when session is provided so state survives restarts
    if session is not None:
        from src.storage.checkpoints import PostgresCheckpointer

        checkpointer = PostgresCheckpointer(session)
    else:
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
    session: AsyncSession | None = None,
    thread_id: str | None = None,
    existing_state: ConversationState | None = None,
) -> ConversationState:
    """Execute the conversation workflow.

    Starts a trace session for correlation across all operations.

    Args:
        user_message: User's message
        session: Database session
        thread_id: Thread ID for checkpointing
        existing_state: Optional existing state to continue

    Returns:
        Updated conversation state
    """
    from langchain_core.messages import HumanMessage

    from src.tracing.context import get_session_id, session_context

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

    # Run with MLflow tracking and session context (inherit parent session if one exists)
    import mlflow

    with (
        session_context(get_session_id()) as session_id,
        start_experiment_run("conversation_workflow"),
    ):
        mlflow.update_current_trace(
            tags={
                "workflow": "conversation",
                **({"mlflow.trace.session": session_id} if session_id else {}),
            }
        )
        mlflow.set_tag("workflow", "conversation")
        mlflow.set_tag("thread_id", thread_id or state.conversation_id)
        mlflow.set_tag("session.id", session_id)

        try:
            # Execute the graph
            config = {"configurable": {"thread_id": thread_id or state.conversation_id}}
            final_state = await compiled.ainvoke(state, config=config)  # type: ignore[attr-defined]

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


@trace_with_uri(name="workflow.resume_after_approval", span_type="CHAIN")
async def resume_after_approval(
    thread_id: str,
    approved: bool,
    approved_by: str = "user",
    rejection_reason: str | None = None,
    session: AsyncSession | None = None,
) -> ConversationState:
    """Resume conversation workflow after HITL approval decision.

    Restores the trace session from the original workflow.

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
    from src.tracing.context import get_session_id, session_context

    # Compile graph with same checkpointer
    compiled = compile_conversation_graph(session=session, thread_id=thread_id)
    config = {"configurable": {"thread_id": thread_id}}

    # Get current state
    state_snapshot = compiled.get_state(config)  # type: ignore[attr-defined]
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
        current_state.approved_items.extend([a.id for a in current_state.pending_approvals])
    else:
        current_state.status = ConversationStatus.REJECTED
        current_state.rejected_items.extend([a.id for a in current_state.pending_approvals])

    # Update the state in the graph
    compiled.update_state(config, current_state.model_dump())  # type: ignore[attr-defined]

    # Resume execution with session context (inherit parent session if one exists)
    import mlflow

    with session_context(get_session_id()) as session_id:
        with start_experiment_run("conversation_workflow_resume"):
            mlflow.set_tag("workflow", "conversation_resume")
            mlflow.set_tag("thread_id", thread_id)
            mlflow.set_tag("session.id", session_id)
            mlflow.set_tag("approval.decision", "approved" if approved else "rejected")

            final_state = await compiled.ainvoke(None, config=config)  # type: ignore[attr-defined]

            if isinstance(final_state, dict):
                return current_state.model_copy(update=cast("dict[str, Any]", final_state))
            return cast("ConversationState", final_state)
