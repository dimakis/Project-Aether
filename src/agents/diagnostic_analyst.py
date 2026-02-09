"""Diagnostic Analyst specialist for the DS team.

Handles HA system health analysis: entity diagnostics, integration health,
config validation, error log analysis, and sensor drift detection.

Absorbs the diagnostic tools from src/diagnostics/ into the specialist
framework for cross-consultation with Energy and Behavioral analysts.

Constitution: Isolation — scripts run in gVisor sandbox.
Constitution: Observability — all analysis traced in MLflow.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base_analyst import BaseAnalyst
from src.agents.model_context import get_model_context
from src.agents.prompts import load_prompt
from src.diagnostics.config_validator import run_config_check
from src.diagnostics.entity_health import (
    find_unavailable_entities,
)
from src.diagnostics.integration_health import find_unhealthy_integrations
from src.diagnostics.log_parser import get_error_summary, parse_error_log
from src.graph.state import (
    AgentRole,
    AnalysisState,
    SpecialistFinding,
)
from src.tracing import log_metric, log_param

if TYPE_CHECKING:
    from src.sandbox.runner import SandboxResult

logger = logging.getLogger(__name__)


class DiagnosticAnalyst(BaseAnalyst):
    """Diagnostic analysis specialist.

    Responsibilities:
    - Find unavailable or unhealthy entities
    - Analyze HA error logs for patterns
    - Check integration health
    - Validate HA configuration
    - Detect sensor drift and hardware issues
    - Cross-reference with energy/behavioral findings
    """

    ROLE = AgentRole.DIAGNOSTIC_ANALYST
    NAME = "DiagnosticAnalyst"

    async def collect_data(self, state: AnalysisState) -> dict[str, Any]:
        """Collect diagnostic data from multiple HA health sources.

        Aggregates entity health, integration status, config validation,
        and error log analysis into a single data dict.

        Args:
            state: Analysis state.

        Returns:
            Diagnostic data dict.
        """
        data: dict[str, Any] = {
            "analysis_type": state.analysis_type.value,
            "hours": state.time_range_hours,
            "entity_ids": state.entity_ids,
        }

        try:
            # Entity health: find unavailable entities
            unavailable = await find_unavailable_entities(self.ha)
            data["unavailable_entities"] = [
                {
                    "entity_id": e.entity_id,
                    "state": e.state,
                    "last_changed": str(e.last_changed) if hasattr(e, "last_changed") else None,
                    "issue": e.issue if hasattr(e, "issue") else None,
                }
                for e in unavailable
            ]

            # Integration health
            unhealthy = await find_unhealthy_integrations(self.ha)
            data["unhealthy_integrations"] = [
                {
                    "domain": i.domain if hasattr(i, "domain") else str(i),
                    "status": i.status if hasattr(i, "status") else "unknown",
                    "issue": i.issue if hasattr(i, "issue") else None,
                }
                for i in unhealthy
            ]

            # Config validation
            config_result = await run_config_check(self.ha)
            data["config_check"] = {
                "valid": config_result.valid,
                "errors": config_result.errors if hasattr(config_result, "errors") else [],
                "warnings": config_result.warnings if hasattr(config_result, "warnings") else [],
            }

            # Error log analysis
            try:
                raw_log = await self.ha.get_error_log()
                if raw_log and raw_log.strip():
                    entries = parse_error_log(raw_log)
                    summary = get_error_summary(entries)
                    data["error_log"] = {
                        "entry_count": len(entries),
                        "summary": summary,
                    }
                else:
                    data["error_log"] = {"entry_count": 0, "summary": {}}
            except Exception as e:
                logger.warning(f"Error fetching error log: {e}")
                data["error_log"] = {"error": str(e)}

            # Include diagnostic context from Architect
            if state.diagnostic_context:
                data["diagnostic_context"] = state.diagnostic_context

            log_metric("diagnostic.unavailable_count", float(len(unavailable)))
            log_metric("diagnostic.unhealthy_integrations", float(len(unhealthy)))
            log_param("diagnostic.config_valid", config_result.valid)

        except Exception as e:
            logger.warning(f"Error collecting diagnostic data: {e}")
            data["error"] = str(e)

        # Include prior findings from other specialists
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
        """Generate diagnostic analysis script via LLM.

        Args:
            state: Analysis state.
            data: Collected diagnostic data.

        Returns:
            Python script for sandbox execution.
        """
        system_prompt = load_prompt("data_scientist_system")
        analysis_prompt = self._build_analysis_prompt(state, data)

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
        """Extract diagnostic findings from sandbox output.

        Args:
            result: Sandbox execution result.
            state: Analysis state.

        Returns:
            List of diagnostic findings.
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
                specialist="diagnostic_analyst",
                finding_type=insight.get("type", "concern"),
                title=insight.get("title", "Diagnostic finding"),
                description=insight.get("description", ""),
                confidence=min(max(float(insight.get("confidence", 0.5)), 0.0), 1.0),
                entities=insight.get("entities", state.entity_ids[:5]),
                evidence=insight.get("evidence", {}),
            )
            findings.append(finding)

        return findings

    async def invoke(self, state: AnalysisState, **kwargs) -> dict[str, Any]:
        """Run diagnostic analysis workflow.

        Args:
            state: Current analysis state.
            **kwargs: Additional args (session for DB).

        Returns:
            State updates with diagnostic findings.
        """
        ctx = get_model_context()
        trace_inputs = {
            "analysis_type": state.analysis_type.value,
            "entity_ids": state.entity_ids[:10],
            "time_range_hours": state.time_range_hours,
        }
        if ctx and ctx.parent_span_id:
            trace_inputs["parent_span_id"] = ctx.parent_span_id

        async with self.trace_span("diagnostic_analysis", state, inputs=trace_inputs) as span:
            try:
                data = await self.collect_data(state)
                script = await self.generate_script(state, data)
                result = await self.execute_script(script, data)
                findings = self.extract_findings(result, state)

                for finding in findings:
                    state = self.add_finding(state, finding)

                # Persist (explicit session or execution context fallback)
                await self._persist_with_fallback(findings, kwargs.get("session"))

                span["outputs"] = {
                    "finding_count": len(findings),
                    "unavailable_entities": len(data.get("unavailable_entities", [])),
                    "unhealthy_integrations": len(data.get("unhealthy_integrations", [])),
                }

                return {
                    "insights": [
                        {"title": f.title, "description": f.description} for f in findings
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

    def _build_analysis_prompt(self, state: AnalysisState, data: dict[str, Any]) -> str:
        """Build diagnostic analysis prompt."""
        unavailable_count = len(data.get("unavailable_entities", []))
        unhealthy_count = len(data.get("unhealthy_integrations", []))
        config_valid = data.get("config_check", {}).get("valid", True)
        hours = state.time_range_hours

        prompt = f"""
Perform a diagnostic analysis of the Home Assistant system.
Time range: {hours} hours.

System health summary:
- Unavailable entities: {unavailable_count}
- Unhealthy integrations: {unhealthy_count}
- Config valid: {config_valid}

Available data keys: {list(data.keys())}

Produce a JSON object with an "insights" array. Each insight must have:
- title: Short description
- description: Detailed explanation
- confidence: 0.0-1.0
- entities: List of affected entity IDs
- type: "concern", "data_quality_flag", or "recommendation"
- evidence: Supporting data

Focus on: entity unavailability causes, integration health issues,
sensor drift detection, error log patterns, and corrective actions.
"""

        if state.diagnostic_context:
            prompt += f"\nArchitect's diagnostic context:\n{state.diagnostic_context}\n"

        prior = data.get("prior_specialist_findings", [])
        if prior:
            prompt += "\nPrior findings from other specialists:\n"
            for pf in prior:
                prompt += f"- [{pf['specialist']}] {pf['title']}: {pf['description']}\n"

        return prompt

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
