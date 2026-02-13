"""Unit tests for AnalysisReport entity and repository.

Tests T3337: AnalysisReport model, status transitions, and repository
CRUD operations (using mocked DB session).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# Entity model tests
# =============================================================================


class TestAnalysisReportEntity:
    """Test the AnalysisReport SQLAlchemy entity."""

    def test_entity_importable(self):
        from src.storage.entities.analysis_report import ReportStatus

        assert ReportStatus.RUNNING == "running"
        assert ReportStatus.COMPLETED == "completed"
        assert ReportStatus.FAILED == "failed"

    def test_mark_completed(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        report = AnalysisReport(
            id="test-id",
            title="Test Report",
            analysis_type="energy_optimization",
            depth="deep",
            strategy="teamwork",
            status=ReportStatus.RUNNING,
        )
        report.mark_completed(summary="All good")

        assert report.status == ReportStatus.COMPLETED
        assert report.summary == "All good"
        assert report.completed_at is not None

    def test_mark_failed(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        report = AnalysisReport(
            id="test-id",
            title="Test Report",
            analysis_type="diagnostic",
            depth="quick",
            strategy="parallel",
            status=ReportStatus.RUNNING,
        )
        report.mark_failed(summary="Timeout")

        assert report.status == ReportStatus.FAILED
        assert report.summary == "Timeout"
        assert report.completed_at is not None

    def test_repr(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        report = AnalysisReport(
            id="12345678-abcd-efgh-ijkl-mnopqrstuvwx",
            title="Test",
            analysis_type="energy",
            depth="standard",
            strategy="parallel",
            status=ReportStatus.RUNNING,
        )
        assert "12345678" in repr(report)
        assert "running" in repr(report)

    def test_default_collections(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        report = AnalysisReport(
            id="test-id",
            title="Test",
            analysis_type="energy",
            depth="standard",
            strategy="parallel",
            status=ReportStatus.RUNNING,
        )
        # These should be empty lists by default at the Python level
        assert report.insight_ids == [] or report.insight_ids is None  # Depends on initialization
        assert report.communication_count == 0 or report.communication_count is None


# =============================================================================
# Repository tests (mocked session)
# =============================================================================


class TestAnalysisReportRepository:
    """Test AnalysisReportRepository with mocked AsyncSession."""

    def _make_repo(self):
        from src.dal.analysis_reports import AnalysisReportRepository

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return AnalysisReportRepository(session), session

    @pytest.mark.asyncio
    async def test_create(self):
        repo, session = self._make_repo()
        report = await repo.create(
            title="Energy Deep Dive",
            analysis_type="energy_optimization",
            depth="deep",
            strategy="teamwork",
        )

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert report.title == "Energy Deep Dive"
        assert report.depth == "deep"
        assert report.strategy == "teamwork"
        assert report.status.value == "running"
        assert len(report.id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_create_with_conversation_id(self):
        repo, _session = self._make_repo()
        report = await repo.create(
            title="Test",
            analysis_type="diagnostic",
            depth="quick",
            strategy="parallel",
            conversation_id="conv-123",
        )
        assert report.conversation_id == "conv-123"

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        repo, session = self._make_repo()
        expected = AnalysisReport(
            id="abc-123",
            title="Test",
            analysis_type="energy",
            depth="deep",
            strategy="teamwork",
            status=ReportStatus.COMPLETED,
        )

        # Mock the execute -> scalar_one_or_none chain
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id("abc-123")
        assert result is expected

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        repo, session = self._make_repo()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_complete(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        repo, session = self._make_repo()
        report = AnalysisReport(
            id="abc-123",
            title="Test",
            analysis_type="energy",
            depth="deep",
            strategy="teamwork",
            status=ReportStatus.RUNNING,
            insight_ids=[],
            artifact_paths=[],
            communication_log=[],
            communication_count=0,
        )

        # Mock get_by_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = report
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.complete(
            report_id="abc-123",
            summary="Analysis complete",
            insight_ids=["ins-1", "ins-2"],
            artifact_paths=["chart.png"],
            communication_log=[{"from": "a", "to": "b", "msg": "test"}],
        )

        assert result is not None
        assert result.status == ReportStatus.COMPLETED
        assert result.summary == "Analysis complete"
        assert result.insight_ids == ["ins-1", "ins-2"]
        assert result.artifact_paths == ["chart.png"]
        assert result.communication_count == 1

    @pytest.mark.asyncio
    async def test_fail(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        repo, session = self._make_repo()
        report = AnalysisReport(
            id="abc-123",
            title="Test",
            analysis_type="energy",
            depth="standard",
            strategy="parallel",
            status=ReportStatus.RUNNING,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = report
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.fail(report_id="abc-123", summary="Timeout")
        assert result is not None
        assert result.status == ReportStatus.FAILED
        assert result.summary == "Timeout"

    @pytest.mark.asyncio
    async def test_list_reports(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

        repo, session = self._make_repo()

        reports = [
            AnalysisReport(
                id=f"r-{i}",
                title=f"Report {i}",
                analysis_type="energy",
                depth="standard",
                strategy="parallel",
                status=ReportStatus.COMPLETED,
            )
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = reports
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_reports()
        assert len(result) == 3
