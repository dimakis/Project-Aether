"""Internal runners for DS team specialists (thin wrappers around analyst invoke)."""

from __future__ import annotations

import logging

from src.agents.behavioral_analyst import BehavioralAnalyst
from src.agents.config_cache import is_agent_enabled
from src.agents.diagnostic_analyst import DiagnosticAnalyst
from src.agents.energy_analyst import EnergyAnalyst
from src.agents.execution_context import emit_progress
from src.agents.model_context import get_model_context, model_context
from src.graph.state import AnalysisDepth, AnalysisState, AnalysisType
from src.tools.specialist_routing import (
    _format_findings,
    _get_or_create_team_analysis,
    _set_team_analysis,
)
from src.tracing import get_active_span

logger = logging.getLogger(__name__)


def _capture_parent_span_context() -> tuple[str | None, float | None, str | None]:
    """Capture current model context + active span ID for trace propagation.

    Returns (model_name, temperature, parent_span_id) so that analyst
    spans appear as children of the coordinator span in the trace tree.
    """
    ctx = get_model_context()
    model_name = ctx.model_name if ctx else None
    temperature = ctx.temperature if ctx else None
    parent_span_id = None
    try:
        active_span = get_active_span()
        if active_span and hasattr(active_span, "span_id"):
            parent_span_id = active_span.span_id
    except Exception:
        logger.debug("Failed to get active span for parent span ID", exc_info=True)
    return model_name, temperature, parent_span_id


async def _run_energy(
    query: str, hours: int, entity_ids: list[str] | None, *, depth: str = "standard"
) -> str:
    """Run the Energy Analyst and return formatted findings."""
    if not await is_agent_enabled("energy_analyst"):
        return "Energy Analyst is currently disabled."
    emit_progress("agent_start", "energy_analyst", "Energy Analyst started")
    try:
        emit_progress(
            "status", "energy_analyst", f"Running energy analysis ({hours}h, depth={depth})..."
        )
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = EnergyAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
            depth=AnalysisDepth(depth),
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])
        return _format_findings(result)
    except Exception as e:
        logger.error("Energy analysis failed: %s", e, exc_info=True)
        return f"Energy analysis failed: {e}"
    finally:
        emit_progress("agent_end", "energy_analyst", "Energy Analyst completed")


async def _run_behavioral(
    query: str, hours: int, entity_ids: list[str] | None, *, depth: str = "standard"
) -> str:
    """Run the Behavioral Analyst and return formatted findings."""
    if not await is_agent_enabled("behavioral_analyst"):
        return "Behavioral Analyst is currently disabled."
    emit_progress("agent_start", "behavioral_analyst", "Behavioral Analyst started")
    try:
        emit_progress(
            "status",
            "behavioral_analyst",
            f"Running behavioral analysis ({hours}h, depth={depth})...",
        )
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = BehavioralAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
            depth=AnalysisDepth(depth),
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])
        return _format_findings(result)
    except Exception as e:
        logger.error("Behavioral analysis failed: %s", e, exc_info=True)
        return f"Behavioral analysis failed: {e}"
    finally:
        emit_progress("agent_end", "behavioral_analyst", "Behavioral Analyst completed")


async def _run_diagnostic(
    query: str, hours: int, entity_ids: list[str] | None, *, depth: str = "standard"
) -> str:
    """Run the Diagnostic Analyst and return formatted findings."""
    if not await is_agent_enabled("diagnostic_analyst"):
        return "Diagnostic Analyst is currently disabled."
    emit_progress("agent_start", "diagnostic_analyst", "Diagnostic Analyst started")
    try:
        emit_progress(
            "status",
            "diagnostic_analyst",
            f"Running diagnostic analysis ({hours}h, depth={depth})...",
        )
        model_name, temperature, parent_span_id = _capture_parent_span_context()
        analyst = DiagnosticAnalyst()
        ta = _get_or_create_team_analysis(query)
        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
            depth=AnalysisDepth(depth),
        )
        with model_context(
            model_name=model_name,
            temperature=temperature,
            parent_span_id=parent_span_id,
        ):
            result = await analyst.invoke(state)
        if result.get("team_analysis"):
            _set_team_analysis(result["team_analysis"])
        return _format_findings(result)
    except Exception as e:
        logger.error("Diagnostic analysis failed: %s", e, exc_info=True)
        return f"Diagnostic analysis failed: {e}"
    finally:
        emit_progress("agent_end", "diagnostic_analyst", "Diagnostic Analyst completed")
