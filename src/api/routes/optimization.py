"""Optimization API routes for intelligent analysis.

Feature 03: Intelligent Optimization & Multi-Agent Collaboration.
Feature 38: Optimization Persistence — jobs and suggestions stored in DB.

Provides endpoints for running behavioral analysis, viewing
automation suggestions, and accepting/rejecting suggestions.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.rate_limit import limiter
from src.api.schemas.optimization import (
    AutomationSuggestionResponse,
    OptimizationRequest,
    OptimizationResult,
    SuggestionAcceptRequest,
    SuggestionListResponse,
    SuggestionRejectRequest,
    SuggestionStatus,
)
from src.dal.optimization import (
    AutomationSuggestionRepository,
    OptimizationJobRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimize", tags=["Optimization"])


def _job_to_result(job: Any, suggestions_loaded: bool = True) -> OptimizationResult:
    """Map an OptimizationJob entity to the API response schema.

    Args:
        job: OptimizationJob entity.
        suggestions_loaded: If False, skip accessing the suggestions
            relationship to avoid lazy-load errors on expired instances.
    """
    suggestions = []
    if suggestions_loaded:
        try:
            suggestions = [
                AutomationSuggestionResponse(
                    id=s.id,
                    pattern=s.pattern,
                    entities=s.entities or [],
                    proposed_trigger=s.proposed_trigger or "",
                    proposed_action=s.proposed_action or "",
                    confidence=s.confidence or 0.0,
                    source_insight_type=s.source_insight_type or "",
                    status=SuggestionStatus(s.status),
                    created_at=s.created_at,
                )
                for s in (job.suggestions or [])
            ]
        except Exception:
            suggestions = []
    return OptimizationResult(
        job_id=job.id,
        status=job.status,
        analysis_types=job.analysis_types or [],
        hours_analyzed=job.hours_analyzed or 0,
        insight_count=job.insight_count,
        suggestion_count=job.suggestion_count,
        suggestions=suggestions,
        recommendations=job.recommendations or [],
        started_at=job.started_at or job.created_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@router.post("", response_model=OptimizationResult, status_code=202)
@limiter.limit("5/minute")
async def start_optimization(
    request: Request,
    data: OptimizationRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> OptimizationResult:
    """Run a full optimization analysis.

    Triggers behavioral analysis in the background. Returns a job
    that can be polled for completion.
    """
    repo = OptimizationJobRepository(session)
    now = datetime.now(UTC)

    job = await repo.create(
        {
            "status": "pending",
            "analysis_types": [t.value for t in data.analysis_types],
            "hours_analyzed": data.hours,
            "insight_count": 0,
            "suggestion_count": 0,
            "started_at": now,
        }
    )
    await session.commit()

    background_tasks.add_task(_run_optimization_background, job.id, data)

    return _job_to_result(job, suggestions_loaded=False)


@router.get("/jobs", response_model=list[OptimizationResult])
async def list_jobs(
    status: str | None = Query(None, description="Filter by job status"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> list[OptimizationResult]:
    """List optimization job history."""
    repo = OptimizationJobRepository(session)
    jobs = await repo.list_all(status=status, limit=limit)
    return [_job_to_result(j) for j in jobs]


@router.get("/suggestions/list", response_model=SuggestionListResponse)
async def list_suggestions(
    job_id: str | None = Query(None, description="Filter by job ID"),
    status: str | None = Query(None, description="Filter by suggestion status"),
    session: AsyncSession = Depends(get_db),
) -> SuggestionListResponse:
    """List automation suggestions."""
    repo = AutomationSuggestionRepository(session)
    entities = await repo.list_all(status=status, job_id=job_id)

    items = [
        AutomationSuggestionResponse(
            id=s.id,
            pattern=s.pattern,
            entities=s.entities or [],
            proposed_trigger=s.proposed_trigger or "",
            proposed_action=s.proposed_action or "",
            confidence=s.confidence or 0.0,
            source_insight_type=s.source_insight_type or "",
            status=SuggestionStatus(s.status),
            created_at=s.created_at,
        )
        for s in entities
    ]

    return SuggestionListResponse(items=items, total=len(items))


@router.get("/{job_id}", response_model=OptimizationResult)
async def get_optimization_status(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> OptimizationResult:
    """Get the status of an optimization job."""
    repo = OptimizationJobRepository(session)
    job = await repo.get_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return _job_to_result(job)


@router.post("/suggestions/{suggestion_id}/accept")
@limiter.limit("10/minute")
async def accept_suggestion(
    request: Request,
    suggestion_id: str,
    data: SuggestionAcceptRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Accept an automation suggestion and create a proposal."""
    repo = AutomationSuggestionRepository(session)
    entity = await repo.get_by_id(suggestion_id)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Suggestion not found: {suggestion_id}",
        )
    if entity.status != "pending":
        raise HTTPException(status_code=409, detail="Suggestion already processed")

    try:
        from src.agents import ArchitectAgent
        from src.graph.state import AutomationSuggestion

        suggestion = AutomationSuggestion(
            pattern=entity.pattern,
            entities=entity.entities or [],
            proposed_trigger=entity.proposed_trigger or "",
            proposed_action=entity.proposed_action or "",
            confidence=entity.confidence or 0.0,
            source_insight_type=entity.source_insight_type or "",
        )

        architect = ArchitectAgent()
        result = await architect.receive_suggestion(suggestion, session)
        await repo.update_status(suggestion_id, "accepted")
        await session.commit()

        return {
            "status": "accepted",
            "proposal_id": result.get("proposal_id"),
            "proposal_name": result.get("proposal_name"),
            "message": "Suggestion accepted. Proposal created for approval.",
        }

    except Exception as e:
        from src.api.utils import sanitize_error

        raise HTTPException(
            status_code=500,
            detail=sanitize_error(e, context="Create proposal from suggestion"),
        ) from e


