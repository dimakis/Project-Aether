"""Insight API routes for energy analysis results.

User Story 3: Energy Optimization Suggestions.
"""

import contextlib
import logging
from datetime import UTC
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.rate_limit import limiter
from src.api.schemas import (
    ActionRequest,
    AnalysisJob,
    AnalysisRequest,
    DismissRequest,
    ErrorResponse,
    InsightCreate,
    InsightListResponse,
    InsightResponse,
    InsightSummary,
    ReviewRequest,
)
from src.dal import InsightRepository
from src.storage.entities.insight import InsightStatus, InsightType

# Route handlers use Depends(get_db) for request-scoped session; background
# tasks (e.g. _run_analysis_job) import get_session locally as they have no request.

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


def _insight_to_response(insight: Any) -> InsightResponse:
    """Convert Insight model to response schema."""
    return InsightResponse(
        id=insight.id,
        type=insight.type.value,
        title=insight.title,
        description=insight.description,
        evidence=insight.evidence,
        confidence=insight.confidence,
        impact=insight.impact,
        entities=insight.entities,
        script_path=insight.script_path,
        script_output=insight.script_output,
        status=insight.status.value,
        mlflow_run_id=insight.mlflow_run_id,
        conversation_id=getattr(insight, "conversation_id", None),
        task_label=getattr(insight, "task_label", None),
        created_at=insight.created_at,
        reviewed_at=insight.reviewed_at,
        actioned_at=insight.actioned_at,
    )


@router.get(
    "",
    response_model=InsightListResponse,
    summary="List insights",
    description="List insights with optional type and status filters.",
)
async def list_insights(
    type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
) -> InsightListResponse:
    """List all insights with optional filters."""
    repo = InsightRepository(session)

    # Parse filters
    type_filter = None
    status_filter = None

    if type:
        with contextlib.suppress(ValueError):
            type_filter = InsightType(type.lower())

    if status:
        with contextlib.suppress(ValueError):
            status_filter = InsightStatus(status.lower())

    # Fetch based on filters
    if type_filter:
        insights = await repo.list_by_type(
            type_filter, status=status_filter, limit=limit, offset=offset
        )
    elif status_filter:
        insights = await repo.list_by_status(status_filter, limit=limit, offset=offset)
    else:
        insights = await repo.list_all(limit=limit, offset=offset)

    total = await repo.count(type=type_filter, status=status_filter)

    return InsightListResponse(
        items=[_insight_to_response(i) for i in insights],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/pending",
    response_model=InsightListResponse,
    summary="List pending insights",
    description="List insights awaiting review.",
)
async def list_pending_insights(
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
) -> InsightListResponse:
    """List insights pending review."""
    repo = InsightRepository(session)
    insights = await repo.list_pending(limit=limit)
    total = await repo.count(status=InsightStatus.PENDING)

    return InsightListResponse(
        items=[_insight_to_response(i) for i in insights],
        total=total,
        limit=limit,
        offset=0,
    )


@router.get(
    "/summary",
    response_model=InsightSummary,
    summary="Get insights summary",
    description="Get counts and statistics for insights.",
)
async def get_insights_summary(
    session: AsyncSession = Depends(get_db),
) -> InsightSummary:
    """Get insights summary with counts by type and status."""
    repo = InsightRepository(session)
    summary = await repo.get_summary()
    return InsightSummary(**summary)


@router.get(
    "/{insight_id}",
    response_model=InsightResponse,
    summary="Get insight",
    description="Get a specific insight by ID.",
    responses={404: {"model": ErrorResponse}},
)
async def get_insight(
    insight_id: str,
    session: AsyncSession = Depends(get_db),
) -> InsightResponse:
    """Get insight by ID."""
    repo = InsightRepository(session)
    insight = await repo.get_by_id(insight_id)

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    return _insight_to_response(insight)


@router.post(
    "",
    response_model=InsightResponse,
    status_code=201,
    summary="Create insight",
    description="Create a new insight (typically done by Data Scientist agent).",
)
async def create_insight(
    data: InsightCreate,
    session: AsyncSession = Depends(get_db),
) -> InsightResponse:
    """Create a new insight."""
    repo = InsightRepository(session)

    # Map string type to enum
    try:
        insight_type = InsightType(data.type.value)
    except ValueError:
        insight_type = InsightType.ENERGY_OPTIMIZATION

    insight = await repo.create(
        type=insight_type,
        title=data.title,
        description=data.description,
        evidence=data.evidence,
        confidence=data.confidence,
        impact=data.impact,
        entities=data.entities,
        script_path=data.script_path,
        script_output=data.script_output,
        mlflow_run_id=data.mlflow_run_id,
    )
    await session.commit()

    return _insight_to_response(insight)


