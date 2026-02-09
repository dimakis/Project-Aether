"""Conversation workflow nodes for Architect/Developer agents.

These nodes handle user conversations, proposal generation, HITL approval,
and automation deployment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage

from src.graph.state import ConversationState, ConversationStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def architect_propose_node(
    state: ConversationState,
    session: AsyncSession | None = None,
) -> dict[str, object]:
    """Architect agent processes user message and proposes automation.

    Args:
        state: Current conversation state
        session: Database session

    Returns:
        State updates with response and any proposals
    """
    from src.agents import ArchitectAgent
    from src.api.metrics import get_metrics_collector

    agent = ArchitectAgent()
    metrics = get_metrics_collector()
    metrics.record_agent_invocation(agent.role.value)
    return await agent.invoke(state, session=session)


async def architect_refine_node(
    state: ConversationState,
    feedback: str,
    proposal_id: str,
    session: AsyncSession | None = None,
) -> dict[str, object]:
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
) -> dict[str, object]:
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
    session: AsyncSession | None = None,
) -> dict[str, object]:
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

    updates: dict[str, object] = {}
    approved_ids: list[str] = []
    rejected_ids: list[str] = []

    for approval in state.pending_approvals:
        if approved:
            approval.approved = True
            approval.approved_by = approved_by
            approval.approved_at = datetime.now(UTC)
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
    session: AsyncSession | None = None,
) -> dict[str, object]:
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
    session: AsyncSession | None = None,
) -> dict[str, object]:
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
) -> dict[str, object]:
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
