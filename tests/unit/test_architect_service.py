"""Tests for Architect A2A service entrypoint (Phase 4)."""

from __future__ import annotations

import pytest


class TestCreateArchitectService:
    """create_architect_service() produces a working app."""

    def test_returns_starlette_app(self):
        from starlette.applications import Starlette

        from src.services.architect import create_architect_service

        app = create_architect_service()
        assert isinstance(app, Starlette)

    def test_has_health_endpoint(self):
        from src.services.architect import create_architect_service

        app = create_architect_service()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/health" in routes

    def test_has_agent_card_endpoint(self):
        from src.services.architect import create_architect_service

        app = create_architect_service()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/.well-known/agent-card.json" in routes

    @pytest.mark.asyncio()
    async def test_agent_card_has_architect_skills(self):
        from httpx import ASGITransport, AsyncClient

        from src.services.architect import create_architect_service

        app = create_architect_service()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/.well-known/agent-card.json")
            card = resp.json()
            skill_ids = [s["id"] for s in card["skills"]]
            assert "automation_design" in skill_ids
            assert "entity_queries" in skill_ids