@router.post(
    "/{insight_id}/review",
    response_model=InsightResponse,
    summary="Mark insight as reviewed",
    description="Mark an insight as reviewed by a user.",
    responses={404: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
async def review_insight(
    request: Request,
    insight_id: str,
    data: ReviewRequest,
    session: AsyncSession = Depends(get_db),
) -> InsightResponse:
    """Mark insight as reviewed."""
    repo = InsightRepository(session)
    insight = await repo.mark_reviewed(insight_id)

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    await session.commit()
    return _insight_to_response(insight)


@router.post(
    "/{insight_id}/action",
    response_model=InsightResponse,
    summary="Mark insight as actioned",
    description="Mark an insight as actioned (user took action based on it).",
    responses={404: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
async def action_insight(
    request: Request,
    insight_id: str,
    data: ActionRequest,
    session: AsyncSession = Depends(get_db),
) -> InsightResponse:
    """Mark insight as actioned."""
    repo = InsightRepository(session)
    insight = await repo.mark_actioned(insight_id)

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    await session.commit()
    return _insight_to_response(insight)


@router.post(
    "/{insight_id}/dismiss",
    response_model=InsightResponse,
    summary="Dismiss insight",
    description="Dismiss an insight (not relevant or not actionable).",
    responses={404: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
async def dismiss_insight(
    request: Request,
    insight_id: str,
    data: DismissRequest,
    session: AsyncSession = Depends(get_db),
) -> InsightResponse:
    """Dismiss an insight."""
    repo = InsightRepository(session)
    insight = await repo.dismiss(insight_id)

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    await session.commit()
    return _insight_to_response(insight)


@router.delete(
    "/{insight_id}",
    status_code=204,
    summary="Delete insight",
    description="Delete an insight.",
    responses={404: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
async def delete_insight(
    request: Request,
    insight_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete an insight."""
    repo = InsightRepository(session)
    deleted = await repo.delete(insight_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Insight not found")

    await session.commit()


@router.post(
    "/analyze",
    response_model=AnalysisJob,
    status_code=202,
    summary="Start energy analysis",
    description="Start a new energy analysis job (async).",
)
@limiter.limit("5/minute")
async def start_analysis(
    request: Request,
    data: AnalysisRequest,
    background_tasks: BackgroundTasks,
) -> AnalysisJob:
    """Start an energy analysis job.

    Rate limited to 5/minute (sandbox execution).

    This runs asynchronously in the background and returns
    a job ID that can be used to check status.
    """
    from datetime import datetime
    from uuid import uuid4

    # Create job placeholder
    job_id = str(uuid4())
    job = AnalysisJob(
        job_id=job_id,
        status="pending",
        analysis_type=data.analysis_type,
        progress=0.0,
        started_at=datetime.now(UTC),
    )

    # Queue the actual analysis work
    background_tasks.add_task(
        _run_analysis_job,
        job_id=job_id,
        analysis_type=data.analysis_type,
        entity_ids=data.entity_ids,
        hours=data.hours,
        options=data.options,
    )

    return job


async def _run_analysis_job(
    job_id: str,
    analysis_type: str,
    entity_ids: list[str] | None,
    hours: int,
    options: dict,
) -> None:
    """Run the analysis job in the background.

    This is called by FastAPI's BackgroundTasks.
    """
    from src.agents import DataScientistWorkflow
    from src.graph.state import AnalysisType
    from src.jobs import emit_job_agent, emit_job_complete, emit_job_failed, emit_job_start
    from src.storage import get_session

    title = f"Analysis: {analysis_type} ({hours}h)"
    emit_job_start(job_id, "analysis", title)

    try:
        try:
            analysis_enum = AnalysisType(analysis_type)
        except ValueError:
            analysis_enum = AnalysisType.ENERGY_OPTIMIZATION

        workflow = DataScientistWorkflow()
        emit_job_agent(job_id, "data_scientist", "start")

        async with get_session() as session:
            await workflow.run_analysis(
                analysis_type=analysis_enum,
                entity_ids=entity_ids,
                hours=hours,
                custom_query=options.get("custom_query"),
                session=session,
            )
            await session.commit()

        emit_job_agent(job_id, "data_scientist", "end")
        emit_job_complete(job_id)

    except Exception:
        logger.exception("Analysis job %s failed", job_id)
        emit_job_failed(job_id, f"Analysis {analysis_type} failed")
