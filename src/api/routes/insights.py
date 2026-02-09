"""Insight API routes for energy analysis results.

User Story 3: Energy Optimization Suggestions.
"""

import contextlib
from datetime import UTC

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

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
from src.storage import get_session
from src.storage.entities.insight import InsightStatus, InsightType

router = APIRouter(prefix="/insights", tags=["Insights"])


def _insight_to_response(insight) -> InsightResponse:
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
) -> InsightListResponse:
    """List all insights with optional filters."""
    async with get_session() as session:
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
async def list_pending_insights(limit: int = 50) -> InsightListResponse:
    """List insights pending review."""
    async with get_session() as session:
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
async def get_insights_summary() -> InsightSummary:
    """Get insights summary with counts by type and status."""
    async with get_session() as session:
        repo = InsightRepository(session)

        total = await repo.count()
        by_type = await repo.count_by_type()
        by_status = await repo.count_by_status()
        pending_count = await repo.count(status=InsightStatus.PENDING)

        # Count high impact (high + critical)
        high_impact = await repo.list_by_impact("high", limit=100)
        critical_impact = await repo.list_by_impact("critical", limit=100)
        high_impact_count = len(high_impact) + len(critical_impact)

        return InsightSummary(
            total=total,
            by_type=by_type,
            by_status=by_status,
            pending_count=pending_count,
            high_impact_count=high_impact_count,
        )


@router.get(
    "/{insight_id}",
    response_model=InsightResponse,
    summary="Get insight",
    description="Get a specific insight by ID.",
    responses={404: {"model": ErrorResponse}},
)
async def get_insight(insight_id: str) -> InsightResponse:
    """Get insight by ID."""
    async with get_session() as session:
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
async def create_insight(data: InsightCreate) -> InsightResponse:
    """Create a new insight."""
    async with get_session() as session:
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
async def review_insight(request: Request, insight_id: str, data: ReviewRequest) -> InsightResponse:
    """Mark insight as reviewed."""
    async with get_session() as session:
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
async def action_insight(request: Request, insight_id: str, data: ActionRequest) -> InsightResponse:
    """Mark insight as actioned."""
    async with get_session() as session:
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
    request: Request, insight_id: str, data: DismissRequest
) -> InsightResponse:
    """Dismiss an insight."""
    async with get_session() as session:
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
async def delete_insight(request: Request, insight_id: str) -> None:
    """Delete an insight."""
    async with get_session() as session:
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
    from src.storage import get_session

    try:
        # Map string to enum
        try:
            analysis_enum = AnalysisType(analysis_type)
        except ValueError:
            analysis_enum = AnalysisType.ENERGY_OPTIMIZATION

        workflow = DataScientistWorkflow()

        async with get_session() as session:
            await workflow.run_analysis(
                analysis_type=analysis_enum,
                entity_ids=entity_ids,
                hours=hours,
                custom_query=options.get("custom_query"),
                session=session,
            )
            await session.commit()

    except Exception as e:
        # Log error but don't raise (background task)
        import logging

        logging.getLogger(__name__).error(f"Analysis job {job_id} failed: {e}")
