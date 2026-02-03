"""Integration tests for conversation workflow.

T096: Full conversation flow with mocks.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.state import ConversationState, ConversationStatus


class TestConversationWorkflow:
    """Test full conversation workflow."""

    @pytest.fixture
    def mock_llm_response_with_proposal(self):
        """Mock LLM response containing a proposal."""
        content = """I understand you want to automate your lights.

Here's my proposal:

```json
{
  "proposal": {
    "name": "Turn on lights at sunset",
    "description": "Automatically turn on living room lights when the sun sets",
    "trigger": [{"platform": "sun", "event": "sunset"}],
    "conditions": [],
    "actions": [{"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}],
    "mode": "single"
  }
}
```

Would you like me to adjust anything?"""
        response = MagicMock()
        response.content = content
        response.response_metadata = {"token_usage": {"total_tokens": 150}}
        return response

    @pytest.fixture
    def mock_llm_response_clarifying(self):
        """Mock LLM response asking for clarification."""
        content = "I'd be happy to help you automate your lights. Could you tell me more about when you want them to turn on? At a specific time, when you arrive home, or based on another trigger?"
        response = MagicMock()
        response.content = content
        response.response_metadata = {"token_usage": {"total_tokens": 50}}
        return response

    @pytest.mark.asyncio
    async def test_conversation_starts_with_user_message(self, mock_llm_response_clarifying):
        """Test that conversation workflow starts correctly."""
        from src.agents.architect import ArchitectWorkflow

        with patch("src.agents.architect.ChatOpenAI") as MockLLM:
            mock_llm = MockLLM.return_value
            mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response_clarifying)

            workflow = ArchitectWorkflow()
            workflow.agent._llm = mock_llm

            state = await workflow.start_conversation(
                user_message="I want to automate my lights"
            )

            assert state is not None
            assert len(state.messages) >= 1
            # First message should be the assistant response
            assert any(
                hasattr(m, "type") and m.type == "ai"
                for m in state.messages
            )

    @pytest.mark.asyncio
    async def test_conversation_generates_proposal(self, mock_llm_response_with_proposal):
        """Test that conversation can generate proposals."""
        from src.agents.architect import ArchitectWorkflow

        with patch("src.agents.architect.ChatOpenAI") as MockLLM:
            mock_llm = MockLLM.return_value
            mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response_with_proposal)

            workflow = ArchitectWorkflow()
            workflow.agent._llm = mock_llm

            state = await workflow.start_conversation(
                user_message="Turn on lights at sunset"
            )

            # Check workflow processed the request and LLM response is in messages
            assert state is not None
            assert len(state.messages) >= 1
            # The LLM response should contain proposal keywords
            ai_messages = [m for m in state.messages if hasattr(m, "type") and m.type == "ai"]
            assert any("proposal" in m.content.lower() for m in ai_messages)

    @pytest.mark.asyncio
    async def test_conversation_continues_with_context(self, mock_llm_response_clarifying):
        """Test that conversation maintains context."""
        from src.agents.architect import ArchitectWorkflow

        with patch("src.agents.architect.ChatOpenAI") as MockLLM:
            mock_llm = MockLLM.return_value
            mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response_clarifying)

            workflow = ArchitectWorkflow()
            workflow.agent._llm = mock_llm

            # Start conversation
            state = await workflow.start_conversation(
                user_message="I want to automate something"
            )

            # Continue conversation
            state = await workflow.continue_conversation(
                state=state,
                user_message="Specifically, I want my lights to turn on at sunset"
            )

            # Verify invoke was called twice
            assert mock_llm.ainvoke.call_count >= 2


class TestConversationGraph:
    """Test conversation graph building."""

    @pytest.mark.asyncio
    async def test_graph_builds_without_error(self):
        """Test that conversation graph builds correctly."""
        from src.graph.workflows import build_conversation_graph

        graph = build_conversation_graph()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_graph_compiles_with_hitl_interrupt(self):
        """Test that graph compiles with HITL interrupt."""
        from src.graph.workflows import compile_conversation_graph

        compiled = compile_conversation_graph()
        assert compiled is not None


class TestProposalWorkflow:
    """Test proposal state transitions."""

    @pytest.mark.asyncio
    async def test_proposal_transitions(self):
        """Test proposal state machine transitions."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id="test-id",
            name="Test",
            trigger={"platform": "time", "at": "08:00"},
            actions={"service": "light.turn_on"},
            mode="single",
            status=ProposalStatus.DRAFT,
        )

        # Draft -> Proposed
        proposal.propose()
        assert proposal.status == ProposalStatus.PROPOSED

        # Proposed -> Approved
        proposal.approve("test_user")
        assert proposal.status == ProposalStatus.APPROVED

        # Approved -> Deployed
        proposal.deploy("automation.test_123")
        assert proposal.status == ProposalStatus.DEPLOYED
        assert proposal.ha_automation_id == "automation.test_123"

        # Deployed -> Rolled Back
        proposal.rollback()
        assert proposal.status == ProposalStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_proposal_rejection_flow(self):
        """Test proposal rejection workflow."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id="test-id",
            name="Test",
            trigger={"platform": "time", "at": "08:00"},
            actions={"service": "light.turn_on"},
            mode="single",
            status=ProposalStatus.DRAFT,
        )

        proposal.propose()
        proposal.reject("Not what I wanted")

        assert proposal.status == ProposalStatus.REJECTED
        assert proposal.rejection_reason == "Not what I wanted"

        # Can be re-proposed after rejection
        proposal.status = ProposalStatus.PROPOSED  # Reset for test
        assert proposal.can_transition_to(ProposalStatus.APPROVED)
