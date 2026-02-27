"""Optimization API routes for intelligent analysis.

Feature 03: Intelligent Optimization & Multi-Agent Collaboration.

Provides endpoints for running behavioral analysis, viewing
automation suggestions, and accepting/rejecting suggestions.
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from src.api.rate_limit import limiter
from src.api.schemas.optimization import (
    OptimizationRequest,
    OptimizationResult,
    SuggestionAcceptRequest,
    SuggestionListResponse,
    SuggestionRejectRequest,
)

router = APIRouter(prefix="/optimize", tags=["Optimization"])

# In-memory store for optimization jobs and suggestions
# (In production, these would be persisted to the database)
_optimization_jobs: dict[str, OptimizationResult] = {}
_suggestions: dict[str, dict] = {}


@router.post("", response_model=OptimizationResult, status_code=202)
@limiter.limit("5/minute")
async def start_optimization(
    request: Request,
    data: OptimizationRequest,
    background_tasks: BackgroundTasks,
) -> OptimizationResult:
    """Run a full optimization analysis.

    Triggers behavioral analysis in the background. Returns a job
    that can be polled for completion.
    """
    job_id = str(uuid4())

    result = OptimizationResult(
        job_id=job_id,
        status="pending",
        analysis_types=[t.value for t in data.analysis_types],
        hours_analyzed=data.hours,
        insight_count=0,
        suggestion_count=0,
        started_at=datetime.now(UTC),
    )

    _optimization_jobs[job_id] = result
    background_tasks.add_task(
        _run_optimization_background,
        job_id,
        data,
    )

    return result


@router.get("/{job_id}", response_model=OptimizationResult)
async def get_optimization_status(job_id: str) -> OptimizationResult:
    """Get the status of an optimization job."""
    if job_id not in _optimization_jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return _optimization_jobs[job_id]


@router.get("/suggestions/list", response_model=SuggestionListResponse)
async def list_suggestions() -> SuggestionListResponse:
    """List all pending automation suggestions."""
    from src.api.schemas.optimization import AutomationSuggestionResponse, SuggestionStatus

    items = []
    for sid, data in _suggestions.items():
        items.append(
            AutomationSuggestionResponse(
                id=sid,
                pattern=data.get("pattern", ""),
                entities=data.get("entities", []),
                proposed_trigger=data.get("proposed_trigger", ""),
                proposed_action=data.get("proposed_action", ""),
                confidence=data.get("confidence", 0.0),
                source_insight_type=data.get("source_insight_type", ""),
                status=SuggestionStatus(data.get("status", "pending")),
                created_at=data.get("created_at", datetime.now(UTC)),
            )
        )

    return SuggestionListResponse(items=items, total=len(items))


@router.post("/suggestions/{suggestion_id}/accept")
@limiter.limit("10/minute")
async def accept_suggestion(
    request: Request,
    suggestion_id: str,
    data: SuggestionAcceptRequest,
) -> dict:
    """Accept an automation suggestion and create a proposal."""
    if suggestion_id not in _suggestions:
        raise HTTPException(status_code=404, detail=f"Suggestion not found: {suggestion_id}")

    suggestion_data = _suggestions[suggestion_id]
    if suggestion_data.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Suggestion already processed")

    # Create proposal via Architect
    try:
        from src.agents import ArchitectAgent
        from src.graph.state import AutomationSuggestion
        from src.storage import get_session

        suggestion = AutomationSuggestion(
            pattern=suggestion_data["pattern"],
            entities=suggestion_data.get("entities", []),
            proposed_trigger=suggestion_data.get("proposed_trigger", ""),
            proposed_action=suggestion_data.get("proposed_action", ""),
            confidence=suggestion_data.get("confidence", 0.0),
            evidence=suggestion_data.get("evidence", {}),
            source_insight_type=suggestion_data.get("source_insight_type", ""),
        )

        architect = ArchitectAgent()
        async with get_session() as session:
            result = await architect.receive_suggestion(suggestion, session)
            await session.commit()

        suggestion_data["status"] = "accepted"

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
) -> dict:
    """Reject an automation suggestion."""
    if suggestion_id not in _suggestions:
        raise HTTPException(status_code=404, detail=f"Suggestion not found: {suggestion_id}")

    suggestion_data = _suggestions[suggestion_id]
    if suggestion_data.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Suggestion already processed")

    suggestion_data["status"] = "rejected"
    suggestion_data["rejection_reason"] = data.reason

    return {
        "status": "rejected",
        "reason": data.reason,
    }


async def _run_optimization_background(
    job_id: str,
    data: OptimizationRequest,
) -> None:
    """Run optimization analysis in the background."""
    from src.graph.workflows import run_optimization_workflow
    from src.jobs import (
        emit_job_agent,
        emit_job_complete,
        emit_job_failed,
        emit_job_start,
        emit_job_status,
    )
    from src.storage import get_session

    title = f"Optimization ({', '.join(t.value for t in data.analysis_types)}, {data.hours}h)"
    emit_job_start(job_id, "optimization", title)

    job = _optimization_jobs[job_id]
    job.status = "running"

    try:
        async with get_session() as session:
            for analysis_type in data.analysis_types:
                emit_job_status(job_id, f"Running {analysis_type.value}...")
                emit_job_agent(job_id, "data_scientist", "start")

                state = await run_optimization_workflow(
                    analysis_type=analysis_type.value,
                    entity_ids=data.entity_ids,
                    hours=data.hours,
                    session=session,
                )
                await session.commit()

                emit_job_agent(job_id, "data_scientist", "end")

                job.insights.extend(state.insights or [])
                job.recommendations.extend(state.recommendations or [])

                if state.automation_suggestion:
                    emit_job_agent(job_id, "architect", "start")
                    suggestion_id = str(uuid4())
                    _suggestions[suggestion_id] = {
                        "pattern": state.automation_suggestion.pattern,
                        "entities": state.automation_suggestion.entities,
                        "proposed_trigger": state.automation_suggestion.proposed_trigger,
                        "proposed_action": state.automation_suggestion.proposed_action,
                        "confidence": state.automation_suggestion.confidence,
                        "evidence": state.automation_suggestion.evidence,
                        "source_insight_type": state.automation_suggestion.source_insight_type,
                        "status": "pending",
                        "created_at": datetime.now(UTC),
                    }
                    job.suggestion_count += 1
                    emit_job_agent(job_id, "architect", "end")

        job.insight_count = len(job.insights)
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        emit_job_complete(job_id)

    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.completed_at = datetime.now(UTC)
        emit_job_failed(job_id, str(e))
