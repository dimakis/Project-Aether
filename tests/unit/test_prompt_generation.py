"""Unit tests for AI-assisted prompt generation endpoint.

Tests POST /api/v1/agents/{name}/prompt/generate.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.api.main import create_app
from src.settings import Settings, get_settings

JWT_SECRET = "test-jwt-secret-key-for-testing-minimum-32bytes"


def _make_settings(**overrides) -> Settings:
    defaults = {
        "environment": "testing",
        "debug": True,
        "database_url": "postgresql+asyncpg://test:test@localhost:5432/aether_test",
        "ha_url": "http://localhost:8123",
        "ha_token": SecretStr("test-token"),
        "openai_api_key": SecretStr("test-api-key"),
        "mlflow_tracking_uri": "http://localhost:5000",
        "sandbox_enabled": False,
        "auth_username": "admin",
        "auth_password": SecretStr("test-password"),
        "jwt_secret": SecretStr(JWT_SECRET),
        "api_key": SecretStr(""),
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_jwt() -> str:
    payload = {
        "sub": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 72 * 3600,
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture
async def client(monkeypatch):
    """Test client with auth configured."""
    get_settings.cache_clear()
    settings = _make_settings()
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    get_settings.cache_clear()


@pytest.mark.asyncio
class TestPromptGeneration:
    """Test POST /api/v1/agents/{name}/prompt/generate."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/agents/architect/prompt/generate",
            json={},
        )
        assert response.status_code == 401

    async def test_agent_not_found(self, client: AsyncClient):
        token = _make_jwt()
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_name = AsyncMock(return_value=None)

        with patch("src.api.routes.agents.get_session") as mock_gs:
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("src.api.routes.agents.AgentRepository", return_value=mock_repo):
                response = await client.post(
                    "/api/v1/agents/nonexistent/prompt/generate",
                    json={},
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 404

    async def test_generates_prompt_with_user_input(self, client: AsyncClient):
        token = _make_jwt()

        # Mock agent
        mock_agent = MagicMock()
        mock_agent.name = "data_scientist"
        mock_agent.description = "Energy analysis and data-driven insights."
        mock_agent.active_prompt_version = None

        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_agent)

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.content = "You are the Data Scientist agent..."

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        with patch("src.api.routes.agents.get_session") as mock_gs:
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("src.api.routes.agents.AgentRepository", return_value=mock_repo):
                with patch("src.llm.get_llm", return_value=mock_llm):
                    response = await client.post(
                        "/api/v1/agents/data_scientist/prompt/generate",
                        json={"user_input": "Focus on energy optimization"},
                        headers={"Authorization": f"Bearer {token}"},
                    )

        assert response.status_code == 200
        data = response.json()
        assert "generated_prompt" in data
        assert data["generated_prompt"] == "You are the Data Scientist agent..."
        mock_llm.ainvoke.assert_awaited_once()

    async def test_generates_prompt_without_user_input(self, client: AsyncClient):
        token = _make_jwt()

        mock_agent = MagicMock()
        mock_agent.name = "architect"
        mock_agent.description = "Automation design and user interaction."
        mock_agent.active_prompt_version = MagicMock()
        mock_agent.active_prompt_version.prompt_template = "Current prompt content..."

        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_agent)

        mock_llm_response = MagicMock()
        mock_llm_response.content = "Generated prompt content..."

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        with patch("src.api.routes.agents.get_session") as mock_gs:
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("src.api.routes.agents.AgentRepository", return_value=mock_repo):
                with patch("src.llm.get_llm", return_value=mock_llm):
                    response = await client.post(
                        "/api/v1/agents/architect/prompt/generate",
                        json={},
                        headers={"Authorization": f"Bearer {token}"},
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["generated_prompt"] == "Generated prompt content..."
