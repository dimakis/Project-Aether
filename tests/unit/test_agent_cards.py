"""Tests for A2A Agent Card generation and serving (Feature 30).

An Agent Card is a JSON document per the A2A protocol spec that
describes an agent's identity, skills, and endpoint.  In monolith
mode, the card is served at /.well-known/agent.json and aggregates
all routable agents as skills.
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

    from src.api.routes.agent_card import router as card_router

    app = FastAPI()
    app.include_router(card_router)
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
    is_routable: bool = True,
    intent_patterns: list[str] | None = None,
    capabilities: list[str] | None = None,
) -> Agent:
    agent = Agent(
        id=str(uuid4()),
        name=name,
        description=f"{name} agent",
        version="0.1.0",
        status=AgentStatus.ENABLED.value,
    )
    agent.domain = domain  # type: ignore[attr-defined]
    agent.is_routable = is_routable  # type: ignore[attr-defined]
    agent.intent_patterns = intent_patterns or []  # type: ignore[attr-defined]
    agent.capabilities = capabilities or []  # type: ignore[attr-defined]
    agent.created_at = datetime.now(UTC)
    agent.updated_at = datetime.now(UTC)
    return agent


class TestAgentCardEndpoint:
    """GET /.well-known/agent.json returns a valid A2A Agent Card."""

    @pytest.mark.asyncio()
    async def test_returns_valid_agent_card(self, client):
        agents = [
            _make_agent(
                "architect",
                domain="home",
                intent_patterns=["home_automation"],
                capabilities=["control_devices"],
            ),
        ]

        with patch(
            "src.api.routes.agent_card._fetch_routable_agents",
            new_callable=AsyncMock,
            return_value=agents,
        ):
            resp = await client.get("/.well-known/agent.json")

        assert resp.status_code == 200
        card = resp.json()
        assert card["name"] == "Aether"
        assert "skills" in card
        assert "url" in card

    @pytest.mark.asyncio()
    async def test_skills_derived_from_routable_agents(self, client):
        agents = [
            _make_agent("architect", domain="home", capabilities=["control_devices"]),
            _make_agent("knowledge", domain="knowledge", capabilities=["answer_questions"]),
        ]

        with patch(
            "src.api.routes.agent_card._fetch_routable_agents",
            new_callable=AsyncMock,
            return_value=agents,
        ):
            resp = await client.get("/.well-known/agent.json")

        card = resp.json()
        skill_ids = [s["id"] for s in card["skills"]]
        assert "architect" in skill_ids
        assert "knowledge" in skill_ids

    @pytest.mark.asyncio()
    async def test_skill_has_required_a2a_fields(self, client):
        agents = [
            _make_agent(
                "architect",
                domain="home",
                intent_patterns=["home_automation"],
                capabilities=["control_devices"],
            ),
        ]

        with patch(
            "src.api.routes.agent_card._fetch_routable_agents",
            new_callable=AsyncMock,
            return_value=agents,
        ):
            resp = await client.get("/.well-known/agent.json")

        skill = resp.json()["skills"][0]
        assert "id" in skill
        assert "name" in skill
        assert "description" in skill
        assert "inputModes" in skill
        assert "outputModes" in skill

    @pytest.mark.asyncio()
    async def test_empty_skills_when_no_routable_agents(self, client):
        with patch(
            "src.api.routes.agent_card._fetch_routable_agents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get("/.well-known/agent.json")

        assert resp.status_code == 200
        assert resp.json()["skills"] == []

    @pytest.mark.asyncio()
    async def test_card_has_a2a_version(self, client):
        with patch(
            "src.api.routes.agent_card._fetch_routable_agents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get("/.well-known/agent.json")

        card = resp.json()
        assert "version" in card
