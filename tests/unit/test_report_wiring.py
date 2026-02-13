"""Unit tests for report wiring into the DS team workflow.

Tests T3339: Report creation/completion helper that can be used by
consult_data_science_team to manage report lifecycle.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCreateReportHelper:
    """Test the create_analysis_report helper function."""

    @pytest.mark.asyncio
    async def test_creates_running_report(self):
        from src.tools.report_lifecycle import create_analysis_report

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        report = await create_analysis_report(
            session=mock_session,
            title="Energy Deep Dive",
            analysis_type="energy_optimization",
            depth="deep",
            strategy="teamwork",
        )

        assert report.title == "Energy Deep Dive"
        assert report.depth == "deep"
        assert report.strategy == "teamwork"
        assert report.status.value == "running"
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_with_conversation_id(self):
        from src.tools.report_lifecycle import create_analysis_report

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        report = await create_analysis_report(
            session=mock_session,
            title="Test",
            analysis_type="diagnostic",
            depth="quick",
            strategy="parallel",
            conversation_id="conv-123",
        )

        assert report.conversation_id == "conv-123"


class TestCompleteReportHelper:
    """Test the complete_analysis_report helper function."""

    @pytest.mark.asyncio
    async def test_marks_completed(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus
        from src.tools.report_lifecycle import complete_analysis_report

        report = AnalysisReport(
            id="r-1",
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

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = report
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        result = await complete_analysis_report(
            session=mock_session,
            report_id="r-1",
            summary="Analysis complete",
            insight_ids=["ins-1"],
            artifact_paths=["chart.png"],
            communication_log=[{"from": "a", "to": "b"}],
        )

        assert result is not None
        assert result.status == ReportStatus.COMPLETED
        assert result.insight_ids == ["ins-1"]
        assert result.communication_count == 1

    @pytest.mark.asyncio
    async def test_returns_none_for_missing(self):
        from src.tools.report_lifecycle import complete_analysis_report

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await complete_analysis_report(
            session=mock_session,
            report_id="nonexistent",
        )

        assert result is None


class TestFailReportHelper:
    """Test the fail_analysis_report helper function."""

    @pytest.mark.asyncio
    async def test_marks_failed(self):
        from src.storage.entities.analysis_report import AnalysisReport, ReportStatus
        from src.tools.report_lifecycle import fail_analysis_report

        report = AnalysisReport(
            id="r-2",
            title="Test",
            analysis_type="energy",
            depth="standard",
            strategy="parallel",
            status=ReportStatus.RUNNING,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = report
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        result = await fail_analysis_report(
            session=mock_session,
            report_id="r-2",
            summary="Timeout exceeded",
        )

        assert result is not None
        assert result.status == ReportStatus.FAILED
        assert result.summary == "Timeout exceeded"
