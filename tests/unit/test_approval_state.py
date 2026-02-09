"""Unit tests for HITL approval state machine.

T094: Tests for ApprovalState and ProposalStatus transitions.
"""

from datetime import UTC, datetime

import pytest


class TestProposalStatusTransitions:
    """Test AutomationProposal state machine transitions."""

    @pytest.fixture
    def proposal(self):
        """Create a proposal for testing."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id="test-id",
            name="Test Automation",
            trigger={"platform": "time", "at": "08:00"},
            actions={"service": "light.turn_on"},
            mode="single",
            status=ProposalStatus.DRAFT,
        )
        return proposal

    def test_draft_to_proposed(self, proposal):
        """Test transition from draft to proposed."""
        from src.storage.entities import ProposalStatus

        assert proposal.status == ProposalStatus.DRAFT
        proposal.propose()
        assert proposal.status == ProposalStatus.PROPOSED
        assert proposal.proposed_at is not None

    def test_proposed_to_approved(self, proposal):
        """Test transition from proposed to approved."""
        from src.storage.entities import ProposalStatus

        proposal.propose()
        proposal.approve("test_user")
        assert proposal.status == ProposalStatus.APPROVED
        assert proposal.approved_at is not None
        assert proposal.approved_by == "test_user"

    def test_proposed_to_rejected(self, proposal):
        """Test transition from proposed to rejected."""
        from src.storage.entities import ProposalStatus

        proposal.propose()
        proposal.reject("Not what I wanted")
        assert proposal.status == ProposalStatus.REJECTED
        assert proposal.rejection_reason == "Not what I wanted"

    def test_approved_to_deployed(self, proposal):
        """Test transition from approved to deployed."""
        from src.storage.entities import ProposalStatus

        proposal.propose()
        proposal.approve("test_user")
        proposal.deploy("automation.test_123")
        assert proposal.status == ProposalStatus.DEPLOYED
        assert proposal.deployed_at is not None
        assert proposal.ha_automation_id == "automation.test_123"

    def test_deployed_to_rolled_back(self, proposal):
        """Test transition from deployed to rolled_back."""
        from src.storage.entities import ProposalStatus

        proposal.propose()
        proposal.approve("test_user")
        proposal.deploy("automation.test_123")
        proposal.rollback()
        assert proposal.status == ProposalStatus.ROLLED_BACK
        assert proposal.rolled_back_at is not None

    def test_invalid_transition_draft_to_approved(self, proposal):
        """Test that invalid transitions raise errors."""
        # Cannot go directly from draft to approved
        with pytest.raises(ValueError, match="Cannot approve"):
            proposal.approve("test_user")

    def test_invalid_transition_draft_to_deployed(self, proposal):
        """Test that invalid transitions raise errors."""
        # Cannot go directly from draft to deployed
        with pytest.raises(ValueError, match="Cannot deploy"):
            proposal.deploy("automation.test")

    def test_invalid_transition_proposed_to_deployed(self, proposal):
        """Test HITL safety - cannot skip approval."""

        proposal.propose()
        # Cannot go directly from proposed to deployed (HITL safety)
        with pytest.raises(ValueError, match="Cannot deploy"):
            proposal.deploy("automation.test")

    def test_can_transition_to(self, proposal):
        """Test can_transition_to helper."""
        from src.storage.entities import ProposalStatus

        # Draft can only go to proposed
        assert proposal.can_transition_to(ProposalStatus.PROPOSED)
        assert not proposal.can_transition_to(ProposalStatus.APPROVED)
        assert not proposal.can_transition_to(ProposalStatus.DEPLOYED)

        # Proposed can go to approved or rejected
        proposal.propose()
        assert proposal.can_transition_to(ProposalStatus.APPROVED)
        assert proposal.can_transition_to(ProposalStatus.REJECTED)
        assert not proposal.can_transition_to(ProposalStatus.DEPLOYED)

    def test_archived_is_terminal(self, proposal):
        """Test that archived is a terminal state."""
        from src.storage.entities import ProposalStatus

        proposal.propose()
        proposal.reject("Testing")
        proposal.archive()
        assert proposal.status == ProposalStatus.ARCHIVED

        # Cannot transition from archived
        assert not proposal.can_transition_to(ProposalStatus.PROPOSED)
        assert not proposal.can_transition_to(ProposalStatus.APPROVED)

    def test_to_ha_yaml_dict(self, proposal):
        """Test YAML dict generation."""
        yaml_dict = proposal.to_ha_yaml_dict()

        assert yaml_dict["alias"] == "Test Automation"
        assert "trigger" in yaml_dict
        assert "action" in yaml_dict
        assert yaml_dict["mode"] == "single"


class TestApprovalState:
    """Test ApprovalState model."""

    def test_approval_state_creation(self):
        """Test creating an approval state."""
        from src.graph.state import ApprovalDecision, ApprovalState

        state = ApprovalState(
            proposal_id="test-id",
            proposal_name="Test Automation",
            proposal_yaml="alias: Test",
        )

        assert state.proposal_id == "test-id"
        assert state.user_decision == ApprovalDecision.PENDING
        assert state.is_pending

    def test_approval_state_approve(self):
        """Test approving via ApprovalState."""
        from src.graph.state import ApprovalDecision, ApprovalState

        state = ApprovalState(
            proposal_id="test-id",
            proposal_name="Test Automation",
            proposal_yaml="alias: Test",
        )

        state.approve("test_user", "Looks good!")

        assert state.user_decision == ApprovalDecision.APPROVED
        assert state.decided_by == "test_user"
        assert state.decided_at is not None
        assert state.comment == "Looks good!"
        assert state.is_approved
        assert not state.is_pending

    def test_approval_state_reject(self):
        """Test rejecting via ApprovalState."""
        from src.graph.state import ApprovalDecision, ApprovalState

        state = ApprovalState(
            proposal_id="test-id",
            proposal_name="Test Automation",
            proposal_yaml="alias: Test",
        )

        state.reject("test_user", "Needs changes")

        assert state.user_decision == ApprovalDecision.REJECTED
        assert state.decided_by == "test_user"
        assert state.rejection_reason == "Needs changes"
        assert state.is_rejected
        assert not state.is_pending


class TestHITLApproval:
    """Test HITLApproval model."""

    def test_hitl_approval_creation(self):
        """Test creating HITL approval request."""
        from src.graph.state import HITLApproval

        approval = HITLApproval(
            request_type="automation",
            description="Turn on lights automation",
            yaml_content="alias: Turn on lights",
        )

        assert approval.id is not None
        assert approval.request_type == "automation"
        assert approval.approved is None  # Pending
        assert approval.created_at is not None

    def test_hitl_approval_approved(self):
        """Test approved HITL request."""
        from src.graph.state import HITLApproval

        approval = HITLApproval(
            request_type="automation",
            description="Test",
            yaml_content="alias: Test",
        )

        approval.approved = True
        approval.approved_by = "user"
        approval.approved_at = datetime.now(UTC)

        assert approval.approved is True
        assert approval.approved_by == "user"

    def test_hitl_approval_rejected(self):
        """Test rejected HITL request."""
        from src.graph.state import HITLApproval

        approval = HITLApproval(
            request_type="automation",
            description="Test",
            yaml_content="alias: Test",
        )

        approval.approved = False
        approval.rejection_reason = "Not needed"

        assert approval.approved is False
        assert approval.rejection_reason == "Not needed"
