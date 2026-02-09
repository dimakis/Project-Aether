"""Unit tests for CLI chat command."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli.main import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_workflow():
    """Mock ArchitectWorkflow."""
    workflow = MagicMock()
    workflow.start_conversation = AsyncMock()
    workflow.continue_conversation = AsyncMock()
    return workflow


@pytest.fixture
def mock_conversation_repo():
    """Mock conversation repository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


class TestChat:
    """Test chat command."""

    def test_chat_with_message(self, runner, mock_session, mock_workflow):
        """Test chat with initial message."""
        from langchain_core.messages import AIMessage

        from src.graph.state import ConversationState

        mock_state = ConversationState(
            conversation_id="conv-123",
            messages=[AIMessage(content="Hello! How can I help?")],
        )

        mock_workflow.start_conversation = AsyncMock(return_value=mock_state)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch(
                "src.tracing.get_tracing_status",
                return_value={"tracking_uri": "", "experiment_name": "", "traces_enabled": False},
            ),
            patch("src.agents.ArchitectWorkflow", return_value=mock_workflow),
            patch("src.tracing.context.session_context"),
            patch("src.tracing.context.set_session_id"),
            patch("src.dal.ConversationRepository"),
            patch("src.dal.MessageRepository"),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = runner.invoke(app, ["chat", "Turn on lights"])

            assert result.exit_code == 0
            mock_workflow.start_conversation.assert_called_once()

    def test_chat_continue_conversation(
        self, runner, mock_session, mock_workflow, mock_conversation_repo
    ):
        """Test continuing an existing conversation."""
        from datetime import UTC, datetime

        from langchain_core.messages import AIMessage

        from src.graph.state import ConversationState
        from src.storage.entities.conversation import Conversation
        from src.storage.entities.message import Message

        mock_conv = Conversation(
            id="conv-123",
            created_at=datetime.now(UTC),
        )
        mock_conv.messages = [
            Message(id="1", role="user", content="Hello", created_at=datetime.now(UTC)),
            Message(id="2", role="assistant", content="Hi!", created_at=datetime.now(UTC)),
        ]

        mock_conversation_repo.get_by_id = AsyncMock(return_value=mock_conv)

        mock_state = ConversationState(
            conversation_id="conv-123",
            messages=[AIMessage(content="How can I help?")],
        )

        mock_workflow.continue_conversation = AsyncMock(return_value=mock_state)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch(
                "src.tracing.get_tracing_status",
                return_value={"tracking_uri": "", "experiment_name": "", "traces_enabled": False},
            ),
            patch("src.agents.ArchitectWorkflow", return_value=mock_workflow),
            patch("src.tracing.context.session_context"),
            patch("src.tracing.context.set_session_id"),
            patch("src.dal.ConversationRepository", return_value=mock_conversation_repo),
            patch("src.dal.MessageRepository"),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = runner.invoke(app, ["chat", "--continue", "conv-123", "More help"])

            assert result.exit_code == 0
            mock_workflow.continue_conversation.assert_called_once()

    def test_chat_conversation_not_found(self, runner, mock_session, mock_conversation_repo):
        """Test continuing conversation that doesn't exist."""
        mock_conversation_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch(
                "src.tracing.get_tracing_status",
                return_value={"tracking_uri": "", "experiment_name": "", "traces_enabled": False},
            ),
            patch("src.tracing.context.session_context"),
            patch("src.dal.ConversationRepository", return_value=mock_conversation_repo),
            patch("src.dal.MessageRepository"),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = runner.invoke(app, ["chat", "--continue", "nonexistent"])

            assert result.exit_code == 0
            assert "not found" in result.stdout

    def test_chat_with_pending_approval(self, runner, mock_session, mock_workflow):
        """Test chat with pending proposal approval."""
        from langchain_core.messages import AIMessage

        from src.graph.state import ConversationState, HITLApproval

        mock_approval = HITLApproval(
            id="prop-123",
            request_type="automation",
            description="Test Proposal",
            yaml_content="alias: Test Proposal",
        )

        mock_state = ConversationState(
            conversation_id="conv-123",
            messages=[AIMessage(content="I created a proposal")],
            pending_approvals=[mock_approval],
        )

        mock_workflow.start_conversation = AsyncMock(return_value=mock_state)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch(
                "src.tracing.get_tracing_status",
                return_value={"tracking_uri": "", "experiment_name": "", "traces_enabled": False},
            ),
            patch("src.agents.ArchitectWorkflow", return_value=mock_workflow),
            patch("src.tracing.context.session_context"),
            patch("src.tracing.context.set_session_id"),
            patch("src.dal.ConversationRepository"),
            patch("src.dal.MessageRepository"),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = runner.invoke(app, ["chat", "Create automation"])

            assert result.exit_code == 0
            assert "Proposal pending approval" in result.stdout
