"""Diagnostics API endpoints.

Exposes HA health checks, error log analysis, config validation,
and recent agent trace summaries.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from src.diagnostics.config_validator import run_config_check
from src.diagnostics.entity_health import (
    find_stale_entities,
    find_unavailable_entities,
)
from src.diagnostics.error_patterns import analyze_errors
from src.diagnostics.integration_health import (
    find_unhealthy_integrations,
)
from src.diagnostics.log_parser import (
    categorize_by_integration,
    get_error_summary,
    parse_error_log,
)
from src.ha import get_ha_client
from src.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


# =============================================================================
# HA Health
# =============================================================================


@router.get("/ha-health")
async def ha_health() -> dict[str, Any]:
    """Home Assistant health: unavailable/stale entities & unhealthy integrations."""
    try:
        ha = get_ha_client()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to Home Assistant",
        ) from e

    unavailable = await find_unavailable_entities(ha)
    stale = await find_stale_entities(ha)
    unhealthy = await find_unhealthy_integrations(ha)

    return {
        "unavailable_entities": [asdict(e) for e in unavailable],
        "stale_entities": [asdict(e) for e in stale],
        "unhealthy_integrations": [asdict(i) for i in unhealthy],
        "summary": {
            "unavailable_count": len(unavailable),
            "stale_count": len(stale),
            "unhealthy_integration_count": len(unhealthy),
        },
    }


# =============================================================================
# Error Log
# =============================================================================


@router.get("/error-log")
async def error_log() -> dict[str, Any]:
    """Parsed HA error log with summary and known pattern matching."""
    try:
        ha = get_ha_client()
        raw_log = await ha.get_error_log()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Unable to fetch error log from Home Assistant",
        ) from e

    entries = parse_error_log(raw_log)
    summary = get_error_summary(entries)
    by_integration = categorize_by_integration(entries)
    known_patterns = analyze_errors(entries)

    # Serialize by_integration: integration -> list of entry dicts
    serialized_by_int = {}
    for integration, int_entries in by_integration.items():
        serialized_by_int[integration] = [asdict(e) for e in int_entries]

    return {
        "summary": summary,
        "by_integration": serialized_by_int,
        "known_patterns": known_patterns,
        "entry_count": len(entries),
    }


# =============================================================================
# Config Check
# =============================================================================


@router.get("/config-check")
async def config_check() -> dict[str, Any]:
    """Run HA config validation."""
    try:
        ha = get_ha_client()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to Home Assistant",
        ) from e

    result = await run_config_check(ha)

    return {
        "valid": result.result == "valid",
        "result": result.result,
        "errors": result.errors,
        "warnings": result.warnings,
    }


# =============================================================================
# Recent Traces
# =============================================================================

# Lazy import to avoid hard dependency on mlflow at module level
MlflowClient: Any = None


def _get_mlflow_client() -> Any:
    """Get an MLflow client, importing lazily."""
    global MlflowClient
    if MlflowClient is None:
        from mlflow.tracking import MlflowClient as _MlflowClient

        MlflowClient = _MlflowClient

    settings = get_settings()
    return MlflowClient(tracking_uri=settings.mlflow_tracking_uri)


@router.get("/traces/recent")
async def recent_traces(limit: int = 50) -> dict[str, Any]:
    """Get recent agent traces from MLflow."""
    try:
        client = _get_mlflow_client()
    except Exception:
        # MLflow not available -- return empty
        return {"traces": [], "total": 0}

    try:
        settings = get_settings()
        experiment_name = settings.mlflow_experiment_name

        # Resolve experiment name to ID (MLflow 3.x API)
        experiment = client.get_experiment_by_name(experiment_name)
        if experiment is None:
            return {"traces": [], "total": 0}

        traces = client.search_traces(
            experiment_ids=[experiment.experiment_id],
            max_results=limit,
            order_by=["timestamp_ms DESC"],
        )

        items = []
        for t in traces:
            info = t.info
            items.append(
                {
                    "trace_id": info.request_id,
                    "status": info.status.value
                    if hasattr(info.status, "value")
                    else str(info.status),
                    "timestamp_ms": info.timestamp_ms,
                    "duration_ms": info.execution_time_ms,
                }
            )

        return {"traces": items, "total": len(items)}

    except Exception as e:
        logger.warning("Failed to fetch recent traces: %s", e)
        return {"traces": [], "total": 0}
