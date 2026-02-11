"""Unit tests for Conversation DAL operations.

Tests ConversationRepository, MessageRepository, and ProposalRepository
CRUD operations with mocked database.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.dal.conversations import (
    ConversationRepository,
    MessageRepository,
    ProposalRepository,
)
from src.storage.entities import (
    ConversationStatus,
    ProposalStatus,
)


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def conversation_repo(mock_session):
    """Create ConversationRepository with mock session."""
    return ConversationRepository(mock_session)


@pytest.fixture
def message_repo(mock_session):
    """Create MessageRepository with mock session."""
    return MessageRepository(mock_session)


@pytest.fixture
def proposal_repo(mock_session):
    """Create ProposalRepository with mock session."""
    return ProposalRepository(mock_session)


# ─── ConversationRepository ────────────────────────────────────────────────────


class TestConversationRepositoryCreate:
    """Tests for ConversationRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_success(self, conversation_repo, mock_session):
        """Test creating a new conversation."""
        result = await conversation_repo.create(
            agent_id=str(uuid4()),
            user_id="user123",
            title="Test Conversation",
            context={"key": "value"},
        )

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()


class TestConversationRepositoryGetById:
    """Tests for ConversationRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, conversation_repo, mock_session):
        """Test getting conversation by ID when it exists."""
        conversation_id = str(uuid4())
        mock_conversation = MagicMock()
        mock_conversation.id = conversation_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.get_by_id(conversation_id)

        assert result == mock_conversation

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, conversation_repo, mock_session):
        """Test getting conversation by ID when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.get_by_id(str(uuid4()))

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_messages(self, conversation_repo, mock_session):
        """Test getting conversation with messages eagerly loaded."""
        conversation_id = str(uuid4())
        mock_conversation = MagicMock()
        mock_conversation.id = conversation_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.get_by_id(conversation_id, include_messages=True)

        assert result == mock_conversation


