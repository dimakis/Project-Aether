"""Data Scientist agent for energy analysis and insights.

User Story 3: Energy Optimization Suggestions.
Feature 03: Intelligent Optimization & Multi-Agent Collaboration.

The Data Scientist analyzes energy data and behavioral patterns
from Home Assistant, generates Python scripts for analysis,
executes them in a sandboxed environment, and extracts actionable insights.

Constitution: Isolation - All scripts run in gVisor sandbox.
Constitution: Observability - All analysis traced in MLflow.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

from src.agents import BaseAgent
from src.agents.model_context import get_model_context, resolve_model
from src.dal import EntityRepository, InsightRepository
from src.graph.state import AgentRole, AnalysisState, AnalysisType, AutomationSuggestion
from src.llm import get_llm
from src.mcp import EnergyHistoryClient, MCPClient, get_mcp_client
from src.mcp.behavioral import BehavioralAnalysisClient
from src.sandbox.runner import SandboxResult, SandboxRunner
from src.settings import get_settings
from src.storage.entities.insight import InsightStatus, InsightType
from src.tracing import log_metric, log_param, start_experiment_run


# System prompt for the Data Scientist
DATA_SCIENTIST_SYSTEM_PROMPT = """You are an expert data scientist specializing in home energy analysis and system diagnostics.

Your role is to analyze energy sensor data from Home Assistant and generate insights
that help users optimize their energy consumption. You also perform diagnostic
analysis when asked to troubleshoot issues with sensors, integrations, or data quality.

## Response Formatting

