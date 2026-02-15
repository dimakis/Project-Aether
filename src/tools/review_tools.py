"""Config review tools for the Architect agent (Feature 28).

Provides the review_config tool that triggers the Smart Config Review
workflow, analyzing existing HA configurations and suggesting improvements.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)


@tool("review_config")
@trace_with_uri(name="review.review_config", span_type="TOOL")
async def review_config(
    target: str,
    focus: str | None = None,
) -> str:
    """Review HA config and suggest improvements.

    Args:
        target: Entity ID or 'all_automations'/'all_scripts'/'all_scenes'
        focus: Focus area: energy, behavioral, efficiency, security
    """
    from src.graph.workflows import build_review_graph

    graph = build_review_graph()
    compiled = graph.compile()

    initial_state: dict[str, Any] = {
        "targets": [target],
        "focus": focus,
    }

    try:
        result = await compiled.ainvoke(initial_state)  # type: ignore[arg-type]
    except Exception:
        logger.exception("Review workflow failed for target=%s", target)
        return f"Error: Review workflow failed for '{target}'. Check logs for details."

    # Check for workflow-level error
    error = result.get("error")
    if error:
        return f"Error during review: {error}"

    # Summarize results
    suggestions = result.get("suggestions", [])
    if not suggestions:
        return f"Review of '{target}' completed. No improvement suggestions found."

    summary_parts = [f"Review of '{target}' completed with {len(suggestions)} suggestion(s):"]
    for i, suggestion in enumerate(suggestions, 1):
        entity_id = suggestion.get("entity_id", "unknown")
        notes = suggestion.get("review_notes", [])
        summary_parts.append(f"\n{i}. {entity_id}:")
        for note in notes:
            summary_parts.append(f"   - [{note.get('category', '?')}] {note.get('change', '?')}")

    summary_parts.append("\nReview proposals have been created and are awaiting approval.")
    return "\n".join(summary_parts)
