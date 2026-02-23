"""Tests for DS Analysts A2A service entrypoint (Phase 4).

The DS Analysts service wraps Energy, Behavioral, and Diagnostic
analysts into a single A2A-compliant container.
"""

from __future__ import annotations

import pytest


class TestCreateDsAnalystsService:
    """create_ds_analysts_service() produces a working app."""

    def test_returns_starlette_app(self):
        from starlette.applications import Starlette

        from src.services.ds_analysts import create_ds_analysts_service

        app = create_ds_analysts_service()
        assert isinstance(app, Starlette)

    def test_has_health_endpoint(self):
        from src.services.ds_analysts import create_ds_analysts_service

        app = create_ds_analysts_service()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/health" in routes

    def test_has_agent_card_endpoint(self):
        from src.services.ds_analysts import create_ds_analysts_service

        app = create_ds_analysts_service()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/.well-known/agent-card.json" in routes

    @pytest.mark.asyncio()
    async def test_agent_card_has_three_skills(self):
        from httpx import ASGITransport, AsyncClient

        from src.services.ds_analysts import create_ds_analysts_service

        app = create_ds_analysts_service()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/.well-known/agent-card.json")
            card = resp.json()
            skill_ids = [s["id"] for s in card["skills"]]
            assert "energy_analysis" in skill_ids
            assert "behavioral_analysis" in skill_ids
            assert "diagnostic_analysis" in skill_ids
