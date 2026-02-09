"""Unit tests for Flow Grades API routes.

Tests flow grade endpoints with mock repositories -- no real database
or app lifespan needed.

The get_session() function is called directly (not a FastAPI dependency),
so it must be patched at the source: "src.api.routes.flow_grades.get_session".
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _make_test_app():
    """Create a minimal FastAPI app with the flow grades router."""
    from fastapi import FastAPI

    from src.api.routes.flow_grades import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    return app


@pytest.fixture
def flow_grades_app():
    """Lightweight FastAPI app with flow grades routes."""
    return _make_test_app()


@pytest.fixture
async def flow_grades_client(flow_grades_app):
    """Async HTTP client wired to the flow grades test app."""
    async with AsyncClient(
        transport=ASGITransport(app=flow_grades_app),
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


@pytest.fixture
def mock_flow_grade():
    """Create a mock FlowGrade object."""
    grade = MagicMock()
    grade.id = "grade-uuid-1"
    grade.conversation_id = "conv-uuid-1"
    grade.span_id = "span-uuid-1"
    grade.grade = 1
    grade.comment = "Great response!"
    grade.agent_role = "architect"
    grade.created_at = datetime.now(UTC)
    return grade


@pytest.fixture
def mock_flow_grade_repo(mock_flow_grade):
    """Create mock FlowGradeRepository."""
    repo = MagicMock()
    repo.upsert = AsyncMock(return_value=mock_flow_grade)
    repo.get_summary = AsyncMock(
        return_value={
            "conversation_id": "conv-uuid-1",
            "overall": {
                "id": "grade-uuid-1",
                "span_id": None,
                "grade": 1,
                "comment": "Overall great",
                "agent_role": None,
                "created_at": datetime.now(UTC).isoformat(),
            },
            "steps": [
                {
                    "id": "grade-uuid-2",
                    "span_id": "span-uuid-1",
                    "grade": 1,
                    "comment": "Step 1",
                    "agent_role": "architect",
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ],
            "total_grades": 2,
            "thumbs_up": 2,
            "thumbs_down": 0,
        }
    )
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.mark.asyncio
class TestSubmitGrade:
    """Tests for POST /api/v1/flow-grades."""

    async def test_submit_grade_success(
        self, flow_grades_client, mock_get_session, mock_flow_grade_repo, mock_flow_grade
    ):
        """Should create a new grade and return it."""
        with (
            patch("src.api.routes.flow_grades.get_session", mock_get_session),
            patch(
                "src.api.routes.flow_grades.FlowGradeRepository",
                return_value=mock_flow_grade_repo,
            ),
            patch("src.tracing.log_human_feedback") as mock_log_feedback,
        ):
            response = await flow_grades_client.post(
                "/api/v1/flow-grades",
                json={
                    "conversation_id": "conv-uuid-1",
                    "grade": 1,
                    "span_id": "span-uuid-1",
                    "comment": "Great response!",
                    "agent_role": "architect",
                    "trace_id": "trace-uuid-1",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "grade-uuid-1"
            assert data["conversation_id"] == "conv-uuid-1"
            assert data["span_id"] == "span-uuid-1"
            assert data["grade"] == 1
            assert data["comment"] == "Great response!"
            assert data["agent_role"] == "architect"
            mock_flow_grade_repo.upsert.assert_called_once()
            mock_log_feedback.assert_called_once()

    async def test_submit_grade_without_trace_id(
        self, flow_grades_client, mock_get_session, mock_flow_grade_repo, mock_flow_grade
    ):
        """Should create grade without MLflow feedback when trace_id is missing."""
        with (
            patch("src.api.routes.flow_grades.get_session", mock_get_session),
            patch(
                "src.api.routes.flow_grades.FlowGradeRepository",
                return_value=mock_flow_grade_repo,
            ),
            patch("src.tracing.log_human_feedback") as mock_log_feedback,
        ):
            response = await flow_grades_client.post(
                "/api/v1/flow-grades",
                json={
                    "conversation_id": "conv-uuid-1",
                    "grade": 1,
                    "span_id": None,
                    "comment": "Overall great",
                },
            )

            assert response.status_code == 201
            mock_log_feedback.assert_not_called()

    async def test_submit_grade_thumbs_down(
        self, flow_grades_client, mock_get_session, mock_flow_grade_repo
    ):
        """Should accept thumbs down grade."""
        mock_grade = MagicMock()
        mock_grade.id = "grade-uuid-2"
        mock_grade.conversation_id = "conv-uuid-1"
        mock_grade.span_id = None
        mock_grade.grade = -1
        mock_grade.comment = "Not helpful"
        mock_grade.agent_role = None
        mock_grade.created_at = datetime.now(UTC)

        mock_flow_grade_repo.upsert = AsyncMock(return_value=mock_grade)

        with (
            patch("src.api.routes.flow_grades.get_session", mock_get_session),
            patch(
                "src.api.routes.flow_grades.FlowGradeRepository",
                return_value=mock_flow_grade_repo,
            ),
            patch("src.tracing.log_human_feedback") as mock_log_feedback,
        ):
            response = await flow_grades_client.post(
                "/api/v1/flow-grades",
                json={
                    "conversation_id": "conv-uuid-1",
                    "grade": -1,
                    "comment": "Not helpful",
                    "trace_id": "trace-uuid-1",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["grade"] == -1
            mock_log_feedback.assert_called_once()
            # Verify negative sentiment was logged
            call_kwargs = mock_log_feedback.call_args[1]
            assert call_kwargs["value"] == "negative"

    async def test_submit_grade_invalid_grade_value(self, flow_grades_client, mock_get_session):
        """Should return 400 for invalid grade value."""
        with patch("src.api.routes.flow_grades.get_session", mock_get_session):
            response = await flow_grades_client.post(
                "/api/v1/flow-grades",
                json={
                    "conversation_id": "conv-uuid-1",
                    "grade": 0,  # Invalid: must be 1 or -1
                },
            )

            assert response.status_code == 400
            assert "Grade must be 1 or -1" in response.json()["detail"]

    async def test_submit_grade_updates_existing(
        self, flow_grades_client, mock_get_session, mock_flow_grade_repo, mock_flow_grade
    ):
        """Should update existing grade for same conversation+span."""
        with (
            patch("src.api.routes.flow_grades.get_session", mock_get_session),
            patch(
                "src.api.routes.flow_grades.FlowGradeRepository",
                return_value=mock_flow_grade_repo,
            ),
        ):
            # First submission
            await flow_grades_client.post(
                "/api/v1/flow-grades",
                json={
                    "conversation_id": "conv-uuid-1",
                    "grade": 1,
                    "span_id": "span-uuid-1",
                },
            )

            # Update to thumbs down
            mock_flow_grade.grade = -1
            response = await flow_grades_client.post(
                "/api/v1/flow-grades",
                json={
                    "conversation_id": "conv-uuid-1",
                    "grade": -1,
                    "span_id": "span-uuid-1",
                },
            )

            assert response.status_code == 201
            assert mock_flow_grade_repo.upsert.call_count == 2


@pytest.mark.asyncio
class TestGetGrades:
    """Tests for GET /api/v1/flow-grades/{conversation_id}."""

    async def test_get_grades_success(
        self, flow_grades_client, mock_get_session, mock_flow_grade_repo
    ):
        """Should return grade summary for conversation."""
        with (
            patch("src.api.routes.flow_grades.get_session", mock_get_session),
            patch(
                "src.api.routes.flow_grades.FlowGradeRepository",
                return_value=mock_flow_grade_repo,
            ),
        ):
            response = await flow_grades_client.get("/api/v1/flow-grades/conv-uuid-1")

            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == "conv-uuid-1"
            assert "overall" in data
            assert "steps" in data
            assert data["total_grades"] == 2
            assert data["thumbs_up"] == 2
            assert data["thumbs_down"] == 0
            mock_flow_grade_repo.get_summary.assert_called_once_with("conv-uuid-1")

    async def test_get_grades_empty_conversation(self, flow_grades_client, mock_get_session):
        """Should return empty summary for conversation with no grades."""
        repo = MagicMock()
        repo.get_summary = AsyncMock(
            return_value={
                "conversation_id": "conv-empty",
                "overall": None,
                "steps": [],
                "total_grades": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
            }
        )

        with (
            patch("src.api.routes.flow_grades.get_session", mock_get_session),
            patch("src.api.routes.flow_grades.FlowGradeRepository", return_value=repo),
        ):
            response = await flow_grades_client.get("/api/v1/flow-grades/conv-empty")

            assert response.status_code == 200
            data = response.json()
            assert data["total_grades"] == 0
            assert data["overall"] is None
            assert data["steps"] == []


@pytest.mark.asyncio
class TestDeleteGrade:
    """Tests for DELETE /api/v1/flow-grades/{grade_id}."""

    async def test_delete_grade_success(
        self, flow_grades_client, mock_get_session, mock_flow_grade_repo
    ):
        """Should delete grade and return 204."""
        with (
            patch("src.api.routes.flow_grades.get_session", mock_get_session),
            patch(
                "src.api.routes.flow_grades.FlowGradeRepository",
                return_value=mock_flow_grade_repo,
            ),
        ):
            response = await flow_grades_client.delete("/api/v1/flow-grades/grade-uuid-1")

            assert response.status_code == 204
            mock_flow_grade_repo.delete.assert_called_once_with("grade-uuid-1")

    async def test_delete_grade_not_found(self, flow_grades_client, mock_get_session):
        """Should return 404 when grade not found."""
        repo = MagicMock()
        repo.delete = AsyncMock(return_value=False)

        with (
            patch("src.api.routes.flow_grades.get_session", mock_get_session),
            patch("src.api.routes.flow_grades.FlowGradeRepository", return_value=repo),
        ):
            response = await flow_grades_client.delete("/api/v1/flow-grades/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
