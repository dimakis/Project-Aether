"""Behavioral Analyst specialist for the DS team.

Handles user behavior patterns, automation effectiveness, script/scene usage,
automation gap detection, and correlation discovery.

Enhanced data sources (per plan):
- Script and scene usage frequency
- Trigger source analysis (automation-triggered vs human-triggered)
- Automation effectiveness with manual override tracking

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
from src.graph.state import (
    AgentRole,
    AnalysisState,
    AnalysisType,
    SpecialistFinding,
)
from src.ha.behavioral import BehavioralAnalysisClient
from src.tracing import log_metric, log_param

if TYPE_CHECKING:
    from src.sandbox.runner import SandboxResult

logger = logging.getLogger(__name__)

# Analysis types handled by the Behavioral Analyst
BEHAVIORAL_TYPES = {
    AnalysisType.BEHAVIOR_ANALYSIS,
    AnalysisType.AUTOMATION_ANALYSIS,
    AnalysisType.AUTOMATION_GAP_DETECTION,
    AnalysisType.CORRELATION_DISCOVERY,
    AnalysisType.DEVICE_HEALTH,
}


class BehavioralAnalyst(BaseAnalyst):
    """Behavioral analysis specialist.

    Responsibilities:
    - Analyze user interaction patterns (button presses, manual actions)
    - Evaluate automation effectiveness and override rates
    - Detect automation gaps (repetitive manual patterns)
    - Track script and scene usage frequency and trigger sources
    - Discover entity correlations
    - Suggest new automations based on behavioral patterns
    """

    ROLE = AgentRole.BEHAVIORAL_ANALYST
    NAME = "BehavioralAnalyst"

    async def collect_data(self, state: AnalysisState) -> dict[str, Any]:
        """Collect behavioral data from logbook and HA.

        Enhanced with script/scene usage and trigger source tracking.

        Args:
            state: Analysis state with type and time range.

        Returns:
            Behavioral data dict.
        """
        behavioral = BehavioralAnalysisClient(self.ha)
        hours = state.time_range_hours
        data: dict[str, Any] = {
            "analysis_type": state.analysis_type.value,
            "hours": hours,
        }

        try:
            if state.analysis_type == AnalysisType.BEHAVIOR_ANALYSIS:
                button_usage = await behavioral.get_button_usage(hours=hours)
                data["button_usage"] = [
                    {
                        "entity_id": r.entity_id,
                        "total_presses": r.total_presses,
                        "avg_daily": r.avg_daily_presses,
                        "by_hour": dict(r.by_hour),
                    }
                    for r in button_usage[:30]
                ]
                data["entity_count"] = len(button_usage)

            elif state.analysis_type == AnalysisType.AUTOMATION_ANALYSIS:
                effectiveness = await behavioral.get_automation_effectiveness(hours=hours)
                data["automation_effectiveness"] = [
                    {
                        "automation_id": r.automation_id,
                        "alias": r.alias,
                        "trigger_count": r.trigger_count,
                        "manual_overrides": r.manual_override_count,
                        "efficiency_score": r.efficiency_score,
                    }
                    for r in effectiveness
                ]
                data["entity_count"] = len(effectiveness)

            elif state.analysis_type == AnalysisType.AUTOMATION_GAP_DETECTION:
                gaps = await behavioral.detect_automation_gaps(hours=hours)
                data["automation_gaps"] = [
                    {
                        "description": g.pattern_description,
                        "entities": g.entities,
                        "occurrences": g.occurrence_count,
                        "typical_time": g.typical_time,
                        "confidence": g.confidence,
                    }
                    for g in gaps
                ]
                data["entity_count"] = len(gaps)

            elif state.analysis_type == AnalysisType.CORRELATION_DISCOVERY:
                correlations = await behavioral.find_correlations(
                    entity_ids=state.entity_ids or None,
                    hours=hours,
                )
                data["correlations"] = [
                    {
                        "entity_a": c.entity_a,
                        "entity_b": c.entity_b,
                        "co_occurrences": c.co_occurrence_count,
                        "avg_delta_seconds": c.avg_time_delta_seconds,
                        "confidence": c.confidence,
                    }
                    for c in correlations
                ]
                data["entity_count"] = len(correlations)

            elif state.analysis_type == AnalysisType.DEVICE_HEALTH:
                health = await behavioral.get_device_health_report(hours=hours)
                data["device_health"] = [
                    {
                        "entity_id": h.entity_id,
                        "status": h.status,
                        "last_seen": h.last_seen,
                        "issue": h.issue,
                        "state_changes": h.state_change_count,
                    }
                    for h in health
                ]
                data["entity_count"] = len(health)

            else:
                # Generic: gather logbook stats
                stats = await behavioral._logbook.get_stats(hours=hours)
                data["logbook_stats"] = {
                    "total_entries": stats.total_entries,
                    "by_action_type": stats.by_action_type,
                    "by_domain": stats.by_domain,
                    "automation_triggers": stats.automation_triggers,
                    "manual_actions": stats.manual_actions,
                    "unique_entities": stats.unique_entities,
                    "by_hour": dict(stats.by_hour),
                }
                data["entity_count"] = stats.unique_entities

            # ---------------------------------------------------------
            # ENHANCED: Script/scene usage and trigger source analysis
            # ---------------------------------------------------------
            script_scene_data = await self._collect_script_scene_usage(behavioral, hours)
            data["script_scene_usage"] = script_scene_data
            data["automation_vs_human"] = await self._collect_trigger_source_breakdown(
                behavioral, hours
            )

            log_metric("behavioral.entity_count", float(data.get("entity_count", 0)))
            log_param("behavioral.analysis_type", state.analysis_type.value)

        except Exception as e:
            logger.warning(f"Error collecting behavioral data: {e}")
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
        """Generate behavioral analysis script via LLM.

        Args:
            state: Analysis state.
            data: Collected behavioral data.

        Returns:
            Python script for sandbox execution.
        """
        system_prompt = load_prompt("data_scientist_behavioral")
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
        """Extract behavioral findings from sandbox output.

        Args:
            result: Sandbox execution result.
            state: Analysis state.

        Returns:
            List of behavioral findings.
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
                specialist="behavioral_analyst",
                finding_type=insight.get("type", "insight"),
                title=insight.get("title", "Behavioral insight"),
                description=insight.get("description", ""),
                confidence=min(max(float(insight.get("confidence", 0.5)), 0.0), 1.0),
                entities=insight.get("entities", []),
                evidence=insight.get("evidence", {}),
            )
            findings.append(finding)

        return findings

    async def invoke(self, state: AnalysisState, **kwargs: object) -> dict[str, Any]:
        """Run behavioral analysis workflow.

        Args:
            state: Current analysis state.
            **kwargs: Additional args (session for DB).

        Returns:
            State updates with findings.
        """
        ctx = get_model_context()
        trace_inputs = {
            "analysis_type": state.analysis_type.value,
            "entity_ids": state.entity_ids[:10],
            "time_range_hours": state.time_range_hours,
        }
        if ctx and ctx.parent_span_id:
            trace_inputs["parent_span_id"] = ctx.parent_span_id

        async with self.trace_span("behavioral_analysis", state, inputs=trace_inputs) as span:
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
                    "script_length": len(script),
                    "execution_success": result.success,
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
    # Enhanced data sources
    # -----------------------------------------------------------------

    async def _collect_script_scene_usage(
        self,
        behavioral: BehavioralAnalysisClient,
        hours: int,
    ) -> dict[str, Any]:
        """Collect script and scene execution frequency.

        Tracks how often each script/scene is called and from where
        (automation trigger vs direct human activation).

        Args:
            behavioral: Behavioral analysis client.
            hours: Time window in hours.

        Returns:
            Dict with script/scene usage stats.
        """
        try:
            stats = await behavioral._logbook.get_stats(hours=hours)
            return {
                "script_calls": stats.by_domain.get("script", 0),
                "scene_calls": stats.by_domain.get("scene", 0),
                "automation_triggered_total": stats.automation_triggers,
                "manual_triggered_total": stats.manual_actions,
            }
        except Exception as e:
            logger.warning(f"Error collecting script/scene usage: {e}")
            return {}

    async def _collect_trigger_source_breakdown(
        self,
        behavioral: BehavioralAnalysisClient,
        hours: int,
    ) -> dict[str, Any]:
        """Break down action triggers by source: automation vs human.

        Useful for discovering which actions could be automated
        (high manual trigger count) or are already well-automated.

        Args:
            behavioral: Behavioral analysis client.
            hours: Time window.

        Returns:
            Automation vs human trigger breakdown.
        """
        try:
            stats = await behavioral._logbook.get_stats(hours=hours)
            total = stats.automation_triggers + stats.manual_actions
            return {
                "automation_triggers": stats.automation_triggers,
                "human_triggers": stats.manual_actions,
                "automation_ratio": (stats.automation_triggers / total if total > 0 else 0.0),
                "human_ratio": (stats.manual_actions / total if total > 0 else 0.0),
            }
        except Exception as e:
            logger.warning(f"Error collecting trigger breakdown: {e}")
            return {}

    # -----------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------

    def _build_analysis_prompt(self, state: AnalysisState, data: dict[str, Any]) -> str:
        """Build behavioral analysis prompt."""
        entity_count = data.get("entity_count", 0)
        hours = state.time_range_hours

        prompt = f"""
Analyze behavioral data from {entity_count} entities over {hours} hours.
Analysis type: {state.analysis_type.value}

Available data keys: {list(data.keys())}

Enhanced data includes:
- script_scene_usage: How often scripts and scenes are called
- automation_vs_human: Breakdown of automation triggers vs human actions

Produce a JSON object with an "insights" array. Each insight must have:
- title: Short description
- description: Detailed explanation
- confidence: 0.0-1.0
- entities: List of relevant entity IDs
- type: "insight", "concern", or "recommendation"

Focus on: repetitive manual patterns (automation candidates), automation
effectiveness, script/scene usage efficiency, and behavioral anomalies.
"""
        # Include prior findings if available
        prior = data.get("prior_specialist_findings", [])
        if prior:
            prompt += "\nPrior findings from other specialists:\n"
            for pf in prior:
                prompt += f"- [{pf['specialist']}] {pf['title']}: {pf['description']}\n"
            prompt += "\nConsider these when analyzing behavioral patterns.\n"

        return self._append_depth_fragment(prompt, state.depth)

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
