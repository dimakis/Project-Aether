"""Unit tests for Insights API routes.

Tests GET/POST endpoints for insights with mock repositories --
no real database or app lifespan needed.

The get_session dependency is patched at the import site so
the test never attempts a real Postgres connection.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.storage.entities.insight import InsightStatus, InsightType


def _make_test_app(mock_session):
    """Create a minimal FastAPI app with the insights router and mock DB."""
    from fastapi import FastAPI
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    from src.api.deps import get_db
    from src.api.rate_limit import limiter
    from src.api.routes.insights import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Attach rate limiter and error handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Override get_db so routes never call get_session() (unit-test DB guard)
    async def _mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_get_db

    return app


@pytest.fixture
def insights_app(mock_session):
    """Lightweight FastAPI app with insights routes and mocked DB."""
    return _make_test_app(mock_session)


@pytest.fixture
async def insights_client(insights_app):
    """Async HTTP client wired to the insights test app."""
    async with AsyncClient(
        transport=ASGITransport(app=insights_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_insight():
    """Create a mock Insight object."""
    insight = MagicMock()
    insight.id = "insight-1"
    insight.type = InsightType.ENERGY_OPTIMIZATION
    insight.title = "Test Insight"
    insight.description = "Test description"
    insight.evidence = {"data": "test"}
    insight.confidence = 0.85
    insight.impact = "high"
    insight.entities = ["sensor.temperature"]
    insight.script_path = None
    insight.script_output = None
    insight.status = InsightStatus.PENDING
    insight.mlflow_run_id = None
    insight.conversation_id = None
    insight.task_label = None
    insight.created_at = datetime.now(UTC)
    insight.reviewed_at = None
    insight.actioned_at = None
    return insight


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_insight_repo(mock_insight):
    """Create mock InsightRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_insight])
    repo.list_by_type = AsyncMock(return_value=[mock_insight])
    repo.list_by_status = AsyncMock(return_value=[mock_insight])
    repo.list_pending = AsyncMock(return_value=[mock_insight])
    repo.list_by_impact = AsyncMock(return_value=[mock_insight])
    repo.get_by_id = AsyncMock(return_value=mock_insight)
    repo.create = AsyncMock(return_value=mock_insight)
    repo.mark_reviewed = AsyncMock(return_value=mock_insight)
    repo.mark_actioned = AsyncMock(return_value=mock_insight)
    repo.dismiss = AsyncMock(return_value=mock_insight)
    repo.delete = AsyncMock(return_value=True)
    repo.count = AsyncMock(return_value=1)
    repo.count_by_type = AsyncMock(return_value={"energy_optimization": 1})
    repo.count_by_status = AsyncMock(return_value={"pending": 1})
    repo.get_summary = AsyncMock(
        return_value={
            "total": 1,
            "by_type": {"energy_optimization": 1},
            "by_status": {"pending": 1},
            "pending_count": 1,
            "high_impact_count": 0,
        }
    )
    return repo


@pytest.mark.asyncio
class TestListInsights:
    """Tests for GET /api/v1/insights."""

    async def test_list_insights_success(
        self, insights_client, mock_insight_repo, mock_insight, mock_session
    ):
        """Should return paginated insights."""

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.get("/api/v1/insights")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["id"] == "insight-1"
            assert data["items"][0]["type"] == "energy_optimization"

    async def test_list_insights_with_type_filter(
        self, insights_client, mock_insight_repo, mock_session
    ):
        """Should filter insights by type."""

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.get("/api/v1/insights?type=energy_optimization")

            assert response.status_code == 200
            mock_insight_repo.list_by_type.assert_called_once()

    async def test_list_insights_with_status_filter(
        self, insights_client, mock_insight_repo, mock_session
    ):
        """Should filter insights by status."""

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.get("/api/v1/insights?status=pending")

            assert response.status_code == 200
            mock_insight_repo.list_by_status.assert_called_once()

    async def test_list_insights_with_pagination(
        self, insights_client, mock_insight_repo, mock_session
    ):
        """Should support pagination."""

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.get("/api/v1/insights?limit=10&offset=5")

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 5

    async def test_list_insights_empty(self, insights_client, mock_session):
        """Should return empty list when no insights exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with patch("src.api.routes.insights.InsightRepository", return_value=repo):
            response = await insights_client.get("/api/v1/insights")

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["total"] == 0


@pytest.mark.asyncio
class TestListPendingInsights:
    """Tests for GET /api/v1/insights/pending."""

    async def test_list_pending_insights_success(
        self, insights_client, mock_insight_repo, mock_session
    ):
        """Should return pending insights."""

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.get("/api/v1/insights/pending")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            mock_insight_repo.list_pending.assert_called_once()


@pytest.mark.asyncio
class TestGetInsightsSummary:
    """Tests for GET /api/v1/insights/summary."""

    async def test_get_insights_summary_success(self, insights_client, mock_insight_repo):
        """Should return insights summary with counts."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.get("/api/v1/insights/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_type" in data
        assert "by_status" in data
        assert "pending_count" in data
        assert "high_impact_count" in data


