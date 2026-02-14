"""Data Science team agent for energy analysis and insights.

User Story 3: Energy Optimization Suggestions.
Feature 03: Intelligent Optimization & Multi-Agent Collaboration.

The Data Science team analyzes energy data and behavioral patterns
from Home Assistant, generates Python scripts for analysis,
executes them in a sandboxed environment, and extracts actionable insights.

Constitution: Isolation - All scripts run in gVisor sandbox.
Constitution: Observability - All analysis traced in MLflow.
"""

from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents import BaseAgent
from src.agents.data_scientist.collectors import collect_behavioral_data, collect_energy_data
from src.agents.data_scientist.prompts import build_analysis_prompt
from src.agents.data_scientist.suggestions import generate_automation_suggestion
from src.agents.model_context import get_model_context, resolve_model
from src.agents.prompts import load_prompt
from src.dal import InsightRepository
from src.graph.state import AgentRole, AnalysisState, AutomationSuggestion
from src.ha import HAClient, get_ha_client
from src.llm import get_llm
from src.sandbox.runner import SandboxResult, SandboxRunner
from src.settings import get_settings
from src.storage.entities.insight import InsightType
from src.tracing import log_metric, log_param

from .constants import BEHAVIORAL_ANALYSIS_TYPES

logger = logging.getLogger(__name__)


