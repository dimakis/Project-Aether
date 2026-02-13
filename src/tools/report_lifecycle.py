"""Report lifecycle helpers for the DS team workflow.

Thin wrappers around AnalysisReportRepository that can be called
from consult_data_science_team to manage report creation, completion,
and failure.

Feature 33: DS Deep Analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.dal.analysis_reports import AnalysisReportRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.storage.entities.analysis_report import AnalysisReport


async def create_analysis_report(
    session: AsyncSession,
    title: str,
    analysis_type: str,
    depth: str,
    strategy: str,
    conversation_id: str | None = None,
) -> AnalysisReport:
    """Create a new RUNNING analysis report.

    Call at the start of a team analysis workflow.

    Args:
        session: Database session.
        title: Report title (derived from query).
        analysis_type: AnalysisType value.
        depth: AnalysisDepth value.
        strategy: ExecutionStrategy value.
        conversation_id: Originating conversation ID.

    Returns:
        The created AnalysisReport with status=RUNNING.
    """
    repo = AnalysisReportRepository(session)
    return await repo.create(
        title=title,
        analysis_type=analysis_type,
        depth=depth,
        strategy=strategy,
        conversation_id=conversation_id,
    )


async def complete_analysis_report(
    session: AsyncSession,
    report_id: str,
    summary: str | None = None,
    insight_ids: list[str] | None = None,
    artifact_paths: list[str] | None = None,
    communication_log: list[dict[str, Any]] | None = None,
) -> AnalysisReport | None:
    """Mark an analysis report as completed with results.

    Call at the end of a successful team analysis workflow.

    Args:
        session: Database session.
        report_id: Report UUID.
        summary: Executive summary.
        insight_ids: Linked insight IDs.
        artifact_paths: Artifact filenames.
        communication_log: Inter-agent communication entries.

    Returns:
        Updated report or None if not found.
    """
    repo = AnalysisReportRepository(session)
    return await repo.complete(
        report_id=report_id,
        summary=summary,
        insight_ids=insight_ids,
        artifact_paths=artifact_paths,
        communication_log=communication_log,
    )


async def fail_analysis_report(
    session: AsyncSession,
    report_id: str,
    summary: str | None = None,
) -> AnalysisReport | None:
    """Mark an analysis report as failed.

    Call when the team analysis workflow fails.

    Args:
        session: Database session.
        report_id: Report UUID.
        summary: Error summary.

    Returns:
        Updated report or None if not found.
    """
    repo = AnalysisReportRepository(session)
    return await repo.fail(
        report_id=report_id,
        summary=summary,
    )
