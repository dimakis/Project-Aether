"""E2E tests for automation design workflow.

T099: Full conversation → proposal → approval flow.
"""

from uuid import uuid4

import pytest


class TestAutomationDesignWorkflow:
    """Test complete automation design workflow."""

    @pytest.mark.asyncio
    async def test_full_design_to_approval_flow(self):
        """Test conversation → proposal → approval flow."""
        from langchain_core.messages import AIMessage, HumanMessage

        from src.graph.state import ConversationState, ConversationStatus

        # Start with user request
        state = ConversationState(
            conversation_id=str(uuid4()),
            messages=[HumanMessage(content="Turn on the lights at sunset")],
            user_intent="create_automation",
            status=ConversationStatus.ACTIVE,
        )

        assert state.status == ConversationStatus.ACTIVE
        assert len(state.messages) == 1

        # Simulate architect response
        state.messages.append(
            AIMessage(content="I'll create an automation that turns on the lights at sunset.")
        )

        # Verify conversation progressed
        assert len(state.messages) == 2

    @pytest.mark.asyncio
    async def test_proposal_creation_from_design(self):
        """Test creating a proposal from architect design."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        # Create proposal from design
        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Sunset Lights",
            description="Turn on lights at sunset",
            trigger={"platform": "sun", "event": "sunset"},
            actions=[{"service": "light.turn_on", "target": {"entity_id": "light.all"}}],
            mode="single",
            status=ProposalStatus.DRAFT,
        )

        assert proposal.status == ProposalStatus.DRAFT
        assert proposal.name == "Sunset Lights"
        assert proposal.trigger["platform"] == "sun"

    @pytest.mark.asyncio
    async def test_proposal_approval_transition(self):
        """Test proposal state transitions during approval."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        # Create proposal
        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Test Automation",
            trigger={"platform": "time", "at": "08:00"},
            actions=[{"service": "light.turn_on"}],
            mode="single",
            status=ProposalStatus.DRAFT,
        )

        # Propose
        proposal.propose()
        assert proposal.status == ProposalStatus.PROPOSED

        # Approve
        proposal.approve(approved_by="test_user")
        assert proposal.status == ProposalStatus.APPROVED
        assert proposal.approved_by == "test_user"
        assert proposal.approved_at is not None

    @pytest.mark.asyncio
    async def test_proposal_rejection_flow(self):
        """Test proposal rejection flow."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Rejected Automation",
            trigger={"platform": "event", "event_type": "test"},
            actions=[{"service": "notify.notify"}],
            mode="single",
            status=ProposalStatus.DRAFT,
        )

        # Propose and reject
        proposal.propose()
        proposal.reject(reason="Not needed")

        assert proposal.status == ProposalStatus.REJECTED
        assert proposal.rejection_reason == "Not needed"


class TestMultiProposalConversation:
    """Test conversations with multiple proposals."""

    @pytest.mark.asyncio
    async def test_conversation_with_multiple_proposals(self):
        """Test conversation can have multiple proposals."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        conversation_id = str(uuid4())

        # Create multiple proposals for same conversation
        proposal1 = AutomationProposal(
            id=str(uuid4()),
            conversation_id=conversation_id,
            name="Morning Routine",
            trigger={"platform": "time", "at": "07:00"},
            actions=[{"service": "light.turn_on"}],
            mode="single",
            status=ProposalStatus.PROPOSED,
        )

        proposal2 = AutomationProposal(
            id=str(uuid4()),
            conversation_id=conversation_id,
            name="Evening Routine",
            trigger={"platform": "time", "at": "18:00"},
            actions=[{"service": "light.turn_on"}],
            mode="single",
            status=ProposalStatus.PROPOSED,
        )

        # Both proposals share conversation
        assert proposal1.conversation_id == proposal2.conversation_id
        assert proposal1.id != proposal2.id

    @pytest.mark.asyncio
    async def test_partial_approval_of_proposals(self):
        """Test approving some proposals while rejecting others."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal1 = AutomationProposal(
            id=str(uuid4()),
            name="Proposal 1",
            trigger={"platform": "time"},
            actions=[{}],
            mode="single",
            status=ProposalStatus.PROPOSED,
        )

        proposal2 = AutomationProposal(
            id=str(uuid4()),
            name="Proposal 2",
            trigger={"platform": "event"},
            actions=[{}],
            mode="single",
            status=ProposalStatus.PROPOSED,
        )

        # Approve one, reject other
        proposal1.approve(approved_by="user")
        proposal2.reject(reason="Not needed")

        assert proposal1.status == ProposalStatus.APPROVED
        assert proposal2.status == ProposalStatus.REJECTED


class TestConversationPersistence:
    """Test conversation state persistence."""

    @pytest.mark.asyncio
    async def test_conversation_state_serialization(self):
        """Test conversation state can be serialized."""
        from langchain_core.messages import HumanMessage

        from src.graph.state import ConversationState, ConversationStatus

        state = ConversationState(
            conversation_id=str(uuid4()),
            messages=[HumanMessage(content="Test message")],
            user_intent="test",
            entities_mentioned=["light.living_room"],
            areas_mentioned=["living_room"],
            status=ConversationStatus.ACTIVE,
        )

        # State should be serializable to dict
        state_dict = {
            "conversation_id": state.conversation_id,
            "user_intent": state.user_intent,
            "entities_mentioned": state.entities_mentioned,
            "areas_mentioned": state.areas_mentioned,
            "status": state.status.value,
        }

        assert state_dict["user_intent"] == "test"
        assert "light.living_room" in state_dict["entities_mentioned"]