class DataScientistAgent(BaseAgent):
    """The Data Science team agent for energy analysis.

    Responsibilities:
    - Analyze energy sensor data
    - Generate analysis scripts (Python)
    - Execute scripts in sandboxed environment
    - Extract and persist insights
    - Provide energy optimization recommendations
    """

    def __init__(
        self,
        ha_client: HAClient | None = None,
    ):
        """Initialize Data Science team agent.

        Args:
            ha_client: Optional HA client (creates one if not provided)
        """
        super().__init__(
            role=AgentRole.DATA_SCIENTIST,
            name="DataScientist",
        )
        self._ha_client = ha_client
        self._llm: BaseChatModel | None = None
        self._sandbox = SandboxRunner()

    @property
    def ha(self) -> HAClient:
        """Get HA client, creating if needed."""
        if self._ha_client is None:
            self._ha_client = get_ha_client()
        return self._ha_client

    @property
    def llm(self) -> BaseChatModel:
        """Get LLM using the model context resolution chain.

        Resolution order:
            1. Active model context (user's UI selection, propagated via delegation)
            2. Per-agent settings (DATA_SCIENTIST_MODEL from .env)
            3. Global default (LLM_MODEL from .env)

        The LLM is NOT cached when a model context is active, since different
        requests may carry different model selections. When no context is
        active, the instance is cached for reuse.
        """

        settings = get_settings()
        model_name, temperature = resolve_model(
            agent_model=settings.data_scientist_model,
            agent_temperature=settings.data_scientist_temperature,
        )

        # If a model context is active, always create a fresh LLM
        # (different requests may carry different models)
        if get_model_context() is not None:
            return get_llm(model=model_name, temperature=temperature)

        # No context: use cached instance (falls back to global default)
        if self._llm is None:
            self._llm = get_llm(model=model_name, temperature=temperature)
        return self._llm

    async def invoke(  # type: ignore[override]
        self,
        state: AnalysisState,
        **kwargs: object,
    ) -> dict[str, object]:
        """Run energy analysis.

        Args:
            state: Current analysis state
            **kwargs: Additional arguments (session for DB access)

        Returns:
            State updates with analysis results
        """
        # Include parent span ID from model context for inter-agent trace linking
        ctx = get_model_context()
        trace_inputs = {
            "analysis_type": state.analysis_type.value,
            "entity_ids": state.entity_ids[:10] if state.entity_ids else [],
            "time_range_hours": state.time_range_hours,
        }
        if ctx and ctx.parent_span_id:
            trace_inputs["parent_span_id"] = ctx.parent_span_id

        async with self.trace_span("analyze", state, inputs=trace_inputs) as span:
            # If we have a parent span ID, set it as an attribute for MLflow linking
            if ctx and ctx.parent_span_id:
                span["parent_agent_span_id"] = ctx.parent_span_id
            try:
                # 1. Collect data based on analysis type
                session = kwargs.get("session")

                if state.analysis_type in BEHAVIORAL_ANALYSIS_TYPES:
                    analysis_data = await self._collect_behavioral_data(state)
                else:
                    analysis_data = await self._collect_energy_data(
                        state, session=cast("AsyncSession | None", session)
                    )

                # 2. Generate analysis script
                script = await self._generate_script(state, analysis_data)
                state.generated_script = script

                # 3. Execute in sandbox
                result = await self._execute_script(script, analysis_data)

                # 4. Extract insights from output
                insights = self._extract_insights(result, state)

                # 5. Save insights to database (if session provided)
                session = kwargs.get("session")
                if session and insights:
                    await self._persist_insights(insights, cast("AsyncSession", session), state)

                # Check for high-confidence, high-impact insights that
                # could be addressed by an automation (reverse communication)
                automation_suggestion = generate_automation_suggestion(insights)

                # Update state
                updates: dict[str, object] = {
                    "insights": insights,
                    "generated_script": script,
                    "recommendations": self._extract_recommendations(result),
                    "automation_suggestion": automation_suggestion,
                }

                span["outputs"] = {
                    "insight_count": len(insights),
                    "script_length": len(script),
                    "execution_success": result.success,
                }

                return updates

            except Exception as e:
                self.log_param("error", str(e)[:500])
                raise

    async def _collect_energy_data(
        self,
        state: AnalysisState,
        session: AsyncSession | None = None,
    ) -> dict[str, object]:
        """Collect energy data for analysis. Delegates to collectors module."""
        return await collect_energy_data(state, self.ha, session=session)

    async def _collect_behavioral_data(self, state: AnalysisState) -> dict[str, object]:
        """Collect behavioral data from logbook. Delegates to collectors module."""
        return await collect_behavioral_data(state, self.ha)

    def _build_analysis_prompt(
        self,
        state: AnalysisState,
        energy_data: dict[str, Any],
    ) -> str:
        """Build the analysis prompt. Delegates to prompts module."""
        return build_analysis_prompt(state, energy_data)

    def _generate_automation_suggestion(
        self,
        insights: list[dict[str, Any]],
    ) -> AutomationSuggestion | None:
        """Generate automation suggestion. Delegates to suggestions module."""
        return generate_automation_suggestion(insights)

    async def _generate_script(
        self,
        state: AnalysisState,
        energy_data: dict[str, object],
    ) -> str:
        """Generate Python analysis script using LLM.

        Args:
            state: Analysis state
            energy_data: Collected energy data

        Returns:
            Python script for analysis
        """
        # Build prompt based on analysis type
        analysis_prompt = build_analysis_prompt(state, energy_data)

        # Use behavioral prompt for behavioral analysis types
        system_prompt = (
            load_prompt("data_scientist_behavioral")
            if state.analysis_type in BEHAVIORAL_ANALYSIS_TYPES
            else load_prompt("data_scientist_system")
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_prompt),
        ]

        response = await self.llm.ainvoke(messages)

        # Extract Python code from response
        script = self._extract_code_from_response(str(response.content))

        log_param("script.lines", script.count("\n") + 1)

        return script

    def _extract_code_from_response(self, content: str) -> str:
        """Extract Python code from LLM response.

        Args:
            content: LLM response content

        Returns:
            Extracted Python code
        """
        # Look for code blocks
        if "```python" in content:
            start = content.find("```python") + len("```python")
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()

        if "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()

        # If no code blocks, assume entire content is code
        # (happens with some models that don't use markdown)
        return content.strip()

    async def _execute_script(
        self,
        script: str,
        energy_data: dict[str, object],
    ) -> SandboxResult:
        """Execute analysis script in sandbox.

        Args:
            script: Python script to execute
            energy_data: Data to pass to script

        Returns:
            Sandbox execution result
        """
        import tempfile

        # Write data to temp file that will be mounted
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(energy_data, f, default=str)
            data_path = Path(f.name)

        try:
            result = await self._sandbox.run(
                script,
                data_path=data_path,
            )

            log_metric("sandbox.duration_seconds", result.duration_seconds)
            log_metric("sandbox.success", 1.0 if result.success else 0.0)
            log_param("sandbox.exit_code", result.exit_code)

            if not result.success:
                log_param("sandbox.stderr", result.stderr[:500])

            return result

        finally:
            # Clean up temp file
            with contextlib.suppress(Exception):
                data_path.unlink()

    def _extract_insights(
        self,
        result: SandboxResult,
        state: AnalysisState,
    ) -> list[dict[str, Any]]:
        """Extract insights from script output.

        Args:
            result: Sandbox execution result
            state: Analysis state

        Returns:
            List of insight dictionaries
        """
        if not result.success:
            # Return error insight
            return [
                {
                    "type": "error",
                    "title": "Analysis Failed",
                    "description": f"Script execution failed: {result.stderr[:500]}",
                    "confidence": 0.0,
                    "impact": "low",
                    "evidence": {
                        "exit_code": result.exit_code,
                        "timed_out": result.timed_out,
                    },
                    "entities": state.entity_ids,
                }
            ]

        # Try to parse JSON from stdout
        try:
            output = json.loads(result.stdout)
            insights = output.get("insights", [])

            # Validate and normalize insights
            normalized = []
            for insight in insights:
                normalized.append(
                    {
                        "type": insight.get("type", "custom"),
                        "title": insight.get("title", "Untitled Insight"),
                        "description": insight.get("description", ""),
                        "confidence": min(1.0, max(0.0, float(insight.get("confidence", 0.5)))),
                        "impact": insight.get("impact", "medium"),
                        "evidence": insight.get("evidence", {}),
                        "entities": insight.get("entities", state.entity_ids),
                    }
                )

            return normalized

        except json.JSONDecodeError:
            # Fallback: create insight from raw output
            return [
                {
                    "type": state.analysis_type.value,
                    "title": f"{state.analysis_type.value.replace('_', ' ').title()} Results",
                    "description": result.stdout[:2000],
                    "confidence": 0.5,
                    "impact": "medium",
                    "evidence": {"raw_output": result.stdout[:500]},
                    "entities": state.entity_ids,
                }
            ]

    def _extract_recommendations(
        self,
        result: SandboxResult,
    ) -> list[str]:
        """Extract recommendations from script output.

        Args:
            result: Sandbox execution result

        Returns:
            List of recommendation strings
        """
        if not result.success:
            return []

        try:
            output = json.loads(result.stdout)
            return cast("list[str]", output.get("recommendations", []))
        except (json.JSONDecodeError, KeyError):
            return []

    async def _persist_insights(
        self,
        insights: list[dict[str, object]],
        session: AsyncSession,
        state: AnalysisState,
    ) -> list[str]:
        """Persist insights to database.

        Args:
            insights: List of insight dictionaries
            session: Database session
            state: Analysis state

        Returns:
            List of created insight IDs
        """
        repo = InsightRepository(session)
        insight_ids = []

        for insight_data in insights:
            # Map string type to InsightType enum
            type_str = insight_data.get("type", "custom")
            try:
                insight_type = InsightType(type_str)
            except ValueError:
                insight_type = InsightType.ENERGY_OPTIMIZATION

            insight = await repo.create(
                type=insight_type,
                title=cast("str", insight_data.get("title", "Analysis Result")),
                description=cast("str", insight_data.get("description", "")),
                evidence=cast("dict[str, Any]", insight_data.get("evidence", {})),
                confidence=cast("float", insight_data.get("confidence", 0.5)),
                impact=cast("str", insight_data.get("impact", "medium")),
                entities=cast("list[str]", insight_data.get("entities", [])),
                script_path=None,  # Could store in MLflow artifacts
                script_output={"stdout": cast("str", insight_data.get("raw_output", ""))[:1000]},
                mlflow_run_id=state.mlflow_run_id,
            )
            insight_ids.append(insight.id)

        log_metric("insights.persisted", float(len(insight_ids)))

        return insight_ids
