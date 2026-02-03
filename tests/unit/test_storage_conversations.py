"""Unit tests for conversation/message storage.

T091: Tests for ConversationRepository and MessageRepository.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.storage.entities import ConversationStatus


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestConversationRepository:
    """Test ConversationRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, mock_session):
        """Test creating a new conversation."""
        from src.dal.conversations import ConversationRepository

        repo = ConversationRepository(mock_session)

        conversation = await repo.create(
            agent_id="test-agent-id",
            user_id="test-user",
            title="Test Conversation",
            context={"key": "value"},
        )

        assert conversation is not None
        assert conversation.agent_id == "test-agent-id"
        assert conversation.user_id == "test-user"
        assert conversation.title == "Test Conversation"
        assert conversation.context == {"key": "value"}
        assert conversation.status == ConversationStatus.ACTIVE
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_session):
        """Test retrieving conversation by ID."""
        from src.dal.conversations import ConversationRepository
        from src.storage.entities import Conversation

        # Mock conversation
        mock_conv = MagicMock(spec=Conversation)
        mock_conv.id = "test-id"
        mock_conv.status = ConversationStatus.ACTIVE

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        result = await repo.get_by_id("test-id", include_messages=False)

        assert result is not None
        assert result.id == "test-id"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session):
        """Test retrieving non-existent conversation."""
        from src.dal.conversations import ConversationRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        result = await repo.get_by_id("non-existent", include_messages=False)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self, mock_session):
        """Test updating conversation status."""
        from src.dal.conversations import ConversationRepository
        from src.storage.entities import Conversation

        mock_conv = MagicMock(spec=Conversation)
        mock_conv.id = "test-id"
        mock_conv.status = ConversationStatus.ACTIVE

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        result = await repo.update_status("test-id", ConversationStatus.COMPLETED)

        assert result is not None
        assert mock_conv.status == ConversationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_count(self, mock_session):
        """Test counting conversations."""
        from src.dal.conversations import ConversationRepository

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        count = await repo.count()

        assert count == 5


class TestMessageRepository:
    """Test MessageRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_message(self, mock_session):
        """Test creating a new message."""
        from src.dal.conversations import MessageRepository

        repo = MessageRepository(mock_session)

        message = await repo.create(
            conversation_id="conv-id",
            role="user",
            content="Hello, Architect!",
            tokens_used=10,
        )

        assert message is not None
        assert message.conversation_id == "conv-id"
        assert message.role == "user"
        assert message.content == "Hello, Architect!"
        assert message.tokens_used == 10
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_session):
        """Test retrieving message by ID."""
        from src.dal.conversations import MessageRepository
        from src.storage.entities import Message

        mock_msg = MagicMock(spec=Message)
        mock_msg.id = "msg-id"
        mock_msg.content = "Test"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_msg
        mock_session.execute.return_value = mock_result

        repo = MessageRepository(mock_session)
        result = await repo.get_by_id("msg-id")

        assert result is not None
        assert result.id == "msg-id"

    @pytest.mark.asyncio
    async def test_count_by_conversation(self, mock_session):
        """Test counting messages in conversation."""
        from src.dal.conversations import MessageRepository

        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        repo = MessageRepository(mock_session)
        count = await repo.count_by_conversation("conv-id")

        assert count == 10

    @pytest.mark.asyncio
    async def test_get_token_usage(self, mock_session):
        """Test getting total token usage."""
        from src.dal.conversations import MessageRepository

        mock_result = MagicMock()
        mock_result.scalar.return_value = 500
        mock_session.execute.return_value = mock_result

        repo = MessageRepository(mock_session)
        usage = await repo.get_token_usage("conv-id")

        assert usage == 500


class TestProposalRepository:
    """Test ProposalRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_proposal(self, mock_session):
        """Test creating a proposal."""
        from src.dal.conversations import ProposalRepository

        repo = ProposalRepository(mock_session)

        proposal = await repo.create(
            name="Test Automation",
            trigger={"platform": "state", "entity_id": "light.test"},
            actions={"service": "light.turn_on"},
            description="Test description",
            mode="single",
        )

        assert proposal is not None
        assert proposal.name == "Test Automation"
        assert proposal.trigger["platform"] == "state"
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_proposal(self, mock_session):
        """Test approving a proposal."""
        from src.dal.conversations import ProposalRepository
        from src.storage.entities import AutomationProposal, ProposalStatus

        mock_proposal = MagicMock(spec=AutomationProposal)
        mock_proposal.id = "prop-id"
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal.approve = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        repo = ProposalRepository(mock_session)
        result = await repo.approve("prop-id", "test-user")

        assert result is not None
        mock_proposal.approve.assert_called_once_with("test-user")

    @pytest.mark.asyncio
    async def test_reject_proposal(self, mock_session):
        """Test rejecting a proposal."""
        from src.dal.conversations import ProposalRepository
        from src.storage.entities import AutomationProposal, ProposalStatus

        mock_proposal = MagicMock(spec=AutomationProposal)
        mock_proposal.id = "prop-id"
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal.reject = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        repo = ProposalRepository(mock_session)
        result = await repo.reject("prop-id", "Not what I wanted")

        assert result is not None
        mock_proposal.reject.assert_called_once_with("Not what I wanted")

    @pytest.mark.asyncio
    async def test_deploy_proposal(self, mock_session):
        """Test deploying a proposal."""
        from src.dal.conversations import ProposalRepository
        from src.storage.entities import AutomationProposal, ProposalStatus

        mock_proposal = MagicMock(spec=AutomationProposal)
        mock_proposal.id = "prop-id"
        mock_proposal.status = ProposalStatus.APPROVED
        mock_proposal.deploy = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        repo = ProposalRepository(mock_session)
        result = await repo.deploy("prop-id", "automation.test_123")

        assert result is not None
        mock_proposal.deploy.assert_called_once_with("automation.test_123")

    @pytest.mark.asyncio
    async def test_rollback_proposal(self, mock_session):
        """Test rolling back a proposal."""
        from src.dal.conversations import ProposalRepository
        from src.storage.entities import AutomationProposal, ProposalStatus

        mock_proposal = MagicMock(spec=AutomationProposal)
        mock_proposal.id = "prop-id"
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal.rollback = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        repo = ProposalRepository(mock_session)
        result = await repo.rollback("prop-id")

        assert result is not None
        mock_proposal.rollback.assert_called_once()
