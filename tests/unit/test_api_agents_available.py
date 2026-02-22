"""Tests for GET /api/v1/agents/available endpoint (Feature 30).

Returns only routable agents with their domain, capabilities,
and intent_patterns for the Orchestrator and UI agent picker.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter
from src.storage.entities.agent import Agent, AgentStatus


def _make_test_app():
    from fastapi import FastAPI

    from src.api.routes.agents import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    return app


@pytest.fixture()
def app():
    return _make_test_app()


@pytest.fixture()
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _make_agent(
    name: str,
    *,
    domain: str | None = None,
    is_routable: bool = False,
    intent_patterns: list[str] | None = None,
    capabilities: list[str] | None = None,
    status: str = AgentStatus.ENABLED.value,
) -> Agent:
    agent = Agent(
        id=str(uuid4()),
        name=name,
        description=f"{name} agent",
        version="0.1.0",
        status=status,
    )
    agent.domain = domain  # type: ignore[attr-defined]
    agent.is_routable = is_routable  # type: ignore[attr-defined]
    agent.intent_patterns = intent_patterns or []  # type: ignore[attr-defined]
    agent.capabilities = capabilities or []  # type: ignore[attr-defined]
    agent.created_at = datetime.now(UTC)
    agent.updated_at = datetime.now(UTC)
    return agent


class TestAvailableAgentsEndpoint:
    """GET /api/v1/agents/available returns routable agents."""

    @pytest.mark.asyncio()
    async def test_returns_only_routable_agents(self, client):
        routable = _make_agent(
            "architect",
            domain="home",
            is_routable=True,
            intent_patterns=["home_automation"],
            capabilities=["control_devices"],
        )
        non_routable = _make_agent("developer", domain=None, is_routable=False)

        mock_list = AsyncMock(return_value=[routable, non_routable])

        with patch("src.api.routes.agents.core.get_session") as mock_session:
            mock_session.return_value = _mock_session_ctx()
            with patch("src.api.routes.agents.core.AgentRepository") as mock_repo_cls:
                mock_repo_cls.return_value.list_all = mock_list
                resp = await client.get("/api/v1/agents/available")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["agents"]) == 1
        assert data["agents"][0]["name"] == "architect"

    @pytest.mark.asyncio()
    async def test_includes_routing_metadata(self, client):
        agent = _make_agent(
            "architect",
            domain="home",
            is_routable=True,
            intent_patterns=["home_automation", "device_control"],
            capabilities=["control_devices", "create_automations"],
        )

        mock_list = AsyncMock(return_value=[agent])

        with patch("src.api.routes.agents.core.get_session") as mock_session:
            mock_session.return_value = _mock_session_ctx()
            with patch("src.api.routes.agents.core.AgentRepository") as mock_repo_cls:
                mock_repo_cls.return_value.list_all = mock_list
                resp = await client.get("/api/v1/agents/available")

        assert resp.status_code == 200
        agent_data = resp.json()["agents"][0]
        assert agent_data["domain"] == "home"
        assert agent_data["is_routable"] is True
        assert "home_automation" in agent_data["intent_patterns"]
        assert "control_devices" in agent_data["capabilities"]

    @pytest.mark.asyncio()
    async def test_excludes_disabled_agents(self, client):
        disabled = _make_agent(
            "knowledge",
            domain="knowledge",
            is_routable=True,
            status=AgentStatus.DISABLED.value,
        )

        mock_list = AsyncMock(return_value=[disabled])

        with patch("src.api.routes.agents.core.get_session") as mock_session:
            mock_session.return_value = _mock_session_ctx()
            with patch("src.api.routes.agents.core.AgentRepository") as mock_repo_cls:
                mock_repo_cls.return_value.list_all = mock_list
                resp = await client.get("/api/v1/agents/available")

        assert resp.status_code == 200
        assert len(resp.json()["agents"]) == 0

    @pytest.mark.asyncio()
    async def test_empty_when_no_routable_agents(self, client):
        mock_list = AsyncMock(return_value=[])

        with patch("src.api.routes.agents.core.get_session") as mock_session:
            mock_session.return_value = _mock_session_ctx()
            with patch("src.api.routes.agents.core.AgentRepository") as mock_repo_cls:
                mock_repo_cls.return_value.list_all = mock_list
                resp = await client.get("/api/v1/agents/available")

        assert resp.status_code == 200
        data = resp.json()
        assert data["agents"] == []
        assert data["total"] == 0


def _mock_session_ctx():
    """Create an async context manager mock for get_session()."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _ctx():
        yield AsyncMock()

    return _ctx()
