"""Unit tests for conversation workflow nodes (src/graph/nodes/conversation.py).

All agent invocations and DAL calls are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import ConversationState, ConversationStatus


def _make_state(**overrides) -> MagicMock:
    """Create a mock ConversationState."""
    state = MagicMock(spec=ConversationState)
    state.run_id = "run-1"
    state.conversation_id = "conv-1"
    state.messages = []
    state.pending_approvals = []
    state.approved_items = []
    state.rejected_items = []
    state.status = ConversationStatus.ACTIVE
    state.errors = []
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


class TestArchitectProposeNode:
    async def test_calls_architect_agent(self):
        from src.graph.nodes.conversation import architect_propose_node

        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={"messages": ["proposal"]})
        mock_agent.role = MagicMock()
        mock_agent.role.value = "architect"

        mock_metrics = MagicMock()

        with (
            patch("src.agents.ArchitectAgent", return_value=mock_agent),
            patch("src.api.metrics.get_metrics_collector", return_value=mock_metrics),
        ):
            state = _make_state()
            result = await architect_propose_node(state)
            assert result == {"messages": ["proposal"]}
            mock_agent.invoke.assert_called_once()

    async def test_passes_session(self):
        from src.graph.nodes.conversation import architect_propose_node

        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={})
        mock_agent.role = MagicMock()
        mock_agent.role.value = "architect"

        mock_session = AsyncMock()

        with (
            patch("src.agents.ArchitectAgent", return_value=mock_agent),
            patch("src.api.metrics.get_metrics_collector", return_value=MagicMock()),
        ):
            await architect_propose_node(_make_state(), session=mock_session)
            mock_agent.invoke.assert_called_once_with(
                mock_agent.invoke.call_args[0][0], session=mock_session
            )


class TestArchitectRefineNode:
    async def test_refine_calls_agent(self):
        from src.graph.nodes.conversation import architect_refine_node

        mock_agent = MagicMock()
        mock_agent.refine_proposal = AsyncMock(return_value={"refined": True})

        mock_session = AsyncMock()

        with patch("src.agents.ArchitectAgent", return_value=mock_agent):
            result = await architect_refine_node(
                _make_state(), feedback="looks good", proposal_id="p-1", session=mock_session
            )
            assert result == {"refined": True}

    async def test_refine_raises_without_session(self):
        from src.graph.nodes.conversation import architect_refine_node

        with (
            patch("src.agents.ArchitectAgent"),
            pytest.raises(ValueError, match="Session is required"),
        ):
            await architect_refine_node(
                _make_state(), feedback="test", proposal_id="p-1", session=None
            )


class TestApprovalGateNode:
    async def test_no_pending_approvals(self):
        from src.graph.nodes.conversation import approval_gate_node

        state = _make_state(pending_approvals=[])
        result = await approval_gate_node(state)
        assert result["status"] == ConversationStatus.ACTIVE

    async def test_with_pending_approvals(self):
        from src.graph.nodes.conversation import approval_gate_node

        approval = MagicMock()
        state = _make_state(pending_approvals=[approval])
        result = await approval_gate_node(state)
        assert result["status"] == ConversationStatus.WAITING_APPROVAL
        assert result["current_agent"] is None


class TestProcessApprovalNode:
    async def test_approve(self):
        from src.graph.nodes.conversation import process_approval_node

        approval = MagicMock()
        approval.id = "a-1"
        state = _make_state(pending_approvals=[approval], approved_items=[], rejected_items=[])

        with patch("src.dal.ProposalRepository"):
            result = await process_approval_node(state, approved=True)
            assert result["status"] == ConversationStatus.APPROVED
            assert "a-1" in result["approved_items"]
            assert result["pending_approvals"] == []

    async def test_reject(self):
        from src.graph.nodes.conversation import process_approval_node

        approval = MagicMock()
        approval.id = "a-1"
        state = _make_state(pending_approvals=[approval], approved_items=[], rejected_items=[])

        with patch("src.dal.ProposalRepository"):
            result = await process_approval_node(
                state, approved=False, rejection_reason="Not needed"
            )
            assert result["status"] == ConversationStatus.REJECTED
            assert "a-1" in result["rejected_items"]

    async def test_no_pending(self):
        from src.graph.nodes.conversation import process_approval_node

        state = _make_state(pending_approvals=[])
        result = await process_approval_node(state, approved=True)
        assert result["status"] == ConversationStatus.ACTIVE

    async def test_approve_with_session_persists(self):
        from src.graph.nodes.conversation import process_approval_node

        approval = MagicMock()
        approval.id = "a-1"
        state = _make_state(pending_approvals=[approval], approved_items=[], rejected_items=[])
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.approve = AsyncMock()

        with patch("src.dal.ProposalRepository", return_value=mock_repo):
            await process_approval_node(
                state, approved=True, approved_by="admin", session=mock_session
            )
            mock_repo.approve.assert_called_once_with("a-1", "admin")


class TestDeveloperDeployNode:
    async def test_deploy_calls_developer(self):
        from src.graph.nodes.conversation import developer_deploy_node

        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={"deployed": True})

        with patch("src.agents.DeveloperAgent", return_value=mock_agent):
            result = await developer_deploy_node(_make_state(), proposal_id="p-1")
            assert result == {"deployed": True}


class TestDeveloperRollbackNode:
    async def test_rollback_success(self):
        from src.graph.nodes.conversation import developer_rollback_node

        mock_agent = MagicMock()
        mock_agent.rollback_automation = AsyncMock(
            return_value={"note": "Rolled back successfully"}
        )
        mock_session = AsyncMock()

        with patch("src.agents.DeveloperAgent", return_value=mock_agent):
            result = await developer_rollback_node(
                _make_state(), proposal_id="p-1", session=mock_session
            )
            assert result["status"] == ConversationStatus.COMPLETED

    async def test_rollback_error(self):
        from src.graph.nodes.conversation import developer_rollback_node

        mock_agent = MagicMock()
        mock_agent.rollback_automation = AsyncMock(return_value={"error": "Not found"})
        mock_session = AsyncMock()

        with patch("src.agents.DeveloperAgent", return_value=mock_agent):
            result = await developer_rollback_node(
                _make_state(), proposal_id="p-1", session=mock_session
            )
            assert "Rollback failed" in result["messages"][0].content

    async def test_rollback_requires_session(self):
        from src.graph.nodes.conversation import developer_rollback_node

        with (
            patch("src.agents.DeveloperAgent"),
            pytest.raises(ValueError, match="Session is required"),
        ):
            await developer_rollback_node(_make_state(), proposal_id="p-1", session=None)


class TestConversationErrorNode:
    async def test_error_node(self):
        from src.graph.nodes.conversation import conversation_error_node

        error = ValueError("Something went wrong")
        result = await conversation_error_node(_make_state(), error=error)
        assert result["status"] == ConversationStatus.FAILED
        assert "ValueError" in result["messages"][0].content
