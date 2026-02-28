"""Analysis workflow - energy analysis pipeline.

Collects energy data, generates analysis scripts,
executes in sandbox, and extracts insights.
Constitution: Isolation - scripts run in gVisor sandbox.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import mlflow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.ha.client import HAClient

from src.graph import END, START, StateGraph, create_graph
from src.graph.nodes import (
    analysis_error_node,
    collect_energy_data_node,
    execute_sandbox_node,
    extract_insights_node,
    generate_script_node,
)
from src.graph.state import AnalysisState
from src.tracing import start_experiment_run, traced_node


def build_analysis_graph(
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
) -> StateGraph:
    """Build the energy analysis workflow graph.

    Graph structure:
    ```
    START
      │
      ▼
    collect_data
      │
      ▼
    generate_script
      │
      ▼
    execute_sandbox
      │
      ▼
    extract_insights
      │
      ▼
    END
    ```

    Constitution: Isolation - scripts run in gVisor sandbox.

    Args:
        ha_client: Optional HA client to inject
        session: Optional database session for insight persistence

    Returns:
        Configured StateGraph
    """
    graph = create_graph(AnalysisState)

    # Define node wrappers with dependency injection (traced for MLflow per-node spans)
    async def _collect_data(state: AnalysisState) -> dict[str, object]:
        return await collect_energy_data_node(state, ha_client=ha_client)

    async def _generate_script(state: AnalysisState) -> dict[str, object]:
        return await generate_script_node(state, session=session)

    async def _execute_sandbox(state: AnalysisState) -> dict[str, object]:
        return await execute_sandbox_node(state)

    async def _extract_insights(state: AnalysisState) -> dict[str, object]:
        return await extract_insights_node(state, session=session)

    async def _handle_error(state: AnalysisState) -> dict[str, object]:
        # Get error from state if available
        error = Exception("Unknown error")
        return await analysis_error_node(state, error)

    # Add nodes (traced for MLflow per-node spans)
    graph.add_node("collect_data", traced_node("collect_data", _collect_data))
    graph.add_node("generate_script", traced_node("generate_script", _generate_script))
    graph.add_node("execute_sandbox", traced_node("execute_sandbox", _execute_sandbox))
    graph.add_node("extract_insights", traced_node("extract_insights", _extract_insights))
    graph.add_node("error", traced_node("error", _handle_error))

    # Define flow
    graph.add_edge(START, "collect_data")
    graph.add_edge("collect_data", "generate_script")
    graph.add_edge("generate_script", "execute_sandbox")
    graph.add_edge("execute_sandbox", "extract_insights")
    graph.add_edge("extract_insights", END)
    graph.add_edge("error", END)

    return graph


@mlflow.trace(name="analysis_workflow", span_type="CHAIN")
async def run_analysis_workflow(
    analysis_type: str = "energy_optimization",
    entity_ids: list[str] | None = None,
    hours: int = 24,
    custom_query: str | None = None,
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
) -> AnalysisState:
    """Run an energy analysis workflow.

    Entry point for energy analysis. Starts a trace session
    for correlation across the workflow.

    Args:
        analysis_type: Type of analysis to perform
        entity_ids: Specific entities to analyze (None = auto-discover)
        hours: Hours of history to analyze
        custom_query: Custom analysis query
        ha_client: Optional HA client
        session: Database session for persistence

    Returns:
        Final analysis state with insights
    """
    from src.graph.state import AnalysisType
    from src.tracing.context import get_session_id, session_context

    # Map string to enum
    try:
        analysis_enum = AnalysisType(analysis_type)
    except ValueError:
        analysis_enum = AnalysisType.ENERGY_OPTIMIZATION

    # Build initial state
    initial_state = AnalysisState(
        analysis_type=analysis_enum,
        entity_ids=entity_ids or [],
        time_range_hours=hours,
        custom_query=custom_query,
    )

    # Build and compile graph
    graph = build_analysis_graph(ha_client=ha_client, session=session)
    compiled = graph.compile()

    # Run with tracing (inherit parent session if one exists)
    with (
        session_context(get_session_id()) as session_id,
        start_experiment_run("analysis_workflow") as run,
    ):
        if run:
            initial_state.mlflow_run_id = run.info.run_id if hasattr(run, "info") else None

        mlflow.update_current_trace(
            tags={
                "workflow": "analysis",
                **({"mlflow.trace.session": session_id} if session_id else {}),
            }
        )
        mlflow.set_tag("workflow", "analysis")
        mlflow.set_tag("session.id", session_id)
        mlflow.set_tag("analysis_type", analysis_type)

        final_state = await compiled.ainvoke(initial_state)  # type: ignore[arg-type]

        if isinstance(final_state, dict):
            return initial_state.model_copy(update=cast("dict[str, Any]", final_state))
        return cast("AnalysisState", final_state)