Use rich markdown formatting to make analysis results clear and actionable:
- Use **bold** for key findings and `code` for entity IDs and values
- Use headings (##, ###) to organize analysis sections
- Use tables to present comparisons, rankings, and data summaries
- Use code blocks with ```python for scripts and ```json for data structures
- Use emojis to improve scanability of results:
  📊 for data/statistics, ⚡ for energy, 💰 for cost savings,
  📈 for trends/increases, 📉 for decreases, ⚠️ for anomalies/warnings,
  ✅ for healthy/good, ❌ for problems/errors, 🔍 for investigation,
  💡 for recommendations, 🌡️ for temperature, 🔋 for battery/power

When analyzing data, you should:
1. Identify usage patterns (daily, weekly, seasonal)
2. Detect anomalies or unusual consumption
3. Find energy-saving opportunities
4. Provide actionable recommendations

When diagnosing issues, you should:
1. Analyze data gaps, missing values, and connectivity patterns
2. Correlate error logs with sensor behavior
3. Identify integration failures or configuration problems
4. Recommend specific remediation steps

You can generate Python scripts for analysis. Scripts run in a sandboxed environment with:
- pandas, numpy, matplotlib, scipy, scikit-learn, statsmodels, seaborn
- Read-only access to data passed via /workspace/data.json
- Output written to stdout/stderr
- 30 second timeout, 512MB memory limit

When generating scripts:
1. Always read data from /workspace/data.json
2. Print results as JSON to stdout for parsing
3. Save any charts to /workspace/output/ directory
4. Handle missing or invalid data gracefully

Output JSON structure for insights:
{
  "insights": [
    {
      "type": "energy_optimization|anomaly_detection|usage_pattern|cost_saving",
      "title": "Brief title",
      "description": "Detailed explanation",
      "confidence": 0.0-1.0,
      "impact": "low|medium|high|critical",
      "evidence": {"key": "value"},
      "entities": ["entity_id1", "entity_id2"]
    }
  ],
  "summary": "Overall analysis summary",
  "recommendations": ["recommendation1", "recommendation2"]
}
"""

# Behavioral analysis system prompt (Feature 03)
DATA_SCIENTIST_BEHAVIORAL_PROMPT = """You are an expert data scientist specializing in smart home behavioral analysis.

Your role is to analyze logbook and usage data from Home Assistant to identify
behavioral patterns, automation gaps, and optimization opportunities.

When analyzing behavioral data, you should:
1. Identify repeating manual actions that could be automated
2. Score existing automation effectiveness (trigger frequency vs manual overrides)
3. Discover entity correlations (devices used together)
4. Detect device health issues (unresponsive, degraded, anomalous)
5. Find cost-saving opportunities from usage patterns

You can generate Python scripts for analysis. Scripts run in a sandboxed environment with:
- pandas, numpy, matplotlib, scipy, scikit-learn, statsmodels, seaborn
- Read-only access to data passed via /workspace/data.json
- Output written to stdout/stderr
- 30 second timeout, 512MB memory limit

When generating scripts:
1. Always read data from /workspace/data.json
2. Print results as JSON to stdout for parsing
3. Save any charts to /workspace/output/ directory
4. Handle missing or invalid data gracefully

Output JSON structure for behavioral insights:
{
  "insights": [
    {
      "type": "automation_gap|automation_inefficiency|correlation|device_health|behavioral_pattern|cost_saving",
      "title": "Brief title",
      "description": "Detailed explanation",
      "confidence": 0.0-1.0,
      "impact": "low|medium|high|critical",
      "evidence": {"key": "value"},
      "entities": ["entity_id1", "entity_id2"]
    }
  ],
  "summary": "Overall analysis summary",
  "recommendations": ["recommendation1", "recommendation2"]
}
"""

# Analysis types that use behavioral (logbook) data vs energy (history) data
BEHAVIORAL_ANALYSIS_TYPES = {
    AnalysisType.BEHAVIOR_ANALYSIS,
    AnalysisType.AUTOMATION_ANALYSIS,
    AnalysisType.AUTOMATION_GAP_DETECTION,
    AnalysisType.CORRELATION_DISCOVERY,
    AnalysisType.DEVICE_HEALTH,
}


class DataScientistAgent(BaseAgent):
    """The Data Scientist agent for energy analysis.

    Responsibilities:
    - Analyze energy sensor data
    - Generate analysis scripts (Python)
    - Execute scripts in sandboxed environment
    - Extract and persist insights
    - Provide energy optimization recommendations
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize Data Scientist agent.

        Args:
            mcp_client: Optional MCP client (creates one if not provided)
        """
        super().__init__(
            role=AgentRole.DATA_SCIENTIST,
            name="DataScientist",
        )
        self._mcp = mcp_client
        self._llm = None
        self._sandbox = SandboxRunner()

    @property
    def mcp(self) -> MCPClient:
        """Get MCP client, creating if needed."""
        if self._mcp is None:
            self._mcp = get_mcp_client()
        return self._mcp

    @property
    def llm(self):
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

    async def invoke(
        self,
        state: AnalysisState,
        **kwargs: Any,
    ) -> dict[str, Any]:
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
                    analysis_data = await self._collect_energy_data(state, session=session)
                
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
                    await self._persist_insights(insights, session, state)
                
                # Check for high-confidence, high-impact insights that
                # could be addressed by an automation (reverse communication)
                automation_suggestion = self._generate_automation_suggestion(insights)

                # Update state
                updates = {
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
        session: Any = None,
    ) -> dict[str, Any]:
        """Collect energy data for analysis.

        Uses local database for entity discovery (faster, no MCP overhead),
        then falls back to MCP only for historical data which isn't stored locally.

        In diagnostic mode, entity_ids are expected to be pre-supplied by the
        Architect, and diagnostic_context is included in the returned data.

        Args:
            state: Analysis state with entity IDs and time range
            session: Database session for entity lookups

        Returns:
            Energy data for analysis
        """
        entity_ids = state.entity_ids
        
        # If no specific entities, discover energy sensors from DB first
        if not entity_ids:
            entity_ids = await self._discover_energy_sensors_from_db(session)
            log_param("discovered_sensors", len(entity_ids))
            log_param("discovery_source", "database" if entity_ids else "mcp")
        
        # If DB discovery failed or returned nothing, fall back to MCP
        if not entity_ids:
            energy_client = EnergyHistoryClient(self.mcp)
            sensors = await energy_client.get_energy_sensors()
            entity_ids = [s["entity_id"] for s in sensors[:20]]
            log_param("discovered_sensors", len(entity_ids))
            log_param("discovery_source", "mcp_fallback")

        # Collect historical data via MCP (not stored locally)
        energy_client = EnergyHistoryClient(self.mcp)
        data = await energy_client.get_aggregated_energy(
            entity_ids,
            hours=state.time_range_hours,
        )
        
        log_metric("energy.total_kwh", data.get("total_kwh", 0.0))
        log_metric("energy.sensor_count", float(len(entity_ids)))

        # In diagnostic mode, include the Architect's evidence in the data
        if state.analysis_type == AnalysisType.DIAGNOSTIC and state.diagnostic_context:
            data["diagnostic_context"] = state.diagnostic_context
            log_param("diagnostic_mode", True)
        
        return data

    async def _discover_energy_sensors_from_db(
        self,
        session: Any,
    ) -> list[str]:
        """Discover energy sensors from the local database.

        Queries the synced entities table instead of making MCP calls.
        Much faster and doesn't require HA to be available.

        Args:
            session: Database session

        Returns:
            List of energy sensor entity IDs
        """
        if not session:
            return []
        
        try:
            repo = EntityRepository(session)
            
            # Get all sensor entities
            sensors = await repo.list_all(domain="sensor", limit=500)
            
            # Filter for energy-related sensors
            # Energy device classes: energy, power
            # Energy units: kWh, Wh, MWh, W, kW, MW
            energy_device_classes = {"energy", "power"}
            energy_units = {"kWh", "Wh", "MWh", "W", "kW", "MW"}
            
            energy_sensors = []
            for entity in sensors:
                attrs = entity.attributes or {}
                device_class = attrs.get("device_class", "")
                unit = attrs.get("unit_of_measurement", "")
                
                is_energy = (
                    device_class in energy_device_classes
                    or unit in energy_units
                )
                
                if is_energy:
                    energy_sensors.append(entity.entity_id)
            
            return energy_sensors[:20]  # Limit to 20
            
        except Exception as e:
            # Log but don't fail - will fall back to MCP
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to discover energy sensors from DB: {e}"
            )
            return []

    async def _collect_behavioral_data(
        self,
        state: AnalysisState,
    ) -> dict[str, Any]:
        """Collect behavioral data from logbook for analysis.

        Uses the BehavioralAnalysisClient to gather button usage,
        automation effectiveness, correlations, gaps, and device health.

        Args:
            state: Analysis state with type and time range

        Returns:
            Behavioral data for analysis
        """
        behavioral = BehavioralAnalysisClient(self.mcp)
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
                # Cost optimization or generic behavioral - gather everything
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

            log_metric("behavioral.entity_count", float(data.get("entity_count", 0)))
            log_param("behavioral.analysis_type", state.analysis_type.value)

        except Exception as e:
            logger.warning(f"Error collecting behavioral data: {e}")
            data["error"] = str(e)

        return data

    async def _generate_script(
        self,
        state: AnalysisState,
        energy_data: dict[str, Any],
    ) -> str:
        """Generate Python analysis script using LLM.

        Args:
            state: Analysis state
            energy_data: Collected energy data

        Returns:
            Python script for analysis
        """
        # Build prompt based on analysis type
        analysis_prompt = self._build_analysis_prompt(state, energy_data)
        
        # Use behavioral prompt for behavioral analysis types
        system_prompt = (
            DATA_SCIENTIST_BEHAVIORAL_PROMPT
            if state.analysis_type in BEHAVIORAL_ANALYSIS_TYPES
            else DATA_SCIENTIST_SYSTEM_PROMPT
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_prompt),
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # Extract Python code from response
        script = self._extract_code_from_response(response.content)
        
        log_param("script.lines", script.count("\n") + 1)
        
        return script

    def _build_analysis_prompt(
        self,
        state: AnalysisState,
        energy_data: dict[str, Any],
    ) -> str:
        """Build the analysis prompt based on type.

        Args:
            state: Analysis state
            energy_data: Energy data summary

        Returns:
            Prompt for script generation
        """
        entity_count = energy_data.get("entity_count", 0)
        total_kwh = energy_data.get("total_kwh", 0.0)
        hours = state.time_range_hours
        
        base_context = f"""
I have energy data from {entity_count} sensors over the past {hours} hours.
Total energy consumption: {total_kwh:.2f} kWh

Data structure (available in /workspace/data.json):
- entities: List of entity data with data_points, stats, etc.
- total_kwh: Total consumption
- hours: Analysis period

"""
        
        if state.analysis_type == AnalysisType.ENERGY_OPTIMIZATION:
            return base_context + """
Please analyze this energy data and generate a Python script that:
1. Identifies the top energy consumers
2. Detects peak usage times
3. Finds opportunities for energy savings
4. Calculates potential savings if usage is shifted to off-peak hours

Output insights as JSON to stdout with type="energy_optimization".
"""
        
        elif state.analysis_type == AnalysisType.ANOMALY_DETECTION:
            return base_context + """
Please analyze this energy data and generate a Python script that:
1. Establishes baseline consumption patterns
2. Detects anomalies using statistical methods (z-score, IQR)
3. Identifies unusual spikes or drops
4. Flags entities with abnormal behavior

Output insights as JSON to stdout with type="anomaly_detection".
"""
        
        elif state.analysis_type == AnalysisType.USAGE_PATTERNS:
            return base_context + """
Please analyze this energy data and generate a Python script that:
1. Identifies daily usage patterns (morning, afternoon, evening, night)
2. Compares weekday vs weekend consumption
3. Detects recurring patterns
4. Suggests optimal automation schedules

Output insights as JSON to stdout with type="usage_pattern".
"""
        
        elif state.analysis_type == AnalysisType.DIAGNOSTIC:
            instructions = state.custom_query or "Perform a general diagnostic analysis"
            diagnostic_ctx = state.diagnostic_context or "No additional diagnostic context provided."

            return base_context + f"""
**DIAGNOSTIC MODE** — The Architect has gathered evidence about a system issue
and needs your help analyzing it.

**Architect's Collected Evidence:**
{diagnostic_ctx}

**Investigation Instructions:**
{instructions}

Please generate a Python script that:
1. Analyzes the provided entity data for gaps, missing values, and anomalies
2. Checks for periods with no data (connectivity issues)
3. Identifies state transitions that suggest integration failures
4. Correlates any patterns with the diagnostic context above
5. Provides specific findings about root cause and affected time periods

Output insights as JSON to stdout with type="diagnostic".
Each insight should include:
- title: Short description of the finding
- description: Detailed explanation
- impact: "critical", "high", "medium", or "low"
- confidence: 0.0-1.0
- evidence: Supporting data points
- recommendation: What to do about it
"""

        elif state.analysis_type == AnalysisType.BEHAVIOR_ANALYSIS:
            return base_context + """
Please analyze this behavioral data and generate a Python script that:
1. Identifies the most frequently manually controlled entities
2. Detects peak usage hours for manual interactions
3. Finds patterns in button/switch press timing
4. Suggests which manual actions could benefit from automation

Output insights as JSON to stdout with type="behavioral_pattern".
"""

        elif state.analysis_type == AnalysisType.AUTOMATION_ANALYSIS:
            return base_context + """
Please analyze this automation effectiveness data and generate a Python script that:
1. Ranks automations by effectiveness (trigger count vs manual overrides)
2. Identifies automations with high manual override rates
3. Suggests improvements for inefficient automations
4. Calculates overall automation coverage

Output insights as JSON to stdout with type="automation_inefficiency" for issues
and type="behavioral_pattern" for positive findings.
"""

        elif state.analysis_type == AnalysisType.AUTOMATION_GAP_DETECTION:
            return base_context + """
Please analyze this automation gap data and generate a Python script that:
1. Identifies the strongest repeating manual patterns
2. Ranks gaps by frequency and confidence
3. Generates specific automation trigger/action suggestions for each gap
4. Estimates effort saved if each gap were automated

Output insights as JSON to stdout with type="automation_gap".
Include proposed_trigger and proposed_action in the evidence for each insight.
"""

        elif state.analysis_type == AnalysisType.CORRELATION_DISCOVERY:
            return base_context + """
Please analyze this entity correlation data and generate a Python script that:
1. Identifies the strongest entity correlations (devices used together)
2. Visualizes correlation patterns (timing, frequency)
3. Suggests automation groups based on correlated entities
4. Detects unexpected correlations that may indicate issues

Output insights as JSON to stdout with type="correlation".
"""

        elif state.analysis_type == AnalysisType.DEVICE_HEALTH:
            return base_context + """
Please analyze this device health data and generate a Python script that:
1. Identifies devices that appear unresponsive or degraded
2. Detects devices with unusual state change patterns
3. Flags devices with high unavailable/unknown state ratios
4. Provides health scores and recommended actions per device

Output insights as JSON to stdout with type="device_health".
"""

        elif state.analysis_type == AnalysisType.COST_OPTIMIZATION:
            return base_context + """
Please analyze this data and generate a Python script that:
1. Identifies the highest energy consumers
2. Calculates cost projections based on usage patterns
3. Suggests schedule changes to reduce costs (off-peak shifting)
4. Estimates monthly savings for each recommendation

Output insights as JSON to stdout with type="cost_saving".
Include estimated_monthly_savings in the evidence for each insight.
"""

        else:  # CUSTOM or other
            custom_query = state.custom_query or "Perform a general energy analysis"
            return base_context + f"""
Custom analysis request: {custom_query}

Generate a Python script that addresses this request.
Output insights as JSON to stdout.
"""

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
        energy_data: dict[str, Any],
    ) -> SandboxResult:
        """Execute analysis script in sandbox.

        Args:
            script: Python script to execute
            energy_data: Data to pass to script

        Returns:
            Sandbox execution result
        """
        import json
        import tempfile
        from pathlib import Path

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
            try:
                data_path.unlink()
            except Exception:
                pass

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
            return [{
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
            }]

        # Try to parse JSON from stdout
        import json
        
        try:
            output = json.loads(result.stdout)
            insights = output.get("insights", [])
            
            # Validate and normalize insights
            normalized = []
            for insight in insights:
                normalized.append({
                    "type": insight.get("type", "custom"),
                    "title": insight.get("title", "Untitled Insight"),
                    "description": insight.get("description", ""),
                    "confidence": min(1.0, max(0.0, float(insight.get("confidence", 0.5)))),
                    "impact": insight.get("impact", "medium"),
                    "evidence": insight.get("evidence", {}),
                    "entities": insight.get("entities", state.entity_ids),
                })
            
            return normalized

        except json.JSONDecodeError:
            # Fallback: create insight from raw output
            return [{
                "type": state.analysis_type.value,
                "title": f"{state.analysis_type.value.replace('_', ' ').title()} Results",
                "description": result.stdout[:2000],
                "confidence": 0.5,
                "impact": "medium",
                "evidence": {"raw_output": result.stdout[:500]},
                "entities": state.entity_ids,
            }]

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

        import json
        
        try:
            output = json.loads(result.stdout)
            return output.get("recommendations", [])
        except (json.JSONDecodeError, KeyError):
            return []

    def _generate_automation_suggestion(
        self,
        insights: list[dict[str, Any]],
    ) -> AutomationSuggestion | None:
        """Generate a structured automation suggestion from high-value insights.

        Scans insights for high-confidence (>=0.7) and high/critical impact
        findings that could be addressed by a Home Assistant automation.

        Args:
            insights: List of insight dictionaries

        Returns:
            An AutomationSuggestion model, or None if no suggestion.
        """
        for insight in insights:
            confidence = insight.get("confidence", 0)
            impact = insight.get("impact", "low")
            insight_type = insight.get("type", "")

            # Only suggest automations for actionable, high-confidence findings
            if confidence >= 0.7 and impact in ("high", "critical"):
                title = insight.get("title", "Untitled")
                description = insight.get("description", "")
                entities = insight.get("entities", [])
                evidence = insight.get("evidence", {})

                # Determine proposed trigger and action based on insight type
                proposed_trigger = ""
                proposed_action = ""

                if insight_type in ("energy_optimization", "cost_saving"):
                    proposed_trigger = "time: off-peak hours"
                    proposed_action = (
                        "Schedule energy-intensive devices during off-peak hours"
                    )
                elif insight_type == "automation_gap":
                    proposed_trigger = evidence.get(
                        "proposed_trigger",
                        f"time: {evidence.get('typical_time', 'detected pattern time')}",
                    )
                    proposed_action = evidence.get(
                        "proposed_action",
                        f"Automate the manual pattern: {title}",
                    )
                elif insight_type == "automation_inefficiency":
                    proposed_trigger = "existing automation trigger"
                    proposed_action = f"Improve automation: {title}"
                elif insight_type == "anomaly_detection":
                    proposed_trigger = "state change pattern"
                    proposed_action = (
                        "Alert or take corrective action when anomaly recurs"
                    )
                elif insight_type in ("usage_pattern", "behavioral_pattern"):
                    proposed_trigger = "detected usage schedule"
                    proposed_action = (
                        "Optimize device scheduling to match actual usage"
                    )
                elif insight_type == "correlation":
                    proposed_trigger = "state change of correlated entity"
                    proposed_action = (
                        "Synchronize correlated entities automatically"
                    )
                elif insight_type == "device_health":
                    proposed_trigger = "device unavailable for > threshold"
                    proposed_action = "Send notification about device health issue"
                else:
                    proposed_trigger = "detected pattern"
                    proposed_action = f"Address: {title}"

                return AutomationSuggestion(
                    pattern=(
                        f"{title}: {description[:200]}"
                    ),
                    entities=entities[:10],
                    proposed_trigger=proposed_trigger,
                    proposed_action=proposed_action,
                    confidence=confidence,
                    evidence=evidence,
                    source_insight_type=insight_type,
                )

        return None

    async def _persist_insights(
        self,
        insights: list[dict[str, Any]],
        session: Any,
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
                title=insight_data.get("title", "Analysis Result"),
                description=insight_data.get("description", ""),
                evidence=insight_data.get("evidence", {}),
                confidence=insight_data.get("confidence", 0.5),
                impact=insight_data.get("impact", "medium"),
                entities=insight_data.get("entities", []),
                script_path=None,  # Could store in MLflow artifacts
                script_output={"stdout": insight_data.get("raw_output", "")[:1000]},
                mlflow_run_id=state.mlflow_run_id,
            )
            insight_ids.append(insight.id)

        log_metric("insights.persisted", float(len(insight_ids)))
        
        return insight_ids


class DataScientistWorkflow:
    """Workflow implementation for the Data Scientist agent.

    Orchestrates the analysis process:
    1. Initialize analysis state
    2. Collect energy data
    3. Generate and execute analysis script
    4. Extract and persist insights
    5. Return results
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize the Data Scientist workflow.

        Args:
            mcp_client: Optional MCP client
        """
        self._settings = get_settings()
        self.agent = DataScientistAgent(mcp_client=mcp_client)

    async def run_analysis(
        self,
        analysis_type: AnalysisType = AnalysisType.ENERGY_OPTIMIZATION,
        entity_ids: list[str] | None = None,
        hours: int = 24,
        custom_query: str | None = None,
        diagnostic_context: str | None = None,
        session: Any = None,
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
        # Initialize state
        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=analysis_type,
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=custom_query,
            diagnostic_context=diagnostic_context,
        )

        with start_experiment_run(run_name="data_scientist_analysis") as run:
            if run:
                state.mlflow_run_id = run.info.run_id if hasattr(run, "info") else None

            log_param("analysis_type", analysis_type.value)
            log_param("hours", hours)
            log_param("entity_count", len(entity_ids) if entity_ids else "auto")

            try:
                # Run the agent
                updates = await self.agent.invoke(state, session=session)
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(state, key):
                        setattr(state, key, value)

                # Log final metrics
                log_metric("insights.count", float(len(state.insights)))
                log_metric("recommendations.count", float(len(state.recommendations)))

            except Exception as e:
                log_param("error", str(e)[:500])
                state.insights.append({
                    "type": "error",
                    "title": "Analysis Failed",
                    "description": str(e),
                    "confidence": 0.0,
                    "impact": "low",
                    "evidence": {},
                    "entities": [],
                })
                raise

        return state


# Exports
__all__ = [
    "DataScientistAgent",
    "DataScientistWorkflow",
    "DATA_SCIENTIST_SYSTEM_PROMPT",
    "DATA_SCIENTIST_BEHAVIORAL_PROMPT",
    "BEHAVIORAL_ANALYSIS_TYPES",
]