@router.post("/suggestions/{suggestion_id}/reject")
@limiter.limit("10/minute")
async def reject_suggestion(
    request: Request,
    suggestion_id: str,
    data: SuggestionRejectRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reject an automation suggestion."""
    repo = AutomationSuggestionRepository(session)
    entity = await repo.get_by_id(suggestion_id)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Suggestion not found: {suggestion_id}",
        )
    if entity.status != "pending":
        raise HTTPException(status_code=409, detail="Suggestion already processed")

    await repo.update_status(suggestion_id, "rejected")
    await session.commit()

    return {
        "status": "rejected",
        "reason": data.reason,
    }


_NODE_LABELS: dict[str, tuple[str, str]] = {
    "collect_behavioral_data": ("data_scientist", "Collecting behavioral data from HA..."),
    "analyze_and_suggest": ("data_scientist", "Running analysis & generating script..."),
    "architect_review": ("architect", "Architect reviewing suggestions..."),
    "present_recommendations": ("data_scientist", "Compiling recommendations..."),
}


async def _run_optimization_background(
    job_id: str,
    data: OptimizationRequest,
) -> None:
    """Run optimization analysis in the background with granular events."""
    from src.graph.state import AgentRole, AnalysisState, AnalysisType
    from src.graph.workflows.optimization import build_optimization_graph
    from src.jobs import (
        emit_job_agent,
        emit_job_complete,
        emit_job_failed,
        emit_job_start,
        emit_job_status,
    )
    from src.storage import get_session

    type_map = {
        "behavior_analysis": AnalysisType.BEHAVIOR_ANALYSIS,
        "automation_analysis": AnalysisType.AUTOMATION_ANALYSIS,
        "automation_gap_detection": AnalysisType.AUTOMATION_GAP_DETECTION,
        "correlation_discovery": AnalysisType.CORRELATION_DISCOVERY,
        "device_health": AnalysisType.DEVICE_HEALTH,
        "cost_optimization": AnalysisType.COST_OPTIMIZATION,
    }

    types_str = ", ".join(t.value for t in data.analysis_types)
    title = f"Optimization ({types_str}, {data.hours}h)"
    emit_job_start(job_id, "optimization", title)

    async with get_session() as session:
        repo = OptimizationJobRepository(session)
        suggestion_repo = AutomationSuggestionRepository(session)

        await repo.update_status(job_id, "running")
        await session.commit()

        insights: list[dict[str, Any]] = []
        recommendations: list[str] = []
        suggestion_count = 0
        _active_agent: str | None = None

        try:
            for analysis_type in data.analysis_types:
                emit_job_status(job_id, f"Running {analysis_type.value}...")

                analysis_enum = type_map.get(analysis_type.value, AnalysisType.BEHAVIOR_ANALYSIS)
                graph = build_optimization_graph(session=session)
                compiled = graph.compile()

                initial_state = AnalysisState(
                    current_agent=AgentRole.DATA_SCIENTIST,
                    analysis_type=analysis_enum,
                    entity_ids=data.entity_ids or [],
                    time_range_hours=data.hours,
                )

                result_state: dict[str, object] = {}
                async for event in compiled.astream(
                    initial_state,
                    stream_mode="updates",  # type: ignore[arg-type]
                ):
                    for node_name, node_output in event.items():
                        agent, label = _NODE_LABELS.get(node_name, ("data_scientist", node_name))
                        if agent and agent != _active_agent:
                            if _active_agent:
                                emit_job_agent(job_id, _active_agent, "end")
                            emit_job_agent(job_id, agent, "start")
                            _active_agent = agent
                        emit_job_status(job_id, label)
                        if isinstance(node_output, dict):
                            result_state.update(node_output)

                if _active_agent:
                    emit_job_agent(job_id, _active_agent, "end")
                    _active_agent = None

                await session.commit()

                final = AnalysisState(
                    current_agent=AgentRole.DATA_SCIENTIST,
                    analysis_type=analysis_enum,
                    entity_ids=data.entity_ids or [],
                    time_range_hours=data.hours,
                    insights=result_state.get("insights", []),  # type: ignore[arg-type]
                    recommendations=result_state.get("recommendations", []),  # type: ignore[arg-type]
                    automation_suggestion=result_state.get("automation_suggestion"),  # type: ignore[arg-type]
                )

                insights.extend(final.insights or [])
                recommendations.extend(final.recommendations or [])

                if final.automation_suggestion:
                    emit_job_agent(job_id, "architect", "start")
                    emit_job_status(job_id, "Saving automation suggestion...")
                    await suggestion_repo.create(
                        {
                            "job_id": job_id,
                            "pattern": final.automation_suggestion.pattern,
                            "entities": final.automation_suggestion.entities,
                            "proposed_trigger": final.automation_suggestion.proposed_trigger,
                            "proposed_action": final.automation_suggestion.proposed_action,
                            "confidence": final.automation_suggestion.confidence,
                            "source_insight_type": final.automation_suggestion.source_insight_type,
                            "status": "pending",
                        }
                    )
                    suggestion_count += 1
                    emit_job_agent(job_id, "architect", "end")

            now = datetime.now(UTC)
            await repo.update_status(
                job_id,
                "completed",
                insight_count=len(insights),
                suggestion_count=suggestion_count,
                recommendations=recommendations or None,
                completed_at=now,
            )
            await session.commit()
            emit_job_complete(job_id)

        except Exception as e:
            logger.exception("Optimization job %s failed", job_id)
            if _active_agent:
                emit_job_agent(job_id, _active_agent, "end")
            # Roll back the tainted transaction so we can write the failure status.
            # Without this, a PendingRollbackError prevents the status update.
            await session.rollback()
            now = datetime.now(UTC)
            try:
                await repo.update_status(
                    job_id,
                    "failed",
                    error=str(e)[:2000],
                    completed_at=now,
                )
                await session.commit()
            except Exception:
                logger.warning("Could not persist failure status for job %s", job_id)
            emit_job_failed(job_id, str(e))
