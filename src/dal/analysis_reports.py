"""Repository for AnalysisReport CRUD operations.

Feature 33: DS Deep Analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import select

from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AnalysisReportRepository:
    """Repository for AnalysisReport CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(
        self,
        title: str,
        analysis_type: str,
        depth: str,
        strategy: str,
        conversation_id: str | None = None,
    ) -> AnalysisReport:
        """Create a new running report.

        Args:
            title: Report title.
            analysis_type: AnalysisType value.
            depth: AnalysisDepth value (quick, standard, deep).
            strategy: ExecutionStrategy value (parallel, teamwork).
            conversation_id: Originating conversation ID.

        Returns:
            The created AnalysisReport with status=RUNNING.
        """
        report = AnalysisReport(
            id=str(uuid4()),
            title=title,
            analysis_type=analysis_type,
            depth=depth,
            strategy=strategy,
            status=ReportStatus.RUNNING,
            insight_ids=[],
            artifact_paths=[],
            communication_log=[],
            communication_count=0,
            conversation_id=conversation_id,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_by_id(self, report_id: str) -> AnalysisReport | None:
        """Get report by ID.

        Args:
            report_id: Report UUID.

        Returns:
            AnalysisReport or None.
        """
        result = await self.session.execute(
            select(AnalysisReport).where(AnalysisReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def complete(
        self,
        report_id: str,
        summary: str | None = None,
        insight_ids: list[str] | None = None,
        artifact_paths: list[str] | None = None,
        communication_log: list[dict[str, Any]] | None = None,
    ) -> AnalysisReport | None:
        """Mark a report as completed and attach results.

        Args:
            report_id: Report UUID.
            summary: Executive summary text.
            insight_ids: IDs of insights linked to this report.
            artifact_paths: Filenames of artifacts produced.
            communication_log: Inter-agent communication entries.

        Returns:
            Updated AnalysisReport or None if not found.
        """
        report = await self.get_by_id(report_id)
        if report is None:
            return None

        report.mark_completed(summary=summary)
        if insight_ids is not None:
            report.insight_ids = insight_ids
        if artifact_paths is not None:
            report.artifact_paths = artifact_paths
        if communication_log is not None:
            report.communication_log = communication_log
            report.communication_count = len(communication_log)

        await self.session.flush()
        return report

    async def fail(
        self,
        report_id: str,
        summary: str | None = None,
    ) -> AnalysisReport | None:
        """Mark a report as failed.

        Args:
            report_id: Report UUID.
            summary: Error summary.

        Returns:
            Updated AnalysisReport or None if not found.
        """
        report = await self.get_by_id(report_id)
        if report is None:
            return None

        report.mark_failed(summary=summary)
        await self.session.flush()
        return report

    async def list_reports(
        self,
        status: ReportStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalysisReport]:
        """List reports with optional status filter.

        Args:
            status: Optional status filter.
            limit: Max results.
            offset: Skip results.

        Returns:
            List of AnalysisReport instances.
        """
        query = select(AnalysisReport).order_by(AnalysisReport.created_at.desc())

        if status is not None:
            query = query.where(AnalysisReport.status == status)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
