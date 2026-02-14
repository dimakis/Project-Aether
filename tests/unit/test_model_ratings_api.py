"""Unit tests for the model ratings API routes.

Tests the /api/v1/models/* endpoints.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from src.api.main import create_app
from src.settings import get_settings
from tests.helpers.auth import make_test_jwt, make_test_settings

@pytest.fixture
async def client(monkeypatch):
    """Test client with auth configured."""
    get_settings.cache_clear()
    settings = make_test_settings()
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    get_settings.cache_clear()


def _mock_rating(
    id_val="r1",
    model_name="gpt-4o",
    agent_role="architect",
    rating=4,
    notes="Good",
    config_snapshot=None,
):
    """Create a mock ModelRating object."""
    now = datetime.now(UTC)
    m = MagicMock()
    m.id = id_val
    m.model_name = model_name
    m.agent_role = agent_role
    m.rating = rating
    m.notes = notes
    m.config_snapshot = config_snapshot or {"temperature": 0.7}
    m.created_at = now
    m.updated_at = now
    return m


# =============================================================================
# Schema validation tests
# =============================================================================


class TestModelRatingSchemas:
    """Test Pydantic schema validation."""

    def test_create_valid(self):
        from src.api.routes.model_ratings import ModelRatingCreate

        body = ModelRatingCreate(
            model_name="gpt-4o",
            agent_role="architect",
            rating=4,
            notes="Solid model",
            config_snapshot={"temperature": 0.7},
        )
        assert body.rating == 4

    def test_create_rejects_rating_below_1(self):
        from src.api.routes.model_ratings import ModelRatingCreate

        with pytest.raises(ValidationError):
            ModelRatingCreate(
                model_name="gpt-4o",
                agent_role="architect",
                rating=0,
            )

    def test_create_rejects_rating_above_5(self):
        from src.api.routes.model_ratings import ModelRatingCreate

        with pytest.raises(ValidationError):
            ModelRatingCreate(
                model_name="gpt-4o",
                agent_role="architect",
                rating=6,
            )

    def test_create_optional_fields(self):
        from src.api.routes.model_ratings import ModelRatingCreate

        body = ModelRatingCreate(
            model_name="gpt-4o",
            agent_role="architect",
            rating=3,
        )
        assert body.notes is None
        assert body.config_snapshot is None


# =============================================================================
# API endpoint tests
# =============================================================================


@pytest.mark.asyncio
class TestListRatings:
    """Test GET /api/v1/models/ratings."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/models/ratings")
        assert response.status_code == 401

    async def test_returns_ratings(self, client: AsyncClient):
        token = make_test_jwt()
        mock_r1 = _mock_rating(id_val="r1", model_name="gpt-4o", rating=4)
        mock_r2 = _mock_rating(id_val="r2", model_name="gemini-2.0-flash", rating=5)

        mock_session = AsyncMock()
        # Count query
        count_result = MagicMock()
        count_result.scalar.return_value = 2
        # List query
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [mock_r1, mock_r2]
        mock_session.execute = AsyncMock(side_effect=[count_result, list_result])

        with patch("src.api.routes.model_ratings.get_session") as mock_gs:
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            response = await client.get(
                "/api/v1/models/ratings",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["model_name"] == "gpt-4o"
        assert data["items"][1]["model_name"] == "gemini-2.0-flash"


@pytest.mark.asyncio
class TestCreateRating:
    """Test POST /api/v1/models/ratings."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/models/ratings",
            json={"model_name": "x", "agent_role": "y", "rating": 3},
        )
        assert response.status_code == 401

    async def test_creates_rating(self, client: AsyncClient):
        token = make_test_jwt()
        now = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        async def fake_refresh(obj):
            obj.created_at = now
            obj.updated_at = now

        mock_session.refresh = AsyncMock(side_effect=fake_refresh)

        with patch("src.api.routes.model_ratings.get_session") as mock_gs:
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            response = await client.post(
                "/api/v1/models/ratings",
                json={
                    "model_name": "gpt-4o",
                    "agent_role": "architect",
                    "rating": 5,
                    "notes": "Excellent",
                    "config_snapshot": {"temperature": 0.7},
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["model_name"] == "gpt-4o"
        assert data["agent_role"] == "architect"
        assert data["rating"] == 5
        assert data["notes"] == "Excellent"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    async def test_rejects_invalid_rating(self, client: AsyncClient):
        token = make_test_jwt()
        response = await client.post(
            "/api/v1/models/ratings",
            json={
                "model_name": "gpt-4o",
                "agent_role": "architect",
                "rating": 0,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestModelSummary:
    """Test GET /api/v1/models/summary."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/models/summary")
        assert response.status_code == 401

    async def test_returns_summary(self, client: AsyncClient):
        token = make_test_jwt()

        # Aggregation result row
        agg_row = MagicMock()
        agg_row.model_name = "gpt-4o"
        agg_row.agent_role = "architect"
        agg_row.avg_rating = 4.5
        agg_row.rating_count = 10

        mock_session = AsyncMock()
        # First execute: aggregation query
        agg_result = MagicMock()
        agg_result.all.return_value = [agg_row]
        # Second execute: latest config
        config_result = MagicMock()
        config_result.scalar_one_or_none.return_value = {"temperature": 0.7}

        mock_session.execute = AsyncMock(side_effect=[agg_result, config_result])

        with patch("src.api.routes.model_ratings.get_session") as mock_gs:
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            response = await client.get(
                "/api/v1/models/summary",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_name"] == "gpt-4o"
        assert data[0]["avg_rating"] == 4.5
        assert data[0]["rating_count"] == 10
        assert data[0]["latest_config"] == {"temperature": 0.7}
