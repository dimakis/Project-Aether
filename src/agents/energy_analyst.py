"""Energy Analyst specialist for the DS team.

Handles energy optimization, cost analysis, and usage pattern detection.
Extracts energy-specific responsibilities from the former monolithic
DataScientistAgent.

Constitution: Isolation — scripts run in gVisor sandbox.
Constitution: Observability — all analysis traced in MLflow.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base_analyst import BaseAnalyst
from src.agents.model_context import get_model_context
from src.agents.prompts import load_prompt
from src.dal import EntityRepository
from src.graph.state import (
    AgentRole,
    AnalysisState,
    AnalysisType,
    SpecialistFinding,
)
from src.ha import EnergyHistoryClient
from src.sandbox.runner import SandboxResult
from src.tracing import log_metric, log_param

logger = logging.getLogger(__name__)


class EnergyAnalyst(BaseAnalyst):
    """Energy analysis specialist.

    Responsibilities:
    - Collect energy sensor data (from DB or HA)
    - Generate energy analysis scripts
    - Extract energy insights and optimization opportunities
    - Detect anomalous consumption patterns
    - Suggest energy-saving automations
    """

    ROLE = AgentRole.ENERGY_ANALYST
    NAME = "EnergyAnalyst"

    async def collect_data(self, state: AnalysisState) -> dict[str, Any]:
        """Collect energy data for analysis.

        Uses local database for entity discovery (faster),
        then falls back to HA for historical data.

        Args:
            state: Analysis state with entity IDs and time range.

        Returns:
            Energy data dict for script generation.
        """
        entity_ids = state.entity_ids

        # If no specific entities, discover energy sensors
        if not entity_ids:
            energy_client = EnergyHistoryClient(self.ha)
            sensors = await energy_client.get_energy_sensors()
            entity_ids = [s["entity_id"] for s in sensors[:20]]
            log_param("discovered_sensors", len(entity_ids))

        # Collect historical data via HA
        energy_client = EnergyHistoryClient(self.ha)
        data = await energy_client.get_aggregated_energy(
            entity_ids,
            hours=state.time_range_hours,
        )

        log_metric("energy.total_kwh", data.get("total_kwh", 0.0))
        log_metric("energy.sensor_count", float(len(entity_ids)))

        # In diagnostic mode, include the Architect's evidence
        if state.analysis_type == AnalysisType.DIAGNOSTIC and state.diagnostic_context:
            data["diagnostic_context"] = state.diagnostic_context
            log_param("diagnostic_mode", True)

        # Include prior findings from other specialists for context
        prior = self.get_prior_findings(state)
        if prior:
            data["prior_specialist_findings"] = [
                {
                    "specialist": f.specialist,
                    "title": f.title,
                    "description": f.description,
                    "entities": f.entities,
                }
                for f in prior
            ]

        return data

    async def generate_script(self, state: AnalysisState, data: dict[str, Any]) -> str:
        """Generate Python energy analysis script using LLM.

        Args:
            state: Analysis state.
            data: Collected energy data.

        Returns:
            Python script for sandbox execution.
        """
        analysis_prompt = self._build_analysis_prompt(state, data)
        system_prompt = load_prompt("data_scientist_system")

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        script = self._extract_code_from_response(response.content)

        log_param("script.lines", script.count("\n") + 1)
        return script

    def extract_findings(
        self, result: SandboxResult, state: AnalysisState
    ) -> list[SpecialistFinding]:
        """Extract SpecialistFinding objects from sandbox output.

        Expects JSON output with an "insights" array, where each entry
        has title, description, confidence, and entities.

        Args:
            result: Sandbox execution result.
            state: Analysis state.

        Returns:
            List of energy findings.
        """
        if not result.success or not result.stdout:
            return []

        try:
            output = json.loads(result.stdout)
            insights = output.get("insights", [])
        except (json.JSONDecodeError, AttributeError):
            return []

        findings = []
        for insight in insights:
            finding = SpecialistFinding(
                specialist="energy_analyst",
                finding_type=insight.get("type", "insight"),
                title=insight.get("title", "Energy insight"),
                description=insight.get("description", ""),
                confidence=min(max(float(insight.get("confidence", 0.5)), 0.0), 1.0),
                entities=insight.get("entities", state.entity_ids[:5]),
                evidence=insight.get("evidence", {}),
            )
            findings.append(finding)

        return findings

    async def invoke(self, state: AnalysisState, **kwargs) -> dict[str, Any]:
        """Run energy analysis workflow.

        Full pipeline: collect -> generate script -> execute -> extract.

        Args:
            state: Current analysis state.
            **kwargs: Additional args (session for DB access).

        Returns:
            State updates with findings and recommendations.
        """
        ctx = get_model_context()
        trace_inputs = {
            "analysis_type": state.analysis_type.value,
            "entity_ids": state.entity_ids[:10],
            "time_range_hours": state.time_range_hours,
        }
        if ctx and ctx.parent_span_id:
            trace_inputs["parent_span_id"] = ctx.parent_span_id

        async with self.trace_span("energy_analysis", state, inputs=trace_inputs) as span:
            try:
                # 1. Collect energy data
                data = await self.collect_data(state)

                # 2. Generate analysis script
                script = await self.generate_script(state, data)

                # 3. Execute in sandbox
                result = await self.execute_script(script, data)

                # 4. Extract findings
                findings = self.extract_findings(result, state)

                # 5. Add findings to team analysis
                for finding in findings:
                    state = self.add_finding(state, finding)

                # 6. Persist if session provided
                session = kwargs.get("session")
                if session and findings:
                    await self.persist_findings(findings, session)

                span["outputs"] = {
                    "finding_count": len(findings),
                    "script_length": len(script),
                    "execution_success": result.success,
                }

                return {
                    "insights": [
                        {"title": f.title, "description": f.description}
                        for f in findings
                    ],
                    "generated_script": script,
                    "team_analysis": state.team_analysis,
                }

            except Exception as e:
                self.log_param("error", str(e)[:500])
                raise

    # -----------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------

    def _build_analysis_prompt(
        self, state: AnalysisState, data: dict[str, Any]
    ) -> str:
        """Build the energy analysis prompt."""
        entity_count = data.get("entity_count", len(state.entity_ids))
        total_kwh = data.get("total_kwh", 0.0)
        hours = state.time_range_hours

        if state.analysis_type == AnalysisType.ENERGY_OPTIMIZATION:
            return load_prompt(
                "data_scientist_energy",
                entity_count=str(entity_count),
                hours=str(hours),
                total_kwh=f"{total_kwh:.2f}",
            )

        # Default energy analysis prompt
        return f"""
Analyze energy data from {entity_count} sensors over {hours} hours.
Total consumption: {total_kwh:.2f} kWh.

Produce a JSON object with an "insights" array. Each insight must have:
- title: Short description
- description: Detailed explanation
- confidence: 0.0-1.0
- entities: List of relevant entity IDs
- type: "insight", "concern", or "recommendation"

Focus on: peak usage times, baseline vs peak ratios, anomalous consumption,
and opportunities for automation.
"""

    def _extract_code_from_response(self, content: str) -> str:
        """Extract Python code from LLM response."""
        if "```python" in content:
            start = content.index("```python") + len("```python")
            end = content.index("```", start)
            return content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            return content[start:end].strip()
        return content.strip()
