"""Integration tests for HITL interrupt behavior.

T097: LangGraph interrupt_before behavior tests.
"""

import pytest

from src.graph.state import (
    ApprovalDecision,
    ApprovalState,
    ConversationState,
    ConversationStatus,
    HITLApproval,
)


class TestHITLApprovalState:
    """Test HITL approval state management."""

    def test_approval_state_pending_by_default(self):
        """Test that approval state starts as pending."""
        state = ApprovalState(
            proposal_id="test-id",
            proposal_name="Test Automation",
            proposal_yaml="alias: Test",
        )

        assert state.is_pending
        assert not state.is_approved
        assert not state.is_rejected
        assert state.user_decision == ApprovalDecision.PENDING

    def test_approval_state_approve(self):
        """Test approving via ApprovalState."""
        state = ApprovalState(
            proposal_id="test-id",
            proposal_name="Test Automation",
            proposal_yaml="alias: Test",
        )

        state.approve("test_user", "LGTM!")

        assert state.is_approved
        assert state.decided_by == "test_user"
        assert state.comment == "LGTM!"
        assert state.decided_at is not None

    def test_approval_state_reject(self):
        """Test rejecting via ApprovalState."""
        state = ApprovalState(
            proposal_id="test-id",
            proposal_name="Test Automation",
            proposal_yaml="alias: Test",
        )

        state.reject("test_user", "Needs changes")

        assert state.is_rejected
        assert state.decided_by == "test_user"
        assert state.rejection_reason == "Needs changes"


class TestHITLInterruptBehavior:
    """Test LangGraph interrupt_before behavior."""

    @pytest.mark.asyncio
    async def test_graph_compiles_with_interrupt(self):
        """Test that graph compiles with interrupt_before."""
        from src.graph.workflows import compile_conversation_graph

        # This should not raise
        compiled = compile_conversation_graph()
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_conversation_state_tracks_pending_approvals(self):
        """Test that conversation state tracks pending approvals."""
        approval = HITLApproval(
            request_type="automation",
            description="Turn on lights",
            yaml_content="alias: Turn on lights",
        )

        state = ConversationState(
            pending_approvals=[approval],
        )

        assert len(state.pending_approvals) == 1
        assert state.pending_approvals[0].request_type == "automation"

    @pytest.mark.asyncio
    async def test_approval_gate_sets_waiting_status(self):
        """Test that approval gate sets waiting_approval status."""
        from src.graph.nodes import approval_gate_node

        approval = HITLApproval(
            id="test-approval",
            request_type="automation",
            description="Test",
            yaml_content="alias: Test",
        )

        state = ConversationState(
            pending_approvals=[approval],
        )

        result = await approval_gate_node(state)

        assert result["status"] == ConversationStatus.WAITING_APPROVAL

    @pytest.mark.asyncio
    async def test_approval_gate_continues_without_pending(self):
        """Test approval gate continues if no pending approvals."""
        from src.graph.nodes import approval_gate_node

        state = ConversationState(
            pending_approvals=[],
        )

        result = await approval_gate_node(state)

        assert result["status"] == ConversationStatus.ACTIVE


class TestApprovalProcessing:
    """Test approval processing logic."""

    @pytest.mark.asyncio
    async def test_process_approval_approved(self):
        """Test processing an approved proposal."""
        from src.graph.nodes import process_approval_node

        approval = HITLApproval(
            id="test-approval",
            request_type="automation",
            description="Test",
            yaml_content="alias: Test",
        )

        state = ConversationState(
            status=ConversationStatus.APPROVED,
            pending_approvals=[approval],
        )

        # Without session, the database operations are skipped
        result = await process_approval_node(
            state,
            approved=True,
            approved_by="test_user",
        )

        assert result["status"] == ConversationStatus.APPROVED
        assert "test-approval" in result["approved_items"]

    @pytest.mark.asyncio
    async def test_process_approval_rejected(self):
        """Test processing a rejected proposal."""
        from src.graph.nodes import process_approval_node

        approval = HITLApproval(
            id="test-approval",
            request_type="automation",
            description="Test",
            yaml_content="alias: Test",
        )

        state = ConversationState(
            status=ConversationStatus.REJECTED,
            pending_approvals=[approval],
        )

        result = await process_approval_node(
            state,
            approved=False,
            rejection_reason="Not needed",
        )

        assert result["status"] == ConversationStatus.REJECTED
        assert "test-approval" in result["rejected_items"]
