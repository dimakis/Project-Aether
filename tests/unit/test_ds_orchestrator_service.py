"""Tests for DS Orchestrator A2A service entrypoint (Phase 4).

The DS Orchestrator wraps DataScientistAgent as a single-agent
container that coordinates the DS Analysts.
"""

from __future__ import annotations

import pytest


class TestCreateDsOrchestratorService:
    """create_ds_orchestrator_service() produces a working app."""

    def test_returns_starlette_app(self):
        from starlette.applications import Starlette

        from src.services.ds_orchestrator import create_ds_orchestrator_service

        app = create_ds_orchestrator_service()
        assert isinstance(app, Starlette)

    def test_has_health_endpoint(self):
        from src.services.ds_orchestrator import create_ds_orchestrator_service

        app = create_ds_orchestrator_service()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/health" in routes

    def test_has_agent_card_endpoint(self):
        from src.services.ds_orchestrator import create_ds_orchestrator_service

        app = create_ds_orchestrator_service()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/.well-known/agent-card.json" in routes

    @pytest.mark.asyncio()
    async def test_agent_card_has_orchestration_skills(self):
        from httpx import ASGITransport, AsyncClient

        from src.services.ds_orchestrator import create_ds_orchestrator_service

        app = create_ds_orchestrator_service()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/.well-known/agent-card.json")
            card = resp.json()
            skill_ids = [s["id"] for s in card["skills"]]
            assert "team_analysis" in skill_ids
            assert "synthesis" in skill_ids