class TestConversationRepositoryListByUser:
    """Tests for ConversationRepository.list_by_user method."""

    @pytest.mark.asyncio
    async def test_list_by_user(self, conversation_repo, mock_session):
        """Test listing conversations for a user."""
        mock_conversations = [MagicMock() for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.list_by_user("user123")

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_by_user_with_status(self, conversation_repo, mock_session):
        """Test listing conversations filtered by status."""
        mock_conversations = [MagicMock() for _ in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.list_by_user("user123", status=ConversationStatus.ACTIVE)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_by_user_with_limit_offset(self, conversation_repo, mock_session):
        """Test listing conversations with limit and offset."""
        mock_conversations = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.list_by_user("user123", limit=10, offset=0)

        assert len(result) == 5


class TestConversationRepositoryListActive:
    """Tests for ConversationRepository.list_active method."""

    @pytest.mark.asyncio
    async def test_list_active(self, conversation_repo, mock_session):
        """Test listing active conversations."""
        mock_conversations = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_conversations
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.list_active(limit=50)

        assert len(result) == 5


class TestConversationRepositoryUpdateStatus:
    """Tests for ConversationRepository.update_status method."""

    @pytest.mark.asyncio
    async def test_update_status_success(self, conversation_repo, mock_session):
        """Test updating conversation status."""
        conversation_id = str(uuid4())
        mock_conversation = MagicMock()
        mock_conversation.id = conversation_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.update_status(
            conversation_id, ConversationStatus.COMPLETED
        )

        assert result == mock_conversation
        assert mock_conversation.status == ConversationStatus.COMPLETED
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, conversation_repo, mock_session):
        """Test updating status when conversation doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.update_status(str(uuid4()), ConversationStatus.COMPLETED)

        assert result is None


class TestConversationRepositoryUpdateContext:
    """Tests for ConversationRepository.update_context method."""

    @pytest.mark.asyncio
    async def test_update_context_replace(self, conversation_repo, mock_session):
        """Test replacing conversation context."""
        conversation_id = str(uuid4())
        mock_conversation = MagicMock()
        mock_conversation.id = conversation_id
        mock_conversation.context = {"old": "value"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_session.execute.return_value = mock_result

        new_context = {"new": "value"}
        result = await conversation_repo.update_context(conversation_id, new_context, merge=False)

        assert result == mock_conversation
        assert mock_conversation.context == new_context
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_context_merge(self, conversation_repo, mock_session):
        """Test merging conversation context."""
        conversation_id = str(uuid4())
        mock_conversation = MagicMock()
        mock_conversation.id = conversation_id
        mock_conversation.context = {"old": "value", "keep": "this"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_session.execute.return_value = mock_result

        new_context = {"new": "value"}
        result = await conversation_repo.update_context(conversation_id, new_context, merge=True)

        assert result == mock_conversation
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_context_not_found(self, conversation_repo, mock_session):
        """Test updating context when conversation doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.update_context(str(uuid4()), {"key": "value"})

        assert result is None


class TestConversationRepositoryUpdateTitle:
    """Tests for ConversationRepository.update_title method."""

    @pytest.mark.asyncio
    async def test_update_title_success(self, conversation_repo, mock_session):
        """Test updating conversation title."""
        conversation_id = str(uuid4())
        mock_conversation = MagicMock()
        mock_conversation.id = conversation_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.update_title(conversation_id, "New Title")

        assert result == mock_conversation
        assert mock_conversation.title == "New Title"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_title_not_found(self, conversation_repo, mock_session):
        """Test updating title when conversation doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.update_title(str(uuid4()), "New Title")

        assert result is None


class TestConversationRepositoryCount:
    """Tests for ConversationRepository.count method."""

    @pytest.mark.asyncio
    async def test_count_all(self, conversation_repo, mock_session):
        """Test counting all conversations."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.count()

        assert result == 10

    @pytest.mark.asyncio
    async def test_count_by_user(self, conversation_repo, mock_session):
        """Test counting conversations for a user."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.count(user_id="user123")

        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_status(self, conversation_repo, mock_session):
        """Test counting conversations by status."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.count(status=ConversationStatus.ACTIVE)

        assert result == 3


class TestConversationRepositoryDelete:
    """Tests for ConversationRepository.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, conversation_repo, mock_session):
        """Test deleting conversation."""
        conversation_id = str(uuid4())
        mock_conversation = MagicMock()
        mock_conversation.id = conversation_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.delete(conversation_id)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_conversation)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, conversation_repo, mock_session):
        """Test deleting non-existent conversation."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await conversation_repo.delete(str(uuid4()))

        assert result is False


# ─── MessageRepository ────────────────────────────────────────────────────────


class TestMessageRepositoryCreate:
    """Tests for MessageRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_success(self, message_repo, mock_session):
        """Test creating a new message."""
        result = await message_repo.create(
            conversation_id=str(uuid4()),
            role="user",
            content="Hello",
            tokens_used=10,
            latency_ms=100,
        )

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()


class TestMessageRepositoryGetById:
    """Tests for MessageRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, message_repo, mock_session):
        """Test getting message by ID when it exists."""
        message_id = str(uuid4())
        mock_message = MagicMock()
        mock_message.id = message_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_session.execute.return_value = mock_result

        result = await message_repo.get_by_id(message_id)

        assert result == mock_message

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, message_repo, mock_session):
        """Test getting message by ID when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await message_repo.get_by_id(str(uuid4()))

        assert result is None


class TestMessageRepositoryListByConversation:
    """Tests for MessageRepository.list_by_conversation method."""

    @pytest.mark.asyncio
    async def test_list_by_conversation(self, message_repo, mock_session):
        """Test listing messages in a conversation."""
        mock_messages = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_session.execute.return_value = mock_result

        result = await message_repo.list_by_conversation(str(uuid4()))

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_by_conversation_with_limit(self, message_repo, mock_session):
        """Test listing messages with limit."""
        mock_messages = [MagicMock() for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_session.execute.return_value = mock_result

        result = await message_repo.list_by_conversation(str(uuid4()), limit=10)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_by_conversation_with_since(self, message_repo, mock_session):
        """Test listing messages since a timestamp."""
        mock_messages = [MagicMock() for _ in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_session.execute.return_value = mock_result

        since = datetime.now(UTC)
        result = await message_repo.list_by_conversation(str(uuid4()), since=since)

        assert len(result) == 2


class TestMessageRepositoryGetLastN:
    """Tests for MessageRepository.get_last_n method."""

    @pytest.mark.asyncio
    async def test_get_last_n(self, message_repo, mock_session):
        """Test getting last N messages."""
        mock_messages = [MagicMock() for _ in range(5)]

        # First call for subquery
        mock_result_subquery = MagicMock()
        mock_result_subquery.scalars.return_value.all.return_value = [MagicMock() for _ in range(5)]

        # Second call for main query
        mock_result_main = MagicMock()
        mock_result_main.scalars.return_value.all.return_value = mock_messages

        mock_session.execute.side_effect = [mock_result_subquery, mock_result_main]

        result = await message_repo.get_last_n(str(uuid4()), n=5)

        assert len(result) == 5


class TestMessageRepositoryCountByConversation:
    """Tests for MessageRepository.count_by_conversation method."""

    @pytest.mark.asyncio
    async def test_count_by_conversation(self, message_repo, mock_session):
        """Test counting messages in a conversation."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 15
        mock_session.execute.return_value = mock_result

        result = await message_repo.count_by_conversation(str(uuid4()))

        assert result == 15


