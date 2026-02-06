"""Data Scientist agent for energy analysis and insights.

User Story 3: Energy Optimization Suggestions.

The Data Scientist analyzes energy data from Home Assistant,
generates Python scripts for analysis, executes them in a
sandboxed environment, and extracts actionable insights.

Constitution: Isolation - All scripts run in gVisor sandbox.
Constitution: Observability - All analysis traced in MLflow.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents import BaseAgent
from src.dal import EntityRepository, InsightRepository
from src.graph.state import AgentRole, AnalysisState, AnalysisType
from src.llm import get_llm
from src.mcp import EnergyHistoryClient, MCPClient, get_mcp_client
from src.sandbox.runner import SandboxResult, SandboxRunner
from src.settings import get_settings
from src.storage.entities.insight import InsightStatus, InsightType
from src.tracing import log_metric, log_param, start_experiment_run


# System prompt for the Data Scientist
DATA_SCIENTIST_SYSTEM_PROMPT = """You are an expert data scientist specializing in home energy analysis and system diagnostics.

Your role is to analyze energy sensor data from Home Assistant and generate insights
that help users optimize their energy consumption. You also perform diagnostic
analysis when asked to troubleshoot issues with sensors, integrations, or data quality.

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
        """Get LLM, creating if needed."""
        if self._llm is None:
            self._llm = get_llm()
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
        trace_inputs = {
            "analysis_type": state.analysis_type.value,
            "entity_ids": state.entity_ids[:10] if state.entity_ids else [],
            "time_range_hours": state.time_range_hours,
        }

        async with self.trace_span("analyze", state, inputs=trace_inputs) as span:
            try:
                # 1. Collect energy data (uses DB for discovery, MCP for history)
                session = kwargs.get("session")
                energy_data = await self._collect_energy_data(state, session=session)
                
                # 2. Generate analysis script
                script = await self._generate_script(state, energy_data)
                state.generated_script = script
                
                # 3. Execute in sandbox
                result = await self._execute_script(script, energy_data)
                
                # 4. Extract insights from output
                insights = self._extract_insights(result, state)
                
                # 5. Save insights to database (if session provided)
                session = kwargs.get("session")
                if session and insights:
                    await self._persist_insights(insights, session, state)
                
                # Update state
                updates = {
                    "insights": insights,
                    "generated_script": script,
                    "recommendations": self._extract_recommendations(result),
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
        
        messages = [
            SystemMessage(content=DATA_SCIENTIST_SYSTEM_PROMPT),
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
]
