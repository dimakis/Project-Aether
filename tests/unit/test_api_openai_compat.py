"""Unit tests for OpenAI-compatible API routes.

Tests chat completions, models list, and feedback endpoints.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter
from src.graph.state import ConversationState


def _make_test_app():
    """Create a minimal FastAPI app with the OpenAI compat router."""
    from fastapi import FastAPI

    from src.api.routes.openai_compat import router

    app = FastAPI()
    app.include_router(router, prefix="/v1")

    # Configure rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    return app


@pytest.fixture
def openai_app():
    """Lightweight FastAPI app with OpenAI compat routes."""
    return _make_test_app()


@pytest.fixture
async def openai_client(openai_app):
    """Async HTTP client wired to the OpenAI compat test app."""
    async with AsyncClient(
        transport=ASGITransport(app=openai_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
class TestListModels:
    """Tests for GET /v1/models."""

    async def test_list_models_success(self, openai_client):
        """Should return list of available models."""
        mock_model = MagicMock()
        mock_model.id = "gpt-4o"
        mock_model.provider = "openai"

        with (
            patch("src.api.services.model_discovery.get_model_discovery") as mock_get_discovery,
            patch("src.llm_pricing.get_model_pricing") as mock_get_pricing,
        ):
            mock_discovery = AsyncMock()
            mock_discovery.discover_all = AsyncMock(return_value=[mock_model])
            mock_get_discovery.return_value = mock_discovery

            mock_get_pricing.return_value = {"input_per_1m": 2.5, "output_per_1m": 10.0}

            response = await openai_client.get("/v1/models")

            assert response.status_code == 200
            data = response.json()
            assert data["object"] == "list"
            assert len(data["data"]) == 1
            assert data["data"][0]["id"] == "gpt-4o"

    async def test_list_models_empty(self, openai_client):
        """Should return empty list when no models."""
        with patch("src.api.services.model_discovery.get_model_discovery") as mock_get_discovery:
            mock_discovery = AsyncMock()
            mock_discovery.discover_all = AsyncMock(return_value=[])
            mock_get_discovery.return_value = mock_discovery

            response = await openai_client.get("/v1/models")

            assert response.status_code == 200
            data = response.json()
            assert data["data"] == []


@pytest.mark.asyncio
class TestSubmitFeedback:
    """Tests for POST /v1/feedback."""

    async def test_submit_feedback_success(self, openai_client):
        """Should submit feedback successfully."""
        mock_mlflow = MagicMock()
        with patch.dict("sys.modules", {"mlflow": mock_mlflow}):

            response = await openai_client.post(
                "/v1/feedback",
                json={"trace_id": "trace-123", "sentiment": "positive"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    async def test_submit_feedback_fallback(self, openai_client):
        """Should fallback to set_trace_tag when log_feedback fails."""
        mock_mlflow = MagicMock()
        with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
            mock_mlflow.log_feedback.side_effect = Exception("Not available")
            mock_client = MagicMock()
            mock_mlflow.MlflowClient.return_value = mock_client

            response = await openai_client.post(
                "/v1/feedback",
                json={"trace_id": "trace-123", "sentiment": "positive"},
            )

            assert response.status_code == 200
            mock_client.set_trace_tag.assert_called_once()

    async def test_submit_feedback_invalid_sentiment(self, openai_client):
        """Should return 400 for invalid sentiment."""
        response = await openai_client.post(
            "/v1/feedback",
            json={"trace_id": "trace-123", "sentiment": "neutral"},
        )

        assert response.status_code == 400


@pytest.mark.asyncio
class TestChatCompletion:
    """Tests for POST /v1/chat/completions."""

    async def test_chat_completion_non_streaming_success(self, openai_client, mock_session):
        """Should return non-streaming chat completion."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        mock_state = ConversationState(
            conversation_id="conv-123",
            messages=[AIMessage(content="Hello, how can I help?")],
        )
        mock_state.last_trace_id = "trace-123"

        with (
            patch("src.api.routes.openai_compat.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.openai_compat.session_context") as mock_context,
            patch("src.api.routes.openai_compat.start_experiment_run") as mock_run,
            patch.dict("sys.modules", {"mlflow": MagicMock()}),
            patch("src.api.routes.openai_compat.ArchitectWorkflow") as MockWorkflow,
            patch("src.api.routes.openai_compat.model_context") as mock_model_ctx,
        ):
            mock_context.return_value.__enter__ = MagicMock()
            mock_context.return_value.__exit__ = MagicMock(return_value=False)

            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            mock_workflow = MagicMock()
            mock_workflow.continue_conversation = AsyncMock(return_value=mock_state)
            MockWorkflow.return_value = mock_workflow

            mock_model_ctx.return_value.__enter__ = MagicMock()
            mock_model_ctx.return_value.__exit__ = MagicMock(return_value=False)

            response = await openai_client.post(
                "/v1/chat/completions",
                json={
                    "model": "architect",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert data["choices"][0]["message"]["role"] == "assistant"

    async def test_chat_completion_no_user_message(self, openai_client, mock_session):
        """Should return 400 when no user message."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.openai_compat.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.openai_compat.session_context") as mock_context,
            patch("src.api.routes.openai_compat.start_experiment_run") as mock_run,
        ):
            mock_context.return_value.__enter__ = MagicMock()
            mock_context.return_value.__exit__ = MagicMock(return_value=False)

            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            response = await openai_client.post(
                "/v1/chat/completions",
                json={
                    "model": "architect",
                    "messages": [{"role": "system", "content": "You are a helper"}],
                    "stream": False,
                },
            )

            assert response.status_code == 400

    async def test_chat_completion_streaming(self, openai_client, mock_session):
        """Should return streaming response."""
        mock_state = ConversationState(
            conversation_id="conv-123",
            messages=[AIMessage(content="Hello")],
        )

        async def mock_stream():
            yield {"type": "token", "content": "Hello"}
            yield {"type": "token", "content": " world"}
            yield {"type": "trace_id", "content": "trace-123"}
            yield {"type": "state", "state": mock_state}

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.openai_compat.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.openai_compat.session_context") as mock_context,
            patch("src.api.routes.openai_compat.start_experiment_run") as mock_run,
            patch.dict("sys.modules", {"mlflow": MagicMock()}),
            patch("src.api.routes.openai_compat.ArchitectWorkflow") as MockWorkflow,
            patch("src.api.routes.openai_compat.model_context") as mock_model_ctx,
        ):
            mock_context.return_value.__enter__ = MagicMock()
            mock_context.return_value.__exit__ = MagicMock(return_value=False)

            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            mock_workflow = MagicMock()
            mock_workflow.stream_conversation = AsyncMock(return_value=mock_stream())
            MockWorkflow.return_value = mock_workflow

            mock_model_ctx.return_value.__enter__ = MagicMock()
            mock_model_ctx.return_value.__exit__ = MagicMock(return_value=False)

            response = await openai_client.post(
                "/v1/chat/completions",
                json={
                    "model": "architect",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                },
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    async def test_chat_completion_with_conversation_id(self, openai_client, mock_session):
        """Should use provided conversation_id."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        mock_state = ConversationState(
            conversation_id="provided-conv-id",
            messages=[AIMessage(content="Response")],
        )

        with (
            patch("src.api.routes.openai_compat.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.openai_compat.session_context") as mock_context,
            patch("src.api.routes.openai_compat.start_experiment_run") as mock_run,
            patch.dict("sys.modules", {"mlflow": MagicMock()}),
            patch("src.api.routes.openai_compat.ArchitectWorkflow") as MockWorkflow,
            patch("src.api.routes.openai_compat.model_context") as mock_model_ctx,
        ):
            mock_context.return_value.__enter__ = MagicMock()
            mock_context.return_value.__exit__ = MagicMock(return_value=False)

            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            mock_workflow = MagicMock()
            mock_workflow.continue_conversation = AsyncMock(return_value=mock_state)
            MockWorkflow.return_value = mock_workflow

            mock_model_ctx.return_value.__enter__ = MagicMock()
            mock_model_ctx.return_value.__exit__ = MagicMock(return_value=False)

            response = await openai_client.post(
                "/v1/chat/completions",
                json={
                    "model": "architect",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "conversation_id": "provided-conv-id",
                    "stream": False,
                },
            )

            assert response.status_code == 200
            mock_context.assert_called_once_with("provided-conv-id")
