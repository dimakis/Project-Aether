"""Unit tests for Optimization API routes.

Tests optimization endpoints with mock repositories -- no real database
or app lifespan needed.

The get_session() function is called directly (not a FastAPI dependency),
so it must be patched at the source: "src.storage.get_session".
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.deps import get_db
from src.api.rate_limit import limiter


def _make_test_app():
    """Create a minimal FastAPI app with the optimization router and mock DB."""
    from fastapi import FastAPI

    from src.api.routes.optimization import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Configure rate limiter for tests (required by @limiter.limit decorators)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    return app


@pytest.fixture
def optimization_app():
    """Lightweight FastAPI app with optimization routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def optimization_client(optimization_app):
    """Async HTTP client wired to the optimization test app."""
    async with AsyncClient(
        transport=ASGITransport(app=optimization_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_get_session(mock_session):
    """Create a mock get_session async context manager (for background task)."""

    @asynccontextmanager
    async def _mock_get_session():
        yield mock_session

    return _mock_get_session


@pytest.fixture
def mock_get_db(mock_session):
    """Async generator that yields mock_session for get_db dependency."""

    async def _get_db():
        yield mock_session

    return _get_db


def _make_mock_job(**kwargs):
    """Build a mock OptimizationJob-like object for _job_to_result."""
    job = MagicMock()
    job.id = kwargs.get("id", "job-uuid-1")
    job.status = kwargs.get("status", "pending")
    job.analysis_types = kwargs.get("analysis_types", ["behavior_analysis"])
    job.hours_analyzed = kwargs.get("hours_analyzed", 168)
    job.insight_count = kwargs.get("insight_count", 0)
    job.suggestion_count = kwargs.get("suggestion_count", 0)
    job.recommendations = kwargs.get("recommendations", [])
    job.started_at = kwargs.get("started_at", datetime.now(UTC))
    job.created_at = kwargs.get("created_at", datetime.now(UTC))
    job.completed_at = kwargs.get("completed_at")
    job.error = kwargs.get("error")
    job.suggestions = kwargs.get("suggestions", [])
    return job


# Valid UUID for suggestion IDs (route validates UUID before DB)
SUGGESTION_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


def _make_mock_suggestion(**kwargs):
    """Build a mock AutomationSuggestionEntity-like object."""
    s = MagicMock()
    s.id = kwargs.get("id", SUGGESTION_ID)
    s.pattern = kwargs.get("pattern", "Power spike detected")
    s.entities = kwargs.get("entities", ["sensor.power"])
    s.proposed_trigger = kwargs.get("proposed_trigger", "sensor.power > 1000")
    s.proposed_action = kwargs.get("proposed_action", "Turn off devices")
    s.confidence = kwargs.get("confidence", 0.85)
    s.source_insight_type = kwargs.get("source_insight_type", "behavior_analysis")
    s.status = kwargs.get("status", "pending")
    s.created_at = kwargs.get("created_at", datetime.now(UTC))
    return s


@pytest.mark.asyncio
class TestStartOptimization:
    """Tests for POST /api/v1/optimize."""

    async def test_start_optimization_success(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
        mock_session,
    ):
        """Should start optimization job and return job ID."""
        mock_job = _make_mock_job(id="job-123", status="pending")
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_job)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with (
            patch("src.api.routes.optimization.OptimizationJobRepository", return_value=mock_repo),
            patch("src.api.routes.optimization._run_optimization_background"),
        ):
            response = await optimization_client.post(
                "/api/v1/optimize",
                json={
                    "analysis_types": ["behavior_analysis"],
                    "hours": 168,
                    "entity_ids": ["sensor.power"],
                },
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"
            assert data["analysis_types"] == ["behavior_analysis"]
            assert data["hours_analyzed"] == 168
            assert data["insight_count"] == 0
            assert data["suggestion_count"] == 0
            assert "started_at" in data
            mock_repo.create.assert_called_once()
            mock_session.commit.assert_called_once()
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_start_optimization_multiple_analysis_types(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should accept multiple analysis types."""
        mock_job = _make_mock_job(
            id="job-456",
            analysis_types=["behavior_analysis", "automation_analysis", "automation_gap_detection"],
            hours_analyzed=72,
        )
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_job)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with (
            patch("src.api.routes.optimization.OptimizationJobRepository", return_value=mock_repo),
            patch("src.api.routes.optimization._run_optimization_background"),
        ):
            response = await optimization_client.post(
                "/api/v1/optimize",
                json={
                    "analysis_types": [
                        "behavior_analysis",
                        "automation_analysis",
                        "automation_gap_detection",
                    ],
                    "hours": 72,
                },
            )
            assert response.status_code == 202
            data = response.json()
            assert len(data["analysis_types"]) == 3
            assert "behavior_analysis" in data["analysis_types"]
            assert "automation_analysis" in data["analysis_types"]
            assert "automation_gap_detection" in data["analysis_types"]
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_start_optimization_default_values(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should use default values when not provided."""
        mock_job = _make_mock_job(id="job-789")
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_job)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with (
            patch("src.api.routes.optimization.OptimizationJobRepository", return_value=mock_repo),
            patch("src.api.routes.optimization._run_optimization_background"),
        ):
            response = await optimization_client.post(
                "/api/v1/optimize",
                json={},
            )
            assert response.status_code == 202
            data = response.json()
            assert data["analysis_types"] == ["behavior_analysis"]
            assert data["hours_analyzed"] == 168  # Default
        optimization_app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
class TestGetOptimizationStatus:
    """Tests for GET /api/v1/optimize/{job_id}."""

    async def test_get_optimization_status_pending(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return pending job status."""
        mock_job = _make_mock_job(id="job-uuid-1", status="pending")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_job)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch("src.api.routes.optimization.OptimizationJobRepository", return_value=mock_repo):
            response = await optimization_client.get("/api/v1/optimize/job-uuid-1")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-uuid-1"
        assert data["status"] == "pending"
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_get_optimization_status_completed(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return completed job status."""
        mock_job = _make_mock_job(
            id="job-uuid-2",
            status="completed",
            insight_count=5,
            suggestion_count=2,
            completed_at=datetime.now(UTC),
            recommendations=["Recommendation 1"],
        )
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_job)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch("src.api.routes.optimization.OptimizationJobRepository", return_value=mock_repo):
            response = await optimization_client.get("/api/v1/optimize/job-uuid-2")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["insight_count"] == 5
        assert data["suggestion_count"] == 2
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_get_optimization_status_not_found(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return 404 when job not found."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch("src.api.routes.optimization.OptimizationJobRepository", return_value=mock_repo):
            response = await optimization_client.get("/api/v1/optimize/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        optimization_app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
class TestListSuggestions:
    """Tests for GET /api/v1/optimize/suggestions/list."""

    async def test_list_suggestions_empty(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return empty list when no suggestions."""
        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[])
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch(
            "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
        ):
            response = await optimization_client.get("/api/v1/optimize/suggestions/list")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_list_suggestions_with_items(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return list of suggestions."""
        mock_s = _make_mock_suggestion(
            id="suggestion-uuid-1",
            pattern="Power spike detected",
            proposed_action="Turn off non-essential devices",
        )
        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[mock_s])
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch(
            "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
        ):
            response = await optimization_client.get("/api/v1/optimize/suggestions/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "suggestion-uuid-1"
        assert data["items"][0]["pattern"] == "Power spike detected"
        assert data["items"][0]["status"] == "pending"
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_list_suggestions_multiple_statuses(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return suggestions with different statuses."""
        s1 = _make_mock_suggestion(id="s1", pattern="Pattern 1", status="pending")
        s2 = _make_mock_suggestion(
            id="s2",
            pattern="Pattern 2",
            status="accepted",
            source_insight_type="automation_analysis",
        )
        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[s1, s2])
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch(
            "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
        ):
            response = await optimization_client.get("/api/v1/optimize/suggestions/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        optimization_app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
class TestAcceptSuggestion:
    """Tests for POST /api/v1/optimize/suggestions/{suggestion_id}/accept."""

    async def test_accept_suggestion_success(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
        mock_session,
        mock_get_session,
    ):
        """Should return 202 and mark suggestion accepted; proposal is created in background."""
        mock_entity = _make_mock_suggestion(id=SUGGESTION_ID, status="pending")
        accepted_entity = _make_mock_suggestion(id=SUGGESTION_ID, status="accepted")
        mock_repo = MagicMock()
        # Request path: pending; background: accepted so proposal creation runs
        mock_repo.get_by_id = AsyncMock(side_effect=[mock_entity, accepted_entity])
        mock_repo.update_status = AsyncMock(return_value=True)
        # Use a dedicated session for background so request-path commit is asserted alone
        background_session = MagicMock()
        background_session.commit = AsyncMock()

        @asynccontextmanager
        async def fake_get_session():
            yield background_session

        optimization_app.dependency_overrides[get_db] = mock_get_db
        with (
            patch(
                "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
            ),
            patch("src.storage.get_session", fake_get_session),
            patch("src.agents.ArchitectAgent") as mock_architect_cls,
        ):
            mock_architect_cls.return_value.receive_suggestion = AsyncMock(return_value=None)
            response = await optimization_client.post(
                f"/api/v1/optimize/suggestions/{SUGGESTION_ID}/accept",
                json={"comment": "Looks good"},
            )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "message" in data
        assert "proposal" in data["message"].lower() or "ready" in data["message"].lower()
        mock_repo.update_status.assert_called_once_with(SUGGESTION_ID, "accepted")
        mock_session.commit.assert_called_once()
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_accept_suggestion_not_found(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return 404 when suggestion not found."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch(
            "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
        ):
            response = await optimization_client.post(
                "/api/v1/optimize/suggestions/nonexistent/accept",
                json={},
            )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_accept_suggestion_already_processed(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return 409 when suggestion already processed."""
        mock_entity = _make_mock_suggestion(id=SUGGESTION_ID, status="accepted")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_entity)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch(
            "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
        ):
            response = await optimization_client.post(
                f"/api/v1/optimize/suggestions/{SUGGESTION_ID}/accept",
                json={},
            )
        assert response.status_code == 409
        assert "already processed" in response.json()["detail"].lower()
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_accept_suggestion_returns_202(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
        mock_get_session,
    ):
        """Accept returns 202 immediately; proposal creation runs in background."""
        mock_entity = _make_mock_suggestion(id=SUGGESTION_ID, status="pending")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_entity)
        mock_repo.update_status = AsyncMock(return_value=True)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with (
            patch(
                "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
            ),
            patch("src.storage.get_session", mock_get_session),
        ):
            response = await optimization_client.post(
                f"/api/v1/optimize/suggestions/{SUGGESTION_ID}/accept",
                json={},
            )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        optimization_app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
class TestRejectSuggestion:
    """Tests for POST /api/v1/optimize/suggestions/{suggestion_id}/reject."""

    async def test_reject_suggestion_success(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
        mock_session,
    ):
        """Should reject suggestion."""
        mock_entity = _make_mock_suggestion(id=SUGGESTION_ID, status="pending")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_entity)
        mock_repo.update_status = AsyncMock(return_value=True)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch(
            "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
        ):
            response = await optimization_client.post(
                f"/api/v1/optimize/suggestions/{SUGGESTION_ID}/reject",
                json={"reason": "Not needed"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["reason"] == "Not needed"
        mock_repo.update_status.assert_called_once_with(SUGGESTION_ID, "rejected")
        mock_session.commit.assert_called_once()
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_reject_suggestion_not_found(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return 404 when suggestion not found."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch(
            "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
        ):
            response = await optimization_client.post(
                "/api/v1/optimize/suggestions/nonexistent/reject",
                json={"reason": "Not needed"},
            )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        optimization_app.dependency_overrides.pop(get_db, None)

    async def test_reject_suggestion_already_processed(
        self,
        optimization_app,
        optimization_client,
        mock_get_db,
    ):
        """Should return 409 when suggestion already processed."""
        mock_entity = _make_mock_suggestion(id=SUGGESTION_ID, status="rejected")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_entity)
        optimization_app.dependency_overrides[get_db] = mock_get_db
        with patch(
            "src.api.routes.optimization.AutomationSuggestionRepository", return_value=mock_repo
        ):
            response = await optimization_client.post(
                f"/api/v1/optimize/suggestions/{SUGGESTION_ID}/reject",
                json={"reason": "Not needed"},
            )
        assert response.status_code == 409
        assert "already processed" in response.json()["detail"].lower()
        optimization_app.dependency_overrides.pop(get_db, None)