class TestMessageRepositoryGetTokenUsage:
    """Tests for MessageRepository.get_token_usage method."""

    @pytest.mark.asyncio
    async def test_get_token_usage(self, message_repo, mock_session):
        """Test getting total token usage for a conversation."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1000
        mock_session.execute.return_value = mock_result

        result = await message_repo.get_token_usage(str(uuid4()))

        assert result == 1000

    @pytest.mark.asyncio
    async def test_get_token_usage_zero(self, message_repo, mock_session):
        """Test getting token usage when none exists."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await message_repo.get_token_usage(str(uuid4()))

        assert result == 0


# ─── ProposalRepository ────────────────────────────────────────────────────────


class TestProposalRepositoryCreate:
    """Tests for ProposalRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_success(self, proposal_repo, mock_session):
        """Test creating a new proposal."""
        result = await proposal_repo.create(
            name="Test Automation",
            trigger={"platform": "state"},
            actions=[{"service": "light.turn_on"}],
        )

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_original_yaml(self, proposal_repo, mock_session):
        """Test creating a review proposal with original_yaml for diff rendering."""
        original = "alias: Old\ntrigger:\n  platform: sun\n"
        notes = [{"change": "Added offset", "rationale": "Better timing", "category": "behavioral"}]

        result = await proposal_repo.create(
            name="Improved: Sunset",
            trigger={"platform": "sun", "event": "sunset"},
            actions=[{"service": "light.turn_on"}],
            original_yaml=original,
            review_notes=notes,
        )

        assert result is not None
        assert result.original_yaml == original
        assert result.review_notes == notes
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_without_original_yaml_defaults_to_none(self, proposal_repo, mock_session):
        """Non-review proposals should have null original_yaml."""
        result = await proposal_repo.create(
            name="Normal Automation",
            trigger={"platform": "state"},
            actions=[{"service": "light.turn_on"}],
        )

        assert result.original_yaml is None
        assert result.review_notes is None


class TestProposalRepositoryGetById:
    """Tests for ProposalRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, proposal_repo, mock_session):
        """Test getting proposal by ID when it exists."""
        proposal_id = str(uuid4())
        mock_proposal = MagicMock()
        mock_proposal.id = proposal_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.get_by_id(proposal_id)

        assert result == mock_proposal

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, proposal_repo, mock_session):
        """Test getting proposal by ID when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.get_by_id(str(uuid4()))

        assert result is None


class TestProposalRepositoryListByStatus:
    """Tests for ProposalRepository.list_by_status method."""

    @pytest.mark.asyncio
    async def test_list_by_status(self, proposal_repo, mock_session):
        """Test listing proposals by status."""
        mock_proposals = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_proposals
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.list_by_status(ProposalStatus.DRAFT, limit=50)

        assert len(result) == 5


class TestProposalRepositoryListByConversation:
    """Tests for ProposalRepository.list_by_conversation method."""

    @pytest.mark.asyncio
    async def test_list_by_conversation(self, proposal_repo, mock_session):
        """Test listing proposals for a conversation."""
        mock_proposals = [MagicMock() for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_proposals
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.list_by_conversation(str(uuid4()))

        assert len(result) == 3


class TestProposalRepositoryListPendingApproval:
    """Tests for ProposalRepository.list_pending_approval method."""

    @pytest.mark.asyncio
    async def test_list_pending_approval(self, proposal_repo, mock_session):
        """Test listing proposals pending approval."""
        mock_proposals = [MagicMock() for _ in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_proposals
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.list_pending_approval(limit=50)

        assert len(result) == 2


class TestProposalRepositoryListDeployed:
    """Tests for ProposalRepository.list_deployed method."""

    @pytest.mark.asyncio
    async def test_list_deployed(self, proposal_repo, mock_session):
        """Test listing deployed proposals."""
        mock_proposals = [MagicMock() for _ in range(4)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_proposals
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.list_deployed(limit=100)

        assert len(result) == 4


class TestProposalRepositoryPropose:
    """Tests for ProposalRepository.propose method."""

    @pytest.mark.asyncio
    async def test_propose_success(self, proposal_repo, mock_session):
        """Test submitting proposal for approval."""
        proposal_id = str(uuid4())
        mock_proposal = MagicMock()
        mock_proposal.id = proposal_id
        mock_proposal.propose = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.propose(proposal_id)

        assert result == mock_proposal
        mock_proposal.propose.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_propose_not_found(self, proposal_repo, mock_session):
        """Test proposing when proposal doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.propose(str(uuid4()))

        assert result is None


