"""Tests for Developer A2A service entrypoint (Phase 5)."""

from __future__ import annotations

import pytest


class TestCreateDeveloperService:
    def test_returns_starlette_app(self):
        from starlette.applications import Starlette

        from src.services.developer import create_developer_service

        app = create_developer_service()
        assert isinstance(app, Starlette)

    def test_has_health_endpoint(self):
        from src.services.developer import create_developer_service

        routes = [r.path for r in create_developer_service().routes if hasattr(r, "path")]
        assert "/health" in routes

    @pytest.mark.asyncio()
    async def test_agent_card_has_skills(self):
        from httpx import ASGITransport, AsyncClient

        from src.services.developer import create_developer_service

        async with AsyncClient(
            transport=ASGITransport(app=create_developer_service()), base_url="http://test"
        ) as client:
            card = (await client.get("/.well-known/agent-card.json")).json()
            skill_ids = [s["id"] for s in card["skills"]]
            assert "automation_deployment" in skill_ids
            assert "rollback" in skill_ids
