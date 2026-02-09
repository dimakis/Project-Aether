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
    """Create a mock get_session async context manager."""

    @asynccontextmanager
    async def _mock_get_session():
        yield mock_session

    return _mock_get_session


@pytest.fixture(autouse=True)
def clear_optimization_stores():
    """Clear in-memory stores before each test."""
    from src.api.routes.optimization import _optimization_jobs, _suggestions

    _optimization_jobs.clear()
    _suggestions.clear()
    yield
    _optimization_jobs.clear()
    _suggestions.clear()


@pytest.mark.asyncio
class TestStartOptimization:
    """Tests for POST /api/v1/optimize."""

    async def test_start_optimization_success(
        self,
        optimization_client,
        mock_get_session,
    ):
        """Should start optimization job and return job ID."""
        with (
            patch("src.storage.get_session", mock_get_session),
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
            # Background task should be queued (doesn't run in tests)

    async def test_start_optimization_multiple_analysis_types(
        self,
        optimization_client,
        mock_get_session,
    ):
        """Should accept multiple analysis types."""
        with (
            patch("src.storage.get_session", mock_get_session),
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

    async def test_start_optimization_default_values(
        self,
        optimization_client,
        mock_get_session,
    ):
        """Should use default values when not provided."""
        with (
            patch("src.storage.get_session", mock_get_session),
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


@pytest.mark.asyncio
class TestGetOptimizationStatus:
    """Tests for GET /api/v1/optimize/{job_id}."""

    async def test_get_optimization_status_pending(
        self,
        optimization_client,
        mock_get_session,
    ):
        """Should return pending job status."""
        from src.api.routes.optimization import _optimization_jobs
        from src.api.schemas.optimization import OptimizationResult

        job = OptimizationResult(
            job_id="job-uuid-1",
            status="pending",
            analysis_types=["behavior_analysis"],
            hours_analyzed=168,
            insight_count=0,
            suggestion_count=0,
            started_at=datetime.now(UTC),
        )
        _optimization_jobs["job-uuid-1"] = job

        response = await optimization_client.get("/api/v1/optimize/job-uuid-1")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-uuid-1"
        assert data["status"] == "pending"

    async def test_get_optimization_status_completed(
        self,
        optimization_client,
    ):
        """Should return completed job status."""
        from src.api.routes.optimization import _optimization_jobs
        from src.api.schemas.optimization import OptimizationResult

        job = OptimizationResult(
            job_id="job-uuid-2",
            status="completed",
            analysis_types=["behavior_analysis"],
            hours_analyzed=168,
            insight_count=5,
            suggestion_count=2,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            insights=[{"type": "pattern", "description": "Test"}],
            recommendations=["Recommendation 1"],
        )
        _optimization_jobs["job-uuid-2"] = job

        response = await optimization_client.get("/api/v1/optimize/job-uuid-2")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["insight_count"] == 5
        assert data["suggestion_count"] == 2

    async def test_get_optimization_status_not_found(
        self,
        optimization_client,
    ):
        """Should return 404 when job not found."""
        response = await optimization_client.get("/api/v1/optimize/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestListSuggestions:
    """Tests for GET /api/v1/optimize/suggestions/list."""

    async def test_list_suggestions_empty(
        self,
        optimization_client,
    ):
        """Should return empty list when no suggestions."""
        response = await optimization_client.get("/api/v1/optimize/suggestions/list")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_suggestions_with_items(
        self,
        optimization_client,
    ):
        """Should return list of suggestions."""
        from src.api.routes.optimization import _suggestions

        _suggestions["suggestion-uuid-1"] = {
            "pattern": "Power spike detected",
            "entities": ["sensor.power"],
            "proposed_trigger": "sensor.power > 1000",
            "proposed_action": "Turn off non-essential devices",
            "confidence": 0.85,
            "source_insight_type": "behavior_analysis",
            "status": "pending",
            "created_at": datetime.now(UTC),
        }

        response = await optimization_client.get("/api/v1/optimize/suggestions/list")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "suggestion-uuid-1"
        assert data["items"][0]["pattern"] == "Power spike detected"
        assert data["items"][0]["status"] == "pending"

    async def test_list_suggestions_multiple_statuses(
        self,
        optimization_client,
    ):
        """Should return suggestions with different statuses."""
        from src.api.routes.optimization import _suggestions

        _suggestions["suggestion-uuid-1"] = {
            "pattern": "Pattern 1",
            "entities": [],
            "proposed_trigger": "",
            "proposed_action": "",
            "confidence": 0.8,
            "source_insight_type": "behavior_analysis",
            "status": "pending",
            "created_at": datetime.now(UTC),
        }
        _suggestions["suggestion-uuid-2"] = {
            "pattern": "Pattern 2",
            "entities": [],
            "proposed_trigger": "",
            "proposed_action": "",
            "confidence": 0.7,
            "source_insight_type": "automation_analysis",
            "status": "accepted",
            "created_at": datetime.now(UTC),
        }

        response = await optimization_client.get("/api/v1/optimize/suggestions/list")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


@pytest.mark.asyncio
class TestAcceptSuggestion:
    """Tests for POST /api/v1/optimize/suggestions/{suggestion_id}/accept."""

    async def test_accept_suggestion_success(
        self,
        optimization_client,
        mock_get_session,
        mock_session,
    ):
        """Should accept suggestion and create proposal."""
        from src.api.routes.optimization import _suggestions

        _suggestions["suggestion-uuid-1"] = {
            "pattern": "Power spike detected",
            "entities": ["sensor.power"],
            "proposed_trigger": "sensor.power > 1000",
            "proposed_action": "Turn off devices",
            "confidence": 0.85,
            "evidence": {},
            "source_insight_type": "behavior_analysis",
            "status": "pending",
            "created_at": datetime.now(UTC),
        }

        mock_architect = MagicMock()
        mock_architect.receive_suggestion = AsyncMock(
            return_value={
                "proposal_id": "proposal-uuid-1",
                "proposal_name": "Power Management Automation",
            }
        )

        with (
            patch("src.storage.get_session", mock_get_session),
            patch("src.agents.ArchitectAgent", return_value=mock_architect),
        ):
            response = await optimization_client.post(
                "/api/v1/optimize/suggestions/suggestion-uuid-1/accept",
                json={"comment": "Looks good"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["proposal_id"] == "proposal-uuid-1"
            assert "Proposal created" in data["message"]
            assert _suggestions["suggestion-uuid-1"]["status"] == "accepted"
            mock_session.commit.assert_called_once()

    async def test_accept_suggestion_not_found(
        self,
        optimization_client,
        mock_get_session,
    ):
        """Should return 404 when suggestion not found."""
        with patch("src.storage.get_session", mock_get_session):
            response = await optimization_client.post(
                "/api/v1/optimize/suggestions/nonexistent/accept",
                json={},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    async def test_accept_suggestion_already_processed(
        self,
        optimization_client,
        mock_get_session,
    ):
        """Should return 409 when suggestion already processed."""
        from src.api.routes.optimization import _suggestions

        _suggestions["suggestion-uuid-1"] = {
            "pattern": "Pattern",
            "entities": [],
            "proposed_trigger": "",
            "proposed_action": "",
            "confidence": 0.8,
            "evidence": {},
            "source_insight_type": "behavior_analysis",
            "status": "accepted",
            "created_at": datetime.now(UTC),
        }

        with patch("src.storage.get_session", mock_get_session):
            response = await optimization_client.post(
                "/api/v1/optimize/suggestions/suggestion-uuid-1/accept",
                json={},
            )

            assert response.status_code == 409
            assert "already processed" in response.json()["detail"].lower()

    async def test_accept_suggestion_architect_error(
        self,
        optimization_client,
        mock_get_session,
        mock_session,
    ):
        """Should handle architect errors gracefully."""
        from src.api.routes.optimization import _suggestions

        _suggestions["suggestion-uuid-1"] = {
            "pattern": "Pattern",
            "entities": [],
            "proposed_trigger": "",
            "proposed_action": "",
            "confidence": 0.8,
            "evidence": {},
            "source_insight_type": "behavior_analysis",
            "status": "pending",
            "created_at": datetime.now(UTC),
        }

        mock_architect = MagicMock()
        mock_architect.receive_suggestion = AsyncMock(side_effect=Exception("Architect error"))

        with (
            patch("src.storage.get_session", mock_get_session),
            patch("src.agents.ArchitectAgent", return_value=mock_architect),
        ):
            response = await optimization_client.post(
                "/api/v1/optimize/suggestions/suggestion-uuid-1/accept",
                json={},
            )

            assert response.status_code == 500
            assert "error" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestRejectSuggestion:
    """Tests for POST /api/v1/optimize/suggestions/{suggestion_id}/reject."""

    async def test_reject_suggestion_success(
        self,
        optimization_client,
    ):
        """Should reject suggestion."""
        from src.api.routes.optimization import _suggestions

        _suggestions["suggestion-uuid-1"] = {
            "pattern": "Power spike detected",
            "entities": ["sensor.power"],
            "proposed_trigger": "",
            "proposed_action": "",
            "confidence": 0.85,
            "source_insight_type": "behavior_analysis",
            "status": "pending",
            "created_at": datetime.now(UTC),
        }

        response = await optimization_client.post(
            "/api/v1/optimize/suggestions/suggestion-uuid-1/reject",
            json={"reason": "Not needed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["reason"] == "Not needed"
        assert _suggestions["suggestion-uuid-1"]["status"] == "rejected"
        assert _suggestions["suggestion-uuid-1"]["rejection_reason"] == "Not needed"

    async def test_reject_suggestion_not_found(
        self,
        optimization_client,
    ):
        """Should return 404 when suggestion not found."""
        response = await optimization_client.post(
            "/api/v1/optimize/suggestions/nonexistent/reject",
            json={"reason": "Not needed"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_reject_suggestion_already_processed(
        self,
        optimization_client,
    ):
        """Should return 409 when suggestion already processed."""
        from src.api.routes.optimization import _suggestions

        _suggestions["suggestion-uuid-1"] = {
            "pattern": "Pattern",
            "entities": [],
            "proposed_trigger": "",
            "proposed_action": "",
            "confidence": 0.8,
            "source_insight_type": "behavior_analysis",
            "status": "rejected",
            "created_at": datetime.now(UTC),
        }

        response = await optimization_client.post(
            "/api/v1/optimize/suggestions/suggestion-uuid-1/reject",
            json={"reason": "Not needed"},
        )

        assert response.status_code == 409
        assert "already processed" in response.json()["detail"].lower()