class TestProposalRepositoryApprove:
    """Tests for ProposalRepository.approve method."""

    @pytest.mark.asyncio
    async def test_approve_success(self, proposal_repo, mock_session):
        """Test approving a proposal."""
        proposal_id = str(uuid4())
        mock_proposal = MagicMock()
        mock_proposal.id = proposal_id
        mock_proposal.approve = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.approve(proposal_id, approved_by="user123")

        assert result == mock_proposal
        mock_proposal.approve.assert_called_once_with("user123")
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_not_found(self, proposal_repo, mock_session):
        """Test approving when proposal doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.approve(str(uuid4()), approved_by="user123")

        assert result is None


class TestProposalRepositoryReject:
    """Tests for ProposalRepository.reject method."""

    @pytest.mark.asyncio
    async def test_reject_success(self, proposal_repo, mock_session):
        """Test rejecting a proposal."""
        proposal_id = str(uuid4())
        mock_proposal = MagicMock()
        mock_proposal.id = proposal_id
        mock_proposal.reject = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.reject(proposal_id, reason="Not needed")

        assert result == mock_proposal
        mock_proposal.reject.assert_called_once_with("Not needed")
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_not_found(self, proposal_repo, mock_session):
        """Test rejecting when proposal doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.reject(str(uuid4()), reason="Test")

        assert result is None


class TestProposalRepositoryDeploy:
    """Tests for ProposalRepository.deploy method."""

    @pytest.mark.asyncio
    async def test_deploy_success(self, proposal_repo, mock_session):
        """Test deploying a proposal."""
        proposal_id = str(uuid4())
        mock_proposal = MagicMock()
        mock_proposal.id = proposal_id
        mock_proposal.deploy = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.deploy(proposal_id, ha_automation_id="auto123")

        assert result == mock_proposal
        mock_proposal.deploy.assert_called_once_with("auto123")
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_not_found(self, proposal_repo, mock_session):
        """Test deploying when proposal doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.deploy(str(uuid4()), ha_automation_id="auto123")

        assert result is None


class TestProposalRepositoryRollback:
    """Tests for ProposalRepository.rollback method."""

    @pytest.mark.asyncio
    async def test_rollback_success(self, proposal_repo, mock_session):
        """Test rolling back a deployed proposal."""
        proposal_id = str(uuid4())
        mock_proposal = MagicMock()
        mock_proposal.id = proposal_id
        mock_proposal.rollback = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.rollback(proposal_id)

        assert result == mock_proposal
        mock_proposal.rollback.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_not_found(self, proposal_repo, mock_session):
        """Test rolling back when proposal doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.rollback(str(uuid4()))

        assert result is None


class TestProposalRepositoryDelete:
    """Tests for ProposalRepository.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, proposal_repo, mock_session):
        """Test deleting a proposal."""
        proposal_id = str(uuid4())
        mock_proposal = MagicMock()
        mock_proposal.id = proposal_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_proposal
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.delete(proposal_id)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_proposal)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, proposal_repo, mock_session):
        """Test deleting non-existent proposal."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.delete(str(uuid4()))

        assert result is False


class TestProposalRepositoryCount:
    """Tests for ProposalRepository.count method."""

    @pytest.mark.asyncio
    async def test_count_all(self, proposal_repo, mock_session):
        """Test counting all proposals."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 20
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.count()

        assert result == 20

    @pytest.mark.asyncio
    async def test_count_by_status(self, proposal_repo, mock_session):
        """Test counting proposals by status."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await proposal_repo.count(status=ProposalStatus.DRAFT)

        assert result == 5
