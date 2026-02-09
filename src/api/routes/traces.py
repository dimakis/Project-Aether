"""Trace visualization API for the Agent Activity panel.

Feature 11: Live Agent Activity Trace.

Exposes MLflow trace data in a format suitable for the frontend
agent topology and timeline visualization.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/traces", tags=["Traces"])


# ─── Response Schemas ─────────────────────────────────────────────────────────


class SpanNode(BaseModel):
    """A single span in the trace tree."""

    span_id: str
    name: str
    agent: str  # architect, data_scientist, energy_analyst, behavioral_analyst, diagnostic_analyst, dashboard_designer, sandbox, librarian, developer, system
    type: str  # chain, llm, tool, retriever, unknown
    start_ms: float  # ms offset from trace start
    end_ms: float
    duration_ms: float
    status: str  # OK, ERROR
    attributes: dict[str, Any] = {}
    children: list[SpanNode] = []


class TraceResponse(BaseModel):
    """Full trace tree for the activity panel."""

    trace_id: str
    status: str
    duration_ms: float
    started_at: str | None = None  # ISO-8601 wall-clock start time
    root_span: SpanNode | None = None
    agents_involved: list[str] = []  # Unique agents seen in the trace
    span_count: int = 0


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/{trace_id}/spans", response_model=TraceResponse)
async def get_trace_spans(trace_id: str) -> TraceResponse:
    """Get the span tree for a trace, formatted for the Agent Activity panel.

    Reads from MLflow's trace storage and transforms the flat span list
    into a nested tree with agent identification and relative timing.
    """
    try:
        from mlflow.tracking import MlflowClient

        from src.settings import get_settings

        settings = get_settings()
        client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    except Exception as e:
        from src.api.utils import sanitize_error

        raise HTTPException(
            status_code=503,
            detail=sanitize_error(e, context="MLflow connection"),
        ) from e

    try:
        trace = client.get_trace(trace_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail="Trace not found",
        ) from e

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    # Extract spans from the trace
    try:
        spans = trace.data.spans if hasattr(trace, "data") and hasattr(trace.data, "spans") else []
    except Exception:
        spans = []

    if not spans:
        return TraceResponse(
            trace_id=trace_id,
            status=_get_trace_status(trace),
            duration_ms=_get_trace_duration(trace),
            started_at=None,
            root_span=None,
            agents_involved=[],
            span_count=0,
        )

    # Build the span tree
    root_span, agents = _build_span_tree(spans, trace)

    # Compute wall-clock start as ISO-8601
    trace_start_ns = _get_trace_start_ns(trace, spans)
    started_at = _ns_to_iso(trace_start_ns) if trace_start_ns > 0 else None

    return TraceResponse(
        trace_id=trace_id,
        status=_get_trace_status(trace),
        duration_ms=_get_trace_duration(trace),
        started_at=started_at,
        root_span=root_span,
        agents_involved=sorted(agents),
        span_count=len(spans),
    )


# ─── Agent Identification ─────────────────────────────────────────────────────

# Patterns for identifying which agent a span belongs to.
# Order matters: more specific patterns must come before generic ones
# (e.g. "EnergyAnalyst" before "data.?scientist").
_AGENT_PATTERNS: list[tuple[str, str]] = [
    # DS team specialists (must be before generic data_scientist)
    (r"(?i)energy.?analyst|EnergyAnalyst|energy_analysis", "energy_analyst"),
    (r"(?i)behavio(?:u?r)al.?analyst|BehavioralAnalyst|behavioral_analysis", "behavioral_analyst"),
    (r"(?i)diagnostic.?analyst|DiagnosticAnalyst|diagnostic_analysis", "diagnostic_analyst"),
    # Dashboard designer
    (r"(?i)dashboard.?designer|Dashboard Designer", "dashboard_designer"),
    # Core agents
    (r"(?i)architect", "architect"),
    (r"(?i)data.?scientist|DataScientist|analyze_energy|analyze_behav", "data_scientist"),
    (r"(?i)sandbox|script.?exec", "sandbox"),
    (r"(?i)librarian|discover", "librarian"),
    (r"(?i)developer|deploy", "developer"),
]

# Valid agent role values emitted by BaseAgent.trace_span as the
# "agent_role" span attribute.  Used for authoritative identification.
_KNOWN_AGENT_ROLES: set[str] = {
    "architect",
    "data_scientist",
    "energy_analyst",
    "behavioral_analyst",
    "diagnostic_analyst",
    "dashboard_designer",
    "sandbox",
    "librarian",
    "developer",
}


def _identify_agent(
    span_name: str,
    span_type: str,
    parent_agent: str | None = None,
    span_attrs: dict[str, Any] | None = None,
) -> str:
    """Identify which agent a span belongs to.

    Uses a resolution chain:
    1. Explicit ``agent_role`` attribute set by BaseAgent.trace_span (most reliable)
    2. Regex pattern match on span name
    3. LLM / chat-model spans inherit their parent agent
    4. Fall back to parent agent or ``"system"``
    """
    # 1. Authoritative: check span attributes for agent_role
    if span_attrs:
        role = span_attrs.get("agent_role") or span_attrs.get("agent")
        if role:
            role_lower = str(role).lower()
            # Handle class-style names like "EnergyAnalyst" → "energy_analyst"
            role_snake = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", str(role)).lower().strip()
            for candidate in (role_lower, role_snake):
                if candidate in _KNOWN_AGENT_ROLES:
                    return candidate

    # 2. Pattern match on span name
    for pattern, agent in _AGENT_PATTERNS:
        if re.search(pattern, span_name):
            return agent

    # 3. LLM spans inherit their parent agent
    if span_type.lower() in ("llm", "chat_model") and parent_agent:
        return parent_agent

    return parent_agent or "system"


# ─── Tree Building ────────────────────────────────────────────────────────────


def _build_span_tree(
    spans: list[Any],
    trace: Any,
) -> tuple[SpanNode | None, set[str]]:
    """Build a nested SpanNode tree from MLflow's flat span list.

    Returns:
        (root SpanNode, set of agent names involved)
    """
    # Find the earliest start time for relative offset
    trace_start = _get_trace_start_ns(trace, spans)

    # Index spans by ID
    span_map: dict[str, Any] = {}
    for span in spans:
        span_id = _get_span_id(span)
        if span_id:
            span_map[span_id] = span

    # Build parent→children mapping
    children_map: dict[str, list[str]] = {}
    root_id: str | None = None

    for span in spans:
        span_id = _get_span_id(span)
        if not span_id:
            continue
        parent_id = _get_parent_id(span)

        if parent_id and parent_id in span_map:
            children_map.setdefault(parent_id, []).append(span_id)
        elif (not parent_id or parent_id not in span_map) and root_id is None:
            # Root span (no parent or parent not in this trace)
            root_id = span_id

    if not root_id:
        # Fallback: use the first span
        root_id = _get_span_id(spans[0]) if spans else None

    if not root_id:
        return None, set()

    agents: set[str] = set()

    def _build_node(span_id: str, parent_agent: str | None = None) -> SpanNode:
        span = span_map[span_id]
        name = _get_span_name(span)
        span_type = _get_span_type(span)
        raw_attrs = getattr(span, "attributes", None) or {}
        agent = _identify_agent(name, span_type, parent_agent, span_attrs=raw_attrs)
        agents.add(agent)

        start_ns = _get_start_time(span)
        end_ns = _get_end_time(span)
        start_ms = max(0, (start_ns - trace_start) / 1e6)
        end_ms = max(start_ms, (end_ns - trace_start) / 1e6)

        child_ids = children_map.get(span_id, [])
        child_nodes = [_build_node(cid, agent) for cid in child_ids if cid in span_map]
        # Sort children by start time
        child_nodes.sort(key=lambda n: n.start_ms)

        # Extract useful attributes
        attrs = _extract_attributes(span)

        return SpanNode(
            span_id=span_id,
            name=name,
            agent=agent,
            type=span_type,
            start_ms=round(start_ms, 1),
            end_ms=round(end_ms, 1),
            duration_ms=round(end_ms - start_ms, 1),
            status=_get_span_status(span),
            attributes=attrs,
            children=child_nodes,
        )

    root = _build_node(root_id)
    return root, agents


# ─── MLflow Span Accessors (defensive) ────────────────────────────────────────
# MLflow span objects have different APIs across versions, so we
# access attributes defensively.


def _get_span_id(span: Any) -> str | None:
    """Get span ID from various MLflow span formats."""
    for attr in ("span_id", "context", "_span_id"):
        val = getattr(span, attr, None)
        if isinstance(val, str):
            return val
        if val and hasattr(val, "span_id"):
            return str(val.span_id)
    return None


def _get_parent_id(span: Any) -> str | None:
    """Get parent span ID."""
    for attr in ("parent_id", "_parent_id"):
        val = getattr(span, attr, None)
        if val:
            return str(val)
    # Check context
    ctx = getattr(span, "context", None)
    if ctx and hasattr(ctx, "parent_id"):
        parent = ctx.parent_id
        return str(parent) if parent else None
    return None


def _get_span_name(span: Any) -> str:
    return str(getattr(span, "name", "unknown"))


def _get_span_type(span: Any) -> str:
    st = getattr(span, "span_type", None) or getattr(span, "type", "unknown")
    return str(st).lower()


def _get_span_status(span: Any) -> str:
    status = getattr(span, "status", None)
    if status is None:
        return "OK"
    if hasattr(status, "status_code"):
        return (
            str(status.status_code.name)
            if hasattr(status.status_code, "name")
            else str(status.status_code)
        )
    return str(status)


def _get_start_time(span: Any) -> int:
    """Get start time in nanoseconds."""
    for attr in ("start_time_ns", "start_time"):
        val = getattr(span, attr, None)
        if val is not None:
            return int(val)
    return 0


def _get_end_time(span: Any) -> int:
    """Get end time in nanoseconds."""
    for attr in ("end_time_ns", "end_time"):
        val = getattr(span, attr, None)
        if val is not None:
            return int(val)
    return 0


def _get_trace_start_ns(trace: Any, spans: list[Any]) -> int:
    """Get the earliest start time across all spans."""
    starts = [_get_start_time(s) for s in spans if _get_start_time(s) > 0]
    return min(starts) if starts else 0


def _ns_to_iso(ns: int) -> str:
    """Convert nanosecond timestamp to ISO-8601 string."""
    from datetime import datetime

    return datetime.fromtimestamp(ns / 1e9, tz=UTC).isoformat()


def _get_trace_status(trace: Any) -> str:
    info = getattr(trace, "info", None)
    if info:
        status = getattr(info, "status", None)
        if status:
            return str(status)
    return "OK"


def _get_trace_duration(trace: Any) -> float:
    info = getattr(trace, "info", None)
    if info:
        duration = getattr(info, "execution_time_ms", None)
        if duration:
            return float(duration)
    return 0.0


def _extract_attributes(span: Any) -> dict[str, Any]:
    """Extract useful display attributes from a span."""
    attrs: dict[str, Any] = {}
    raw = getattr(span, "attributes", None) or {}

    # Common useful attributes
    for key in ("model", "model_name", "llm.model", "openai.model"):
        if key in raw:
            attrs["model"] = str(raw[key])
            break

    for key in ("llm.token_count", "token_count", "total_tokens"):
        if key in raw:
            attrs["tokens"] = int(raw[key])
            break

    for key in ("tool.name", "tool_name"):
        if key in raw:
            attrs["tool"] = str(raw[key])
            break

    return attrs
