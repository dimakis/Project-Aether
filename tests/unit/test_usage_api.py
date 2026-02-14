"""Unit tests for the LLM usage API routes.

Tests the /api/v1/usage/* endpoints with mocked repository.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.settings import get_settings
from tests.helpers.auth import make_test_jwt, make_test_settings


@pytest.fixture
async def usage_client(monkeypatch):
    """Test client with auth configured."""
    get_settings.cache_clear()
    settings = make_test_settings()
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    get_settings.cache_clear()


MOCK_SUMMARY = {
    "period_days": 7,
    "total_calls": 42,
    "total_input_tokens": 50000,
    "total_output_tokens": 25000,
    "total_tokens": 75000,
    "total_cost_usd": 0.3750,
    "by_model": [
        {
            "model": "gpt-4o",
            "provider": "openai",
            "calls": 30,
            "tokens": 60000,
            "cost_usd": 0.30,
        },
        {
            "model": "gpt-4o-mini",
            "provider": "openai",
            "calls": 12,
            "tokens": 15000,
            "cost_usd": 0.075,
        },
    ],
}

MOCK_DAILY = [
    {"date": "2026-02-01T00:00:00+00:00", "calls": 10, "tokens": 15000, "cost_usd": 0.10},
    {"date": "2026-02-02T00:00:00+00:00", "calls": 15, "tokens": 25000, "cost_usd": 0.15},
]

MOCK_MODELS = [
    {
        "model": "gpt-4o",
        "provider": "openai",
        "calls": 30,
        "input_tokens": 40000,
        "output_tokens": 20000,
        "tokens": 60000,
        "cost_usd": 0.30,
        "avg_latency_ms": 850,
    },
]


@pytest.mark.asyncio
class TestUsageSummary:
    """Test GET /api/v1/usage/summary."""

    async def test_requires_auth(self, usage_client: AsyncClient):
        """Usage summary requires authentication."""
        response = await usage_client.get("/api/v1/usage/summary")
        assert response.status_code == 401

    async def test_returns_summary(self, usage_client: AsyncClient):
        """Returns usage summary with valid JWT."""
        token = make_test_jwt()
        mock_repo = AsyncMock()
        mock_repo.get_summary = AsyncMock(return_value=MOCK_SUMMARY)

        with patch("src.api.routes.usage.get_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            with patch("src.api.routes.usage.LLMUsageRepository", return_value=mock_repo):
                response = await usage_client.get(
                    "/api/v1/usage/summary?days=7",
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 42
        assert data["total_cost_usd"] == 0.375
        assert len(data["by_model"]) == 2


@pytest.mark.asyncio
class TestDailyUsage:
    """Test GET /api/v1/usage/daily."""

    async def test_requires_auth(self, usage_client: AsyncClient):
        """Daily usage requires authentication."""
        response = await usage_client.get("/api/v1/usage/daily")
        assert response.status_code == 401

    async def test_returns_daily_data(self, usage_client: AsyncClient):
        """Returns daily breakdown with valid JWT."""
        token = make_test_jwt()
        mock_repo = AsyncMock()
        mock_repo.get_daily = AsyncMock(return_value=MOCK_DAILY)

        with patch("src.api.routes.usage.get_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            with patch("src.api.routes.usage.LLMUsageRepository", return_value=mock_repo):
                response = await usage_client.get(
                    "/api/v1/usage/daily?days=7",
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 7
        assert len(data["data"]) == 2


@pytest.mark.asyncio
class TestUsageByModel:
    """Test GET /api/v1/usage/models."""

    async def test_requires_auth(self, usage_client: AsyncClient):
        """Model usage requires authentication."""
        response = await usage_client.get("/api/v1/usage/models")
        assert response.status_code == 401

    async def test_returns_model_data(self, usage_client: AsyncClient):
        """Returns per-model breakdown with valid JWT."""
        token = make_test_jwt()
        mock_repo = AsyncMock()
        mock_repo.get_by_model = AsyncMock(return_value=MOCK_MODELS)

        with patch("src.api.routes.usage.get_session") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            with patch("src.api.routes.usage.LLMUsageRepository", return_value=mock_repo):
                response = await usage_client.get(
                    "/api/v1/usage/models?days=7",
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 7
        assert len(data["models"]) == 1
        assert data["models"][0]["model"] == "gpt-4o"
