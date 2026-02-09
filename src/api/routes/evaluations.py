"""Trace evaluation API routes.

Exposes MLflow 3.x GenAI evaluation results for the UI to display
quality trends and scorer outcomes over time.

Feature: MLflow 3.x observability upgrade.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


class ScorerResult(BaseModel):
    """Result for a single scorer across all evaluated traces."""

    name: str = Field(description="Scorer name")
    pass_count: int = Field(default=0, description="Number of traces that passed")
    fail_count: int = Field(default=0, description="Number of traces that failed")
    error_count: int = Field(default=0, description="Number of scorer errors")
    pass_rate: float | None = Field(default=None, description="Pass rate (0-1)")
    avg_value: float | None = Field(default=None, description="Average numeric value")


class EvaluationSummary(BaseModel):
    """Summary of an evaluation run."""

    run_id: str | None = Field(default=None, description="MLflow evaluation run ID")
    trace_count: int = Field(default=0, description="Number of traces evaluated")
    scorer_results: list[ScorerResult] = Field(
        default_factory=list, description="Per-scorer results"
    )
    evaluated_at: str | None = Field(default=None, description="ISO-8601 timestamp")


class EvaluationTriggerResponse(BaseModel):
    """Response from triggering an on-demand evaluation."""

    status: str = Field(description="'started' or 'error'")
    trace_count: int = Field(default=0, description="Number of traces found")
    message: str = Field(description="Status message")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=EvaluationSummary)
async def get_evaluation_summary() -> EvaluationSummary:
    """Get the latest evaluation summary from MLflow.

    Searches for the most recent evaluation run and returns
    aggregated scorer results for the UI.
    """
    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        from src.settings import get_settings

        settings = get_settings()
        client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)

        # Search for evaluation runs (tagged by mlflow.genai.evaluate)
        experiment = mlflow.get_experiment_by_name(settings.mlflow_experiment_name)
        if experiment is None:
            return EvaluationSummary()

        # Search for runs with evaluation metrics
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="tags.`mlflow.runName` LIKE '%evaluate%'",
            order_by=["start_time DESC"],
            max_results=1,
        )

        if not runs:
            return EvaluationSummary()

        latest_run = runs[0]
        scorer_results = _extract_scorer_results(latest_run)

        return EvaluationSummary(
            run_id=latest_run.info.run_id,
            trace_count=int(latest_run.data.metrics.get("trace_count", 0)),
            scorer_results=scorer_results,
            evaluated_at=datetime.fromtimestamp(
                latest_run.info.start_time / 1000, tz=UTC
            ).isoformat()
            if latest_run.info.start_time
            else None,
        )

    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="MLflow not available",
        ) from exc
    except Exception as e:
        logger.debug("Failed to get evaluation summary: %s", e)
        return EvaluationSummary()


@router.post("/run", response_model=EvaluationTriggerResponse)
async def trigger_evaluation(
    max_traces: int = 50,
) -> EvaluationTriggerResponse:
    """Trigger an on-demand trace evaluation.

    Runs all custom scorers against recent traces and logs
    results to MLflow. This is the same evaluation that runs
    nightly via the scheduler.
    """
    try:
        import mlflow
        import mlflow.genai

        from src.settings import get_settings
        from src.tracing import init_mlflow
        from src.tracing.scorers import get_all_scorers

        client = init_mlflow()
        if client is None:
            return EvaluationTriggerResponse(
                status="error",
                message="MLflow not available",
            )

        settings = get_settings()
        scorers = get_all_scorers()
        if not scorers:
            return EvaluationTriggerResponse(
                status="error",
                message="No scorers available",
            )

        # Search for recent traces
        trace_df = mlflow.search_traces(
            experiment_names=[settings.mlflow_experiment_name],
            max_results=max_traces,
        )

        if trace_df is None or len(trace_df) == 0:
            return EvaluationTriggerResponse(
                status="error",
                trace_count=0,
                message="No traces found to evaluate",
            )

        # Run evaluation
        mlflow.genai.evaluate(
            data=trace_df,
            scorers=scorers,
        )

        return EvaluationTriggerResponse(
            status="started",
            trace_count=len(trace_df),
            message=f"Evaluated {len(trace_df)} traces with {len(scorers)} scorers",
        )

    except Exception as e:
        from src.api.utils import sanitize_error

        return EvaluationTriggerResponse(
            status="error",
            message=sanitize_error(e, context="Trigger evaluation"),
        )


@router.get("/scorers")
async def list_scorers() -> dict[str, Any]:
    """List available scorers and their descriptions."""
    from src.tracing.scorers import get_all_scorers

    scorers = get_all_scorers()
    return {
        "count": len(scorers),
        "scorers": [
            {
                "name": getattr(s, "__name__", str(s)),
                "description": (getattr(s, "__doc__", "") or "").strip().split("\n")[0],
            }
            for s in scorers
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_scorer_results(run: Any) -> list[ScorerResult]:
    """Extract per-scorer results from an MLflow evaluation run.

    MLflow 3.x stores evaluation metrics with scorer-prefixed keys
    in the run metrics.
    """
    results: dict[str, ScorerResult] = {}
    metrics = getattr(getattr(run, "data", None), "metrics", {}) or {}

    for key, value in metrics.items():
        # MLflow evaluation metrics are typically named like:
        # scorer_name/pass_rate, scorer_name/mean, etc.
        parts = key.split("/")
        if len(parts) >= 2:
            scorer_name = parts[0]
            metric_type = "/".join(parts[1:])

            if scorer_name not in results:
                results[scorer_name] = ScorerResult(name=scorer_name)

            sr = results[scorer_name]
            if "pass_rate" in metric_type:
                sr.pass_rate = float(value)
            elif "mean" in metric_type or "avg" in metric_type:
                sr.avg_value = float(value)
        elif key.endswith("_pass_rate"):
            scorer_name = key.replace("_pass_rate", "")
            if scorer_name not in results:
                results[scorer_name] = ScorerResult(name=scorer_name)
            results[scorer_name].pass_rate = float(value)

    return list(results.values())
