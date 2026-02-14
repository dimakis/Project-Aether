"""Workflow implementation for the Data Science team agent."""

from typing import TYPE_CHECKING, Any, cast

from src.graph.state import AgentRole, AnalysisState, AnalysisType
from src.ha import HAClient
from src.settings import get_settings
from src.tracing import get_active_run, log_metric, log_param, start_experiment_run

from .agent import DataScientistAgent

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DataScientistWorkflow:
    """Workflow implementation for the Data Science team agent.

    Orchestrates the analysis process:
    1. Initialize analysis state
    2. Collect energy data
    3. Generate and execute analysis script
    4. Extract and persist insights
    5. Return results
    """

    def __init__(
        self,
        ha_client: HAClient | None = None,
    ):
        """Initialize the Data Science team workflow.

        Args:
            ha_client: Optional HA client
        """
        self._settings = get_settings()
        self.agent = DataScientistAgent(ha_client=ha_client)

    async def run_analysis(
        self,
        analysis_type: AnalysisType = AnalysisType.ENERGY_OPTIMIZATION,
        entity_ids: list[str] | None = None,
        hours: int = 24,
        custom_query: str | None = None,
        diagnostic_context: str | None = None,
        session: "AsyncSession | None" = None,
    ) -> AnalysisState:
        """Execute an energy analysis.

        Args:
            analysis_type: Type of analysis to perform
            entity_ids: Specific entities to analyze (None = all energy sensors)
            hours: Hours of history to analyze
            custom_query: Custom analysis request
            diagnostic_context: Pre-collected diagnostic data from Architect
                (logs, history observations, config issues) for DIAGNOSTIC mode
            session: Database session for persistence

        Returns:
            Final analysis state with results
        """
        import mlflow as _mlflow

        # Initialize state
        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=analysis_type,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=custom_query,
            diagnostic_context=diagnostic_context,
        )

        # If there's already an active run/trace (e.g. from a conversation tool call),
        # create a span within it so the Data Scientist shows up in the agent activity
        # panel. Only create a new run when called standalone (e.g. from /insights/analyze).
        active_run = get_active_run()

        if active_run:
            # Within existing trace: create a child span (visible in agent activity)
            return await self._run_within_trace(state, session, _mlflow)
        else:
            # Standalone: create a new MLflow run
            return await self._run_standalone(state, session, analysis_type, entity_ids, hours)

    async def _run_within_trace(
        self,
        state: AnalysisState,
        session: "AsyncSession | None",
        _mlflow: Any,
    ) -> AnalysisState:
        """Run analysis within an existing MLflow trace (e.g. conversation tool call)."""
        # Capture the run ID from the active run
        active_run = get_active_run()
        if active_run:
            state.mlflow_run_id = active_run.info.run_id if hasattr(active_run, "info") else None

        @_mlflow.trace(
            name="DataScientist.run_analysis",
            span_type="CHAIN",
            attributes={
                "analysis_type": state.analysis_type.value,
                "hours": state.time_range_hours,
                "entity_count": len(state.entity_ids),
            },
        )
        async def _traced_analysis() -> AnalysisState:
            updates = await self.agent.invoke(state, session=session)
            for key, value in updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            return state

        try:
            return cast("AnalysisState", await _traced_analysis())
        except Exception as e:
            state.insights.append(
                {
                    "type": "error",
                    "title": "Analysis Failed",
                    "description": str(e),
                    "confidence": 0.0,
                    "impact": "low",
                    "evidence": {},
                    "entities": [],
                }
            )
            raise

    async def _run_standalone(
        self,
        state: AnalysisState,
        session: "AsyncSession | None",
        analysis_type: AnalysisType,
        entity_ids: list[str] | None,
        hours: int,
    ) -> AnalysisState:
        """Run analysis as a standalone MLflow run (e.g. from /insights/analyze)."""
        with start_experiment_run(run_name="data_scientist_analysis") as run:
            if run:
                state.mlflow_run_id = run.info.run_id if hasattr(run, "info") else None

            log_param("analysis_type", analysis_type.value)
            log_param("hours", hours)
            log_param("entity_count", len(entity_ids) if entity_ids else "auto")

            try:
                updates = await self.agent.invoke(state, session=session)

                for key, value in updates.items():
                    if hasattr(state, key):
                        setattr(state, key, value)

                log_metric("insights.count", float(len(state.insights)))
                log_metric("recommendations.count", float(len(state.recommendations)))

            except Exception as e:
                log_param("error", str(e)[:500])
                state.insights.append(
                    {
                        "type": "error",
                        "title": "Analysis Failed",
                        "description": str(e),
                        "confidence": 0.0,
                        "impact": "low",
                        "evidence": {},
                        "entities": [],
                    }
                )
                raise

        return state
