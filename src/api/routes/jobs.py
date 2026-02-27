"""Jobs API — list recent jobs from MLflow traces.

Provides a unified job list for the activity panel by mapping MLflow
traces/runs to a job-like structure.  No separate DB table; MLflow
is the single source of truth for execution history.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])

_RUN_NAME_TO_JOB_TYPE: dict[str, str] = {
    "conversation_workflow": "chat",
    "conversation_workflow_resume": "chat",
    "analysis_workflow": "analysis",
    "optimization_workflow": "optimization",
    "discovery_workflow": "discovery",
    "data_scientist_analysis": "analysis",
    "librarian_discovery": "discovery",
}


def _resolve_job_type(run_name: str) -> str:
    """Map MLflow run name to a job type string."""
    for prefix, jtype in _RUN_NAME_TO_JOB_TYPE.items():
        if run_name.startswith(prefix):
            return jtype
    return "other"


def _resolve_status(raw_status: str) -> str:
    """Map MLflow trace status to a job status."""
    upper = raw_status.upper()
    if upper == "OK":
        return "completed"
    if upper in ("ERROR", "ERROR_STATUS"):
        return "failed"
    if upper in ("IN_PROGRESS", "RUNNING"):
        return "running"
    return "completed"


def _map_trace_to_job(trace: Any) -> dict[str, Any]:
    """Convert an MLflow trace object to a job dict for the frontend."""
    info = trace.info
    tags: dict[str, str] = getattr(info, "tags", {}) or {}

    raw_status = info.status.value if hasattr(info.status, "value") else str(info.status)
    run_name = tags.get("mlflow.runName", "")

    return {
        "job_id": info.request_id,
        "job_type": _resolve_job_type(run_name),
        "status": _resolve_status(raw_status),
        "title": run_name.replace("_", " ").title() if run_name else "Unknown",
        "started_at": info.timestamp_ms,
        "duration_ms": info.execution_time_ms,
        "conversation_id": tags.get("mlflow.trace.session") or tags.get("conversation_id"),
        "run_name": run_name,
    }


@router.get("")
async def list_jobs(
    limit: int = 20,
    job_type: str | None = None,
) -> dict[str, Any]:
    """List recent jobs from MLflow traces.

    Args:
        limit: Maximum number of jobs to return.
        job_type: Optional filter by job type (chat, analysis, optimization, etc.).
    """
    try:
        from mlflow.tracking import MlflowClient

        from src.settings import get_settings

        settings = get_settings()
        client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)

        experiment = client.get_experiment_by_name(settings.mlflow_experiment_name)
        if experiment is None:
            return {"jobs": [], "total": 0}

        traces = client.search_traces(
            experiment_ids=[experiment.experiment_id],
            max_results=limit,
            order_by=["timestamp_ms DESC"],
        )

        jobs = [_map_trace_to_job(t) for t in traces]

        if job_type:
            jobs = [j for j in jobs if j["job_type"] == job_type]

        return {"jobs": jobs, "total": len(jobs)}

    except ImportError as exc:
        raise HTTPException(status_code=503, detail="MLflow not available") from exc
    except Exception as e:
        logger.warning("Failed to fetch jobs from MLflow: %s", e)
        return {"jobs": [], "total": 0}