@pytest.mark.asyncio
class TestGetInsight:
    """Tests for GET /api/v1/insights/{insight_id}."""

    async def test_get_insight_success(
        self, insights_client, mock_insight_repo, mock_insight, mock_session
    ):
        """Should return insight by ID."""

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.get("/api/v1/insights/insight-1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "insight-1"
            assert data["title"] == "Test Insight"
            mock_insight_repo.get_by_id.assert_called_once_with("insight-1")

    async def test_get_insight_not_found(self, insights_client, mock_insight_repo, mock_session):
        """Should return 404 when insight not found."""
        mock_insight_repo.get_by_id = AsyncMock(return_value=None)

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.get("/api/v1/insights/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestCreateInsight:
    """Tests for POST /api/v1/insights."""

    async def test_create_insight_success(
        self, insights_client, mock_insight_repo, mock_insight, mock_session
    ):
        """Should create a new insight."""

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.post(
                "/api/v1/insights",
                json={
                    "type": "energy_optimization",
                    "title": "New Insight",
                    "description": "New description",
                    "evidence": {},
                    "confidence": 0.9,
                    "impact": "high",
                    "entities": [],
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "insight-1"
            mock_insight_repo.create.assert_called_once()
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
class TestReviewInsight:
    """Tests for POST /api/v1/insights/{insight_id}/review."""

    async def test_review_insight_success(
        self, insights_client, mock_insight_repo, mock_insight, mock_session
    ):
        """Should mark insight as reviewed."""
        mock_insight.status = InsightStatus.REVIEWED
        mock_insight.reviewed_at = datetime.now(UTC)

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.post(
                "/api/v1/insights/insight-1/review",
                json={"notes": "Reviewed"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "reviewed"
            mock_insight_repo.mark_reviewed.assert_called_once_with("insight-1")
            mock_session.commit.assert_called_once()

    async def test_review_insight_not_found(self, insights_client, mock_insight_repo, mock_session):
        """Should return 404 when insight not found."""
        mock_insight_repo.mark_reviewed = AsyncMock(return_value=None)

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.post(
                "/api/v1/insights/nonexistent/review",
                json={"notes": "Reviewed"},
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestActionInsight:
    """Tests for POST /api/v1/insights/{insight_id}/action."""

    async def test_action_insight_success(
        self, insights_client, mock_insight_repo, mock_insight, mock_session
    ):
        """Should mark insight as actioned."""
        mock_insight.status = InsightStatus.ACTIONED
        mock_insight.actioned_at = datetime.now(UTC)

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.post(
                "/api/v1/insights/insight-1/action",
                json={"action_taken": "Implemented"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "actioned"
            mock_insight_repo.mark_actioned.assert_called_once_with("insight-1")
            mock_session.commit.assert_called_once()

    async def test_action_insight_not_found(self, insights_client, mock_insight_repo, mock_session):
        """Should return 404 when insight not found."""
        mock_insight_repo.mark_actioned = AsyncMock(return_value=None)

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.post(
                "/api/v1/insights/nonexistent/action",
                json={"action_taken": "Implemented"},
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestDismissInsight:
    """Tests for POST /api/v1/insights/{insight_id}/dismiss."""

    async def test_dismiss_insight_success(
        self, insights_client, mock_insight_repo, mock_insight, mock_session
    ):
        """Should dismiss an insight."""
        mock_insight.status = InsightStatus.DISMISSED

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.post(
                "/api/v1/insights/insight-1/dismiss",
                json={"reason": "Not relevant"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "dismissed"
            mock_insight_repo.dismiss.assert_called_once_with("insight-1")
            mock_session.commit.assert_called_once()

    async def test_dismiss_insight_not_found(
        self, insights_client, mock_insight_repo, mock_session
    ):
        """Should return 404 when insight not found."""
        mock_insight_repo.dismiss = AsyncMock(return_value=None)

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.post(
                "/api/v1/insights/nonexistent/dismiss",
                json={"reason": "Not relevant"},
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteInsight:
    """Tests for DELETE /api/v1/insights/{insight_id}."""

    async def test_delete_insight_success(self, insights_client, mock_insight_repo, mock_session):
        """Should delete an insight."""

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.delete("/api/v1/insights/insight-1")

            assert response.status_code == 204
            mock_insight_repo.delete.assert_called_once_with("insight-1")
            mock_session.commit.assert_called_once()

    async def test_delete_insight_not_found(self, insights_client, mock_insight_repo, mock_session):
        """Should return 404 when insight not found."""
        mock_insight_repo.delete = AsyncMock(return_value=False)

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await insights_client.delete("/api/v1/insights/nonexistent")

            assert response.status_code == 404


@pytest.mark.asyncio
class TestStartAnalysis:
    """Tests for POST /api/v1/insights/analyze."""

    async def test_start_analysis_success(self, insights_client):
        """Should start an analysis job and return job ID."""
        response = await insights_client.post(
            "/api/v1/insights/analyze",
            json={
                "analysis_type": "energy_optimization",
                "entity_ids": ["sensor.temperature"],
                "hours": 24,
                "options": {},
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["analysis_type"] == "energy_optimization"
