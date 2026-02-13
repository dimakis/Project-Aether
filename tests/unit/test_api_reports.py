"""Unit tests for the Analysis Reports API endpoints.

Tests T3338: List, get, and communication log endpoints.
Uses mocked DB session to avoid real DB connections.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.reports import router


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_get_session(session: AsyncMock):
    """Create a mock get_session returning an async context manager."""

    @asynccontextmanager
    async def mock_session():
        yield session

    return mock_session


def _make_session_for_list(reports: list) -> AsyncMock:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = reports
    session.execute = AsyncMock(return_value=mock_result)
    return session


def _make_session_for_get(entity: Any | None) -> AsyncMock:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = entity
    session.execute = AsyncMock(return_value=mock_result)
    return session


class TestListReports:
    """Test GET /reports."""

    def test_list_empty(self):
        app = _create_test_app()
        session = _make_session_for_list([])

        with patch("src.api.routes.reports.get_session", _mock_get_session(session)):
            client = TestClient(app)
            response = client.get("/reports")
            assert response.status_code == 200
            data = response.json()
            assert data["reports"] == []
            assert data["total"] == 0

    def test_list_with_reports(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        app = _create_test_app()
        report = AnalysisReport(
            id="r-1",
            title="Energy Report",
            analysis_type="energy_optimization",
            depth="deep",
            strategy="teamwork",
            status=ReportStatus.COMPLETED,
            summary="All good",
            insight_ids=["i-1"],
            artifact_paths=["chart.png"],
            communication_log=[],
            communication_count=0,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        session = _make_session_for_list([report])

        with patch("src.api.routes.reports.get_session", _mock_get_session(session)):
            client = TestClient(app)
            response = client.get("/reports")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["reports"][0]["id"] == "r-1"
            assert data["reports"][0]["depth"] == "deep"


class TestGetReport:
    """Test GET /reports/{report_id}."""

    def test_get_existing(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        app = _create_test_app()
        report = AnalysisReport(
            id="r-123",
            title="Test Report",
            analysis_type="diagnostic",
            depth="standard",
            strategy="parallel",
            status=ReportStatus.COMPLETED,
            summary="Done",
            insight_ids=[],
            artifact_paths=[],
            communication_log=[],
            communication_count=0,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        session = _make_session_for_get(report)

        with patch("src.api.routes.reports.get_session", _mock_get_session(session)):
            client = TestClient(app)
            response = client.get("/reports/r-123")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "r-123"
            assert data["status"] == "completed"

    def test_get_not_found(self):
        app = _create_test_app()
        session = _make_session_for_get(None)

        with patch("src.api.routes.reports.get_session", _mock_get_session(session)):
            client = TestClient(app)
            response = client.get("/reports/nonexistent")
            assert response.status_code == 404


class TestGetCommunicationLog:
    """Test GET /reports/{report_id}/communication."""

    def test_get_communication_log(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        app = _create_test_app()

        comm_log = [
            {
                "from_agent": "energy_analyst",
                "to_agent": "team",
                "message_type": "finding",
                "content": "Spike at 2am",
            },
            {
                "from_agent": "behavioral_analyst",
                "to_agent": "energy_analyst",
                "message_type": "cross_reference",
                "content": "Confirms activity",
            },
        ]

        report = AnalysisReport(
            id="r-456",
            title="Test",
            analysis_type="energy",
            depth="deep",
            strategy="teamwork",
            status=ReportStatus.COMPLETED,
            insight_ids=[],
            artifact_paths=[],
            communication_log=comm_log,
            communication_count=2,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        session = _make_session_for_get(report)

        with patch("src.api.routes.reports.get_session", _mock_get_session(session)):
            client = TestClient(app)
            response = client.get("/reports/r-456/communication")
            assert response.status_code == 200
            data = response.json()
            assert data["report_id"] == "r-456"
            assert data["count"] == 2
            assert len(data["communication_log"]) == 2
            assert data["communication_log"][0]["from_agent"] == "energy_analyst"

    def test_communication_log_not_found(self):
        app = _create_test_app()
        session = _make_session_for_get(None)

        with patch("src.api.routes.reports.get_session", _mock_get_session(session)):
            client = TestClient(app)
            response = client.get("/reports/nonexistent/communication")
            assert response.status_code == 404
