"""Analysis Reports API routes.

Feature 33: DS Deep Analysis — report lifecycle management.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.dal.analysis_reports import AnalysisReportRepository
from src.storage import get_session
from src.storage.entities.analysis_report import ReportStatus

router = APIRouter(prefix="/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ReportResponse(BaseModel):
    """Response schema for an analysis report."""

    id: str
    title: str
    analysis_type: str
    depth: str
    strategy: str
    status: str
    summary: str | None = None
    insight_ids: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)
    communication_log: list[dict[str, Any]] = Field(default_factory=list)
    communication_count: int = 0
    conversation_id: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class ReportListResponse(BaseModel):
    """Response schema for a list of reports."""

    reports: list[ReportResponse]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _report_to_response(report: Any) -> ReportResponse:
    """Convert AnalysisReport entity to response schema."""
    return ReportResponse(
        id=report.id,
        title=report.title,
        analysis_type=report.analysis_type,
        depth=report.depth,
        strategy=report.strategy,
        status=report.status.value if hasattr(report.status, "value") else report.status,
        summary=report.summary,
        insight_ids=report.insight_ids or [],
        artifact_paths=report.artifact_paths or [],
        communication_log=report.communication_log or [],
        communication_count=report.communication_count or 0,
        conversation_id=report.conversation_id,
        created_at=str(report.created_at) if report.created_at else None,
        completed_at=str(report.completed_at) if report.completed_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List analysis reports",
)
async def list_reports(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ReportListResponse:
    """List analysis reports with optional status filter.

    Args:
        status: Optional filter by status (running, completed, failed).
        limit: Maximum number of results.
        offset: Number of results to skip.
    """
    async with get_session() as session:
        repo = AnalysisReportRepository(session)

        import contextlib

        status_filter = None
        if status:
            with contextlib.suppress(ValueError):
                status_filter = ReportStatus(status.lower())

        reports = await repo.list_reports(
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        return ReportListResponse(
            reports=[_report_to_response(r) for r in reports],
            total=len(reports),
        )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get analysis report",
    responses={404: {"description": "Report not found"}},
)
async def get_report(report_id: str) -> ReportResponse:
    """Get a specific analysis report by ID.

    Args:
        report_id: The report UUID.
    """
    async with get_session() as session:
        repo = AnalysisReportRepository(session)
        report = await repo.get_by_id(report_id)

        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")

        return _report_to_response(report)


@router.get(
    "/{report_id}/communication",
    summary="Get report communication log",
    responses={404: {"description": "Report not found"}},
)
async def get_report_communication(report_id: str) -> dict[str, Any]:
    """Get the inter-agent communication log for a report.

    Returns the chronological list of messages exchanged between
    specialist agents during the analysis.

    Args:
        report_id: The report UUID.
    """
    async with get_session() as session:
        repo = AnalysisReportRepository(session)
        report = await repo.get_by_id(report_id)

        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")

        return {
            "report_id": report.id,
            "communication_log": report.communication_log or [],
            "count": report.communication_count or 0,
        }
