"""Unit tests for Chat API routes.

Tests HTTP endpoints for conversations (POST, GET, DELETE) with mock
repositories and workflows -- no real database or LLM calls needed.

The get_session dependency is mocked so the test never attempts a real
Postgres connection (which would hang indefinitely in a unit-test environment).
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage

from src.storage import get_session


def _make_test_app():
    """Create a minimal FastAPI app with the chat router and mock DB."""
    from fastapi import FastAPI

    from src.api.routes.chat import router

    app = FastAPI()
    app.include_router(router)

    # Override get_session so no real Postgres connection is attempted
    @asynccontextmanager
    async def _mock_get_session():
        yield MagicMock()

    app.dependency_overrides[get_session] = _mock_get_session
    return app


@pytest.fixture
def chat_app():
    """Lightweight FastAPI app with chat routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def chat_client(chat_app):
    """Async HTTP client wired to the chat test app."""
    async with AsyncClient(
        transport=ASGITransport(app=chat_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_agent():
    """Create a mock Agent object."""
    agent = MagicMock()
    agent.id = "agent-architect-1"
    agent.name = "Architect"
    agent.description = "Conversational automation design agent"
    agent.agent_type = "architect"
    agent.is_active = True
    return agent


@pytest.fixture
def mock_conversation():
    """Create a mock Conversation object."""
    conv = MagicMock()
    conv.id = "conv-123"
    conv.agent_id = "agent-architect-1"
    conv.user_id = "default_user"
    conv.title = "Test Conversation"
    conv.status = MagicMock()
    conv.status.value = "active"
    conv.context = {"key": "value"}
    conv.created_at = datetime.now(UTC)
    conv.updated_at = datetime.now(UTC)
    conv.messages = []
    conv.proposals = []
    return conv


@pytest.fixture
def mock_message():
    """Create a mock Message object."""
    msg = MagicMock()
    msg.id = "msg-123"
    msg.conversation_id = "conv-123"
    msg.role = "user"
    msg.content = "Hello, I want to automate my lights"
    msg.tool_calls = None
    msg.tool_results = None
    msg.tokens_used = None
    msg.latency_ms = None
    msg.created_at = datetime.now(UTC)
    return msg


@pytest.fixture
def mock_conversation_state():
    """Create a mock ConversationState."""
    from src.graph.state import ConversationState, ConversationStatus

    state = MagicMock(spec=ConversationState)
    state.conversation_id = "conv-123"
    state.messages = [
        HumanMessage(content="Hello, I want to automate my lights"),
        AIMessage(content="I can help you automate your lights!"),
    ]
    state.pending_approvals = []
    state.status = MagicMock()
    state.status.value = ConversationStatus.ACTIVE.value
    return state


@pytest.fixture
def mock_conv_repo(mock_conversation):
    """Create mock ConversationRepository."""
    repo = MagicMock()
    repo.create = AsyncMock(return_value=mock_conversation)
    repo.get_by_id = AsyncMock(return_value=mock_conversation)
    repo.list_by_user = AsyncMock(return_value=[mock_conversation])
    repo.count = AsyncMock(return_value=1)
    repo.update_status = AsyncMock()
    repo.update_context = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_msg_repo(mock_message):
    """Create mock MessageRepository."""
    repo = MagicMock()
    repo.create = AsyncMock(return_value=mock_message)
    repo.list_by_conversation = AsyncMock(return_value=[mock_message])
    return repo


@pytest.fixture
def mock_workflow(mock_conversation_state):
    """Create mock ArchitectWorkflow."""
    workflow = MagicMock()
    workflow.start_conversation = AsyncMock(return_value=mock_conversation_state)
    workflow.continue_conversation = AsyncMock(return_value=mock_conversation_state)
    return workflow


@pytest.fixture
def mock_mlflow():
    """Create a mock mlflow module with trace as a passthrough decorator."""
    mock_mlflow = MagicMock()

    def noop_trace(**kwargs):
        def decorator(fn):
            return fn

        return decorator

    mock_mlflow.trace = noop_trace
    mock_mlflow.get_current_active_span = MagicMock(return_value=None)
    mock_mlflow.update_current_trace = MagicMock()
    return mock_mlflow


@pytest.mark.asyncio
class TestCreateConversation:
    """Tests for POST /conversations."""

    async def test_create_conversation_success(
        self,
        chat_client,
        mock_agent,
        mock_conversation,
        mock_message,
        mock_conv_repo,
        mock_msg_repo,
        mock_workflow,
        mock_mlflow,
    ):
        """Should create a new conversation and return details."""
        # Setup: conversation with messages
        mock_conversation.messages = [mock_message]
        assistant_msg = MagicMock()
        assistant_msg.id = "msg-assistant-1"
        assistant_msg.conversation_id = "conv-123"
        assistant_msg.role = "assistant"
        assistant_msg.content = "I can help you automate your lights!"
        assistant_msg.tool_calls = None
        assistant_msg.tool_results = None
        assistant_msg.tokens_used = None
        assistant_msg.latency_ms = None
        assistant_msg.created_at = datetime.now(UTC)
        mock_conversation.messages.append(assistant_msg)

        # Setup: state with assistant message
        from src.graph.state import ConversationState

        state = MagicMock(spec=ConversationState)
        state.messages = [
            HumanMessage(content="Hello, I want to automate my lights"),
            AIMessage(content="I can help you automate your lights!"),
        ]
        state.pending_approvals = []
        mock_workflow.start_conversation = AsyncMock(return_value=state)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
            patch("src.api.routes.chat.MessageRepository", return_value=mock_msg_repo),
            patch("src.agents.ArchitectWorkflow", return_value=mock_workflow),
            patch("src.api.routes.chat.model_context", MagicMock()),
            patch(
                "src.settings.get_settings",
                MagicMock(return_value=MagicMock(llm_model="test-model", llm_temperature=0.7)),
            ),
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
        ):
            # Mock session context manager
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock Agent query
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=mock_agent)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_session.commit = AsyncMock()

            response = await chat_client.post(
                "/conversations",
                json={
                    "title": "Test Conversation",
                    "initial_message": "Hello, I want to automate my lights",
                    "context": {"key": "value"},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "conv-123"
            assert data["title"] == "Test Conversation"
            assert data["status"] == "active"
            assert "messages" in data
            mock_conv_repo.create.assert_called_once()
            mock_msg_repo.create.assert_called()

    async def test_create_conversation_creates_agent_if_missing(
        self,
        chat_client,
        mock_agent,
        mock_conversation,
        mock_conv_repo,
        mock_msg_repo,
        mock_workflow,
        mock_mlflow,
    ):
        """Should create Architect agent if it doesn't exist."""
        from src.graph.state import ConversationState

        state = MagicMock(spec=ConversationState)
        state.messages = [AIMessage(content="Response")]
        state.pending_approvals = []
        mock_workflow.start_conversation = AsyncMock(return_value=state)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
            patch("src.api.routes.chat.MessageRepository", return_value=mock_msg_repo),
            patch("src.agents.ArchitectWorkflow", return_value=mock_workflow),
            patch("src.api.routes.chat.model_context", MagicMock()),
            patch(
                "src.settings.get_settings",
                MagicMock(return_value=MagicMock(llm_model="test-model", llm_temperature=0.7)),
            ),
            patch(
                "src.api.routes.chat.uuid4",
                return_value=MagicMock(__str__=lambda _: "new-agent-id"),
            ),
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # Agent doesn't exist initially
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_session.commit = AsyncMock()

            response = await chat_client.post(
                "/conversations",
                json={
                    "initial_message": "Hello",
                },
            )

            assert response.status_code == 200
            # Should have created agent
            mock_session.add.assert_called()
            mock_session.flush.assert_called()


@pytest.mark.asyncio
class TestListConversations:
    """Tests for GET /conversations."""

    async def test_list_conversations_success(
        self,
        chat_client,
        mock_conversation,
        mock_conv_repo,
    ):
        """Should return list of conversations."""
        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.get("/conversations")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["id"] == "conv-123"
            mock_conv_repo.list_by_user.assert_called_once()

    async def test_list_conversations_with_status_filter(
        self,
        chat_client,
        mock_conversation,
        mock_conv_repo,
    ):
        """Should filter conversations by status."""
        from src.storage.entities import ConversationStatus

        mock_conversation.status.value = ConversationStatus.ACTIVE.value

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.get("/conversations?status=active")

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            # Verify status filter was passed
            call_kwargs = mock_conv_repo.list_by_user.call_args[1]
            assert call_kwargs["status"] == ConversationStatus.ACTIVE

    async def test_list_conversations_with_pagination(
        self,
        chat_client,
        mock_conversation,
        mock_conv_repo,
    ):
        """Should support pagination parameters."""
        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.get("/conversations?limit=10&offset=5")

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 5
            call_kwargs = mock_conv_repo.list_by_user.call_args[1]
            assert call_kwargs["limit"] == 10
            assert call_kwargs["offset"] == 5

    async def test_list_conversations_empty(
        self,
        chat_client,
    ):
        """Should return empty list when no conversations exist."""
        repo = MagicMock()
        repo.list_by_user = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.get("/conversations")

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["total"] == 0


@pytest.mark.asyncio
class TestGetConversation:
    """Tests for GET /conversations/{conversation_id}."""

    async def test_get_conversation_success(
        self,
        chat_client,
        mock_conversation,
        mock_message,
        mock_conv_repo,
    ):
        """Should return conversation with messages."""
        assistant_msg = MagicMock()
        assistant_msg.id = "msg-assistant-1"
        assistant_msg.conversation_id = "conv-123"
        assistant_msg.role = "assistant"
        assistant_msg.content = "Response"
        assistant_msg.tool_calls = None
        assistant_msg.tool_results = None
        assistant_msg.tokens_used = None
        assistant_msg.latency_ms = None
        assistant_msg.created_at = datetime.now(UTC)

        mock_conversation.messages = [mock_message, assistant_msg]
        mock_conversation.proposals = []

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.get("/conversations/conv-123")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "conv-123"
            assert "messages" in data
            assert len(data["messages"]) == 2
            mock_conv_repo.get_by_id.assert_called_once_with(
                "conv-123",
                include_messages=True,
                include_proposals=True,
            )

    async def test_get_conversation_with_pending_approvals(
        self,
        chat_client,
        mock_conversation,
        mock_conv_repo,
    ):
        """Should include pending approval IDs."""
        mock_proposal = MagicMock()
        mock_proposal.id = "proposal-123"
        mock_proposal.status.value = "proposed"
        mock_conversation.proposals = [mock_proposal]
        mock_conversation.messages = []

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.get("/conversations/conv-123")

            assert response.status_code == 200
            data = response.json()
            assert "pending_approvals" in data
            assert "proposal-123" in data["pending_approvals"]

    async def test_get_conversation_not_found(
        self,
        chat_client,
        mock_conv_repo,
    ):
        """Should return 404 when conversation not found."""
        mock_conv_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.get("/conversations/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestSendMessage:
    """Tests for POST /conversations/{conversation_id}/messages."""

    async def test_send_message_success(
        self,
        chat_client,
        mock_conversation,
        mock_message,
        mock_conv_repo,
        mock_msg_repo,
        mock_workflow,
        mock_mlflow,
    ):
        """Should send message and return assistant response."""
        from src.graph.state import ConversationState, ConversationStatus

        # Setup assistant message
        assistant_msg = MagicMock()
        assistant_msg.id = "msg-assistant-1"
        assistant_msg.conversation_id = "conv-123"
        assistant_msg.role = "assistant"
        assistant_msg.content = "I can help with that!"
        assistant_msg.tool_calls = None
        assistant_msg.tool_results = None
        assistant_msg.tokens_used = None
        assistant_msg.latency_ms = None
        assistant_msg.created_at = datetime.now(UTC)
        mock_msg_repo.create = AsyncMock(return_value=assistant_msg)

        # Setup state
        state = MagicMock(spec=ConversationState)
        state.messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="I can help with that!"),
        ]
        state.pending_approvals = []
        state.status = MagicMock()
        state.status.value = ConversationStatus.ACTIVE.value
        mock_workflow.continue_conversation = AsyncMock(return_value=state)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
            patch("src.api.routes.chat.MessageRepository", return_value=mock_msg_repo),
            patch("src.agents.ArchitectWorkflow", return_value=mock_workflow),
            patch("src.api.routes.chat.model_context", MagicMock()),
            patch(
                "src.settings.get_settings",
                MagicMock(return_value=MagicMock(llm_model="test-model", llm_temperature=0.7)),
            ),
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock()

            response = await chat_client.post(
                "/conversations/conv-123/messages",
                json={"message": "Can you help me?"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == "conv-123"
            assert "message" in data
            assert data["message"]["role"] == "assistant"
            assert data["has_proposal"] is False
            mock_msg_repo.create.assert_called()
            mock_workflow.continue_conversation.assert_called_once()

    async def test_send_message_with_context_update(
        self,
        chat_client,
        mock_conversation,
        mock_conv_repo,
        mock_msg_repo,
        mock_workflow,
        mock_mlflow,
    ):
        """Should update context when provided."""
        from src.graph.state import ConversationState, ConversationStatus

        state = MagicMock(spec=ConversationState)
        state.messages = [AIMessage(content="Response")]
        state.pending_approvals = []
        state.status = MagicMock()
        state.status.value = ConversationStatus.ACTIVE.value
        mock_workflow.continue_conversation = AsyncMock(return_value=state)

        assistant_msg = MagicMock()
        assistant_msg.id = "msg-1"
        assistant_msg.conversation_id = "conv-123"
        assistant_msg.role = "assistant"
        assistant_msg.content = "Response"
        assistant_msg.tool_calls = None
        assistant_msg.tool_results = None
        assistant_msg.tokens_used = None
        assistant_msg.latency_ms = None
        assistant_msg.created_at = datetime.now(UTC)
        mock_msg_repo.create = AsyncMock(return_value=assistant_msg)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
            patch("src.api.routes.chat.MessageRepository", return_value=mock_msg_repo),
            patch("src.agents.ArchitectWorkflow", return_value=mock_workflow),
            patch("src.api.routes.chat.model_context", MagicMock()),
            patch(
                "src.settings.get_settings",
                MagicMock(return_value=MagicMock(llm_model="test-model", llm_temperature=0.7)),
            ),
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock()

            response = await chat_client.post(
                "/conversations/conv-123/messages",
                json={
                    "message": "Hello",
                    "context": {"new_key": "new_value"},
                },
            )

            assert response.status_code == 200
            mock_conv_repo.update_context.assert_called_once_with(
                "conv-123", {"new_key": "new_value"}
            )

    async def test_send_message_with_proposal(
        self,
        chat_client,
        mock_conversation,
        mock_conv_repo,
        mock_msg_repo,
        mock_workflow,
        mock_mlflow,
    ):
        """Should return proposal ID when workflow generates one."""
        from src.graph.state import ConversationState, ConversationStatus

        # Mock proposal
        mock_proposal = MagicMock()
        mock_proposal.id = "proposal-456"

        state = MagicMock(spec=ConversationState)
        state.messages = [AIMessage(content="Response")]
        state.pending_approvals = [mock_proposal]
        state.status = MagicMock()
        state.status.value = ConversationStatus.WAITING_APPROVAL.value
        mock_workflow.continue_conversation = AsyncMock(return_value=state)

        assistant_msg = MagicMock()
        assistant_msg.id = "msg-1"
        assistant_msg.conversation_id = "conv-123"
        assistant_msg.role = "assistant"
        assistant_msg.content = "Response"
        assistant_msg.tool_calls = None
        assistant_msg.tool_results = None
        assistant_msg.tokens_used = None
        assistant_msg.latency_ms = None
        assistant_msg.created_at = datetime.now(UTC)
        mock_msg_repo.create = AsyncMock(return_value=assistant_msg)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
            patch("src.api.routes.chat.MessageRepository", return_value=mock_msg_repo),
            patch("src.agents.ArchitectWorkflow", return_value=mock_workflow),
            patch("src.api.routes.chat.model_context", MagicMock()),
            patch(
                "src.settings.get_settings",
                MagicMock(return_value=MagicMock(llm_model="test-model", llm_temperature=0.7)),
            ),
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock()

            response = await chat_client.post(
                "/conversations/conv-123/messages",
                json={"message": "Create an automation"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_proposal"] is True
            assert data["proposal_id"] == "proposal-456"

    async def test_send_message_conversation_not_found(
        self,
        chat_client,
        mock_conv_repo,
    ):
        """Should return 404 when conversation not found."""
        mock_conv_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.post(
                "/conversations/nonexistent/messages",
                json={"message": "Hello"},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestDeleteConversation:
    """Tests for DELETE /conversations/{conversation_id}."""

    async def test_delete_conversation_success(
        self,
        chat_client,
        mock_conv_repo,
    ):
        """Should delete conversation and return success."""
        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock()

            response = await chat_client.delete("/conversations/conv-123")

            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] is True
            assert data["conversation_id"] == "conv-123"
            mock_conv_repo.delete.assert_called_once_with("conv-123")

    async def test_delete_conversation_not_found(
        self,
        chat_client,
        mock_conv_repo,
    ):
        """Should return 404 when conversation not found."""
        mock_conv_repo.delete = AsyncMock(return_value=False)

        with (
            patch("src.api.routes.chat.get_session") as mock_get_session,
            patch("src.api.routes.chat.ConversationRepository", return_value=mock_conv_repo),
        ):
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await chat_client.delete("/conversations/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
