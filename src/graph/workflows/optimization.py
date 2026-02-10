"""Optimization workflow - behavioural analysis & multi-agent collaboration.

Feature 03: Intelligent Optimization & Multi-Agent Collaboration.
Combines DS analysis with Architect proposal generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.ha.client import HAClient

from src.graph import END, START, StateGraph, create_graph
from src.graph.state import AgentRole, AnalysisState, AnalysisType


def build_optimization_graph(
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
) -> StateGraph:
    """Build the optimization workflow graph.

    Graph structure:
    ```
    START
      │
      ▼
    collect_behavioral_data
      │
      ▼
    analyze_and_suggest
      │
      ▼
    [has suggestion?]──No──► present_recommendations ──► END
      │ Yes
      ▼
    architect_review
      │
      ▼
    present_recommendations
      │
      ▼
    END
    ```

    Feature 03: Intelligent Optimization & Multi-Agent Collaboration.

    Args:
        ha_client: Optional HA client to inject
        session: Optional database session

    Returns:
        Configured StateGraph
    """
    from src.graph.nodes import (
        analyze_and_suggest_node,
        architect_review_node,
        collect_behavioral_data_node,
        present_recommendations_node,
    )

    graph = create_graph(AnalysisState)

    # Node wrappers with dependency injection
    async def _collect_behavioral(state: AnalysisState) -> dict[str, object]:
        return await collect_behavioral_data_node(state, ha_client=ha_client)

    async def _analyze_and_suggest(state: AnalysisState) -> dict[str, object]:
        return await analyze_and_suggest_node(state, session=session)

    async def _architect_review(state: AnalysisState) -> dict[str, object]:
        return await architect_review_node(state, session=session)

    async def _present_recommendations(state: AnalysisState) -> dict[str, object]:
        return await present_recommendations_node(state)

    # Add nodes
    graph.add_node("collect_behavioral_data", _collect_behavioral)
    graph.add_node("analyze_and_suggest", _analyze_and_suggest)
    graph.add_node("architect_review", _architect_review)
    graph.add_node("present_recommendations", _present_recommendations)

    # Define flow
    graph.add_edge(START, "collect_behavioral_data")
    graph.add_edge("collect_behavioral_data", "analyze_and_suggest")

    # Conditional routing: if there's an automation suggestion, go to architect
    def route_after_analysis(state: AnalysisState) -> str:
        if state.automation_suggestion:
            return "architect_review"
        return "present_recommendations"

    graph.add_conditional_edges(
        "analyze_and_suggest",
        route_after_analysis,
        {
            "architect_review": "architect_review",
            "present_recommendations": "present_recommendations",
        },
    )
    graph.add_edge("architect_review", "present_recommendations")
    graph.add_edge("present_recommendations", END)

    return graph


async def run_optimization_workflow(
    analysis_type: str = "behavior_analysis",
    entity_ids: list[str] | None = None,
    hours: int = 168,
    custom_query: str | None = None,
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
) -> AnalysisState:
    """Run an optimization analysis workflow.

    Entry point for behavioral analysis and optimization.
    Combines DS analysis with Architect proposal generation.

    Feature 03: Intelligent Optimization.

    Args:
        analysis_type: Type of analysis
        entity_ids: Specific entities (None = auto-discover)
        hours: Hours of history (default: 1 week)
        custom_query: Optional custom analysis query
        ha_client: Optional HA client
        session: Optional database session

    Returns:
        Final analysis state
    """
    from src.tracing import log_metric, log_param
    from src.tracing.context import session_context

    # Map string to enum
    type_map = {
        "behavior_analysis": AnalysisType.BEHAVIOR_ANALYSIS,
        "automation_analysis": AnalysisType.AUTOMATION_ANALYSIS,
        "automation_gap_detection": AnalysisType.AUTOMATION_GAP_DETECTION,
        "correlation_discovery": AnalysisType.CORRELATION_DISCOVERY,
        "device_health": AnalysisType.DEVICE_HEALTH,
        "cost_optimization": AnalysisType.COST_OPTIMIZATION,
    }
    analysis_enum = type_map.get(analysis_type, AnalysisType.BEHAVIOR_ANALYSIS)

    with session_context():
        log_param("workflow", "optimization")
        log_param("analysis_type", analysis_type)
        log_param("hours", hours)

        # Build and compile graph
        graph = build_optimization_graph(ha_client=ha_client, session=session)
        compiled = graph.compile()

        # Initialize state
        initial_state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=analysis_enum,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=custom_query,
        )

        # Execute
        final_state = await compiled.ainvoke(initial_state)  # type: ignore[arg-type]

        if isinstance(final_state, dict):
            result = initial_state.model_copy(update=final_state)
        else:
            result = final_state

        log_metric("optimization.insights", float(len(result.insights)))
        log_metric(
            "optimization.has_suggestion",
            1.0 if result.automation_suggestion else 0.0,
        )

        return result
