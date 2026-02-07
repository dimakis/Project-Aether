"""Analysis workflow nodes for Data Scientist agent.

These nodes handle energy data collection, script generation, sandbox execution,
insight extraction, and optimization analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage

from src.graph.state import AnalysisState, ScriptExecution

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.ha.client import HAClient


async def collect_energy_data_node(
    state: AnalysisState,
    ha_client: HAClient | None = None,
) -> dict[str, object]:
    """Collect energy data from Home Assistant.

    Fetches energy sensor history and prepares data for analysis.

    Args:
        state: Current analysis state
        ha_client: HA client for HA communication

    Returns:
        State updates with collected energy data
    """
    from src.graph.state import AnalysisState
    from src.ha import EnergyHistoryClient, get_ha_client

    ha = ha_client or get_ha_client()
    energy_client = EnergyHistoryClient(ha)

    # Discover energy sensors if not specified
    entity_ids = state.entity_ids
    if not entity_ids:
        sensors = await energy_client.get_energy_sensors()
        entity_ids = [s["entity_id"] for s in sensors[:20]]

    # Get aggregated energy data
    energy_data = await energy_client.get_aggregated_energy(
        entity_ids,
        hours=state.time_range_hours,
    )

    return {
        "entity_ids": entity_ids,
        "messages": [
            AIMessage(
                content=f"Collected data from {len(entity_ids)} energy sensors "
                f"over {state.time_range_hours} hours. "
                f"Total consumption: {energy_data.get('total_kwh', 0):.2f} kWh"
            )
        ],
    }


async def generate_script_node(
    state: AnalysisState,
    session: AsyncSession | None = None,
) -> dict[str, object]:
    """Generate analysis script using Data Scientist agent.

    Uses LLM to generate a Python script for energy analysis.

    Args:
        state: Current analysis state with energy data
        session: Optional database session

    Returns:
        State updates with generated script
    """
    from src.agents import DataScientistAgent
    from src.ha import EnergyHistoryClient, get_ha_client

    agent = DataScientistAgent()

    # Get energy data for script generation
    ha = get_ha_client()
    energy_client = EnergyHistoryClient(ha)
    energy_data = await energy_client.get_aggregated_energy(
        state.entity_ids,
        hours=state.time_range_hours,
    )

    # Generate script
    script = await agent._generate_script(state, energy_data)

    return {
        "generated_script": script,
        "messages": [
            AIMessage(content=f"Generated analysis script ({script.count(chr(10)) + 1} lines)")
        ],
    }


async def execute_sandbox_node(
    state: AnalysisState,
) -> dict[str, object]:
    """Execute analysis script in sandboxed environment.

    Constitution: Isolation - runs in gVisor sandbox.

    Args:
        state: State with generated script

    Returns:
        State updates with execution results
    """
    from src.graph.state import ScriptExecution
    from src.ha import EnergyHistoryClient, get_ha_client
    from src.sandbox.runner import SandboxRunner

    if not state.generated_script:
        return {
            "messages": [AIMessage(content="No script to execute")],
        }

    # Get fresh energy data for execution
    ha = get_ha_client()
    energy_client = EnergyHistoryClient(ha)
    energy_data = await energy_client.get_aggregated_energy(
        state.entity_ids,
        hours=state.time_range_hours,
    )

    # Execute in sandbox
    import json
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(energy_data, f, default=str)
        data_path = Path(f.name)

    try:
        sandbox = SandboxRunner()
        started_at = datetime.now(timezone.utc)
        result = await sandbox.run(state.generated_script, data_path=data_path)
        completed_at = datetime.now(timezone.utc)

        execution = ScriptExecution(
            script_content=state.generated_script[:5000],
            started_at=started_at,
            completed_at=completed_at,
            stdout=result.stdout[:5000],
            stderr=result.stderr[:2000],
            exit_code=result.exit_code,
            sandbox_policy=result.policy_name,
            timed_out=result.timed_out,
        )

        status_msg = "completed successfully" if result.success else f"failed (exit code {result.exit_code})"

        return {
            "script_executions": [execution],
            "messages": [
                AIMessage(
                    content=f"Script execution {status_msg} in {result.duration_seconds:.2f}s"
                )
            ],
        }

    finally:
        try:
            data_path.unlink()
        except Exception:
            pass


async def extract_insights_node(
    state: AnalysisState,
    session: AsyncSession | None = None,
) -> dict[str, object]:
    """Extract insights from script execution output.

    Parses JSON output and persists insights to database.

    Args:
        state: State with script execution results
        session: Database session for persistence

    Returns:
        State updates with extracted insights
    """
    from src.agents import DataScientistAgent
    from src.dal import InsightRepository
    from src.sandbox.runner import SandboxResult
    from src.storage.entities.insight import InsightStatus, InsightType

    if not state.script_executions:
        return {"messages": [AIMessage(content="No execution results to extract from")]}

    # Get latest execution
    execution = state.script_executions[-1]

    # Calculate duration if timestamps available
    duration = 0.0
    if execution.completed_at and execution.started_at:
        duration = (execution.completed_at - execution.started_at).total_seconds()

    # Create SandboxResult for insight extraction
    result = SandboxResult(
        success=execution.exit_code == 0,
        exit_code=execution.exit_code or 0,
        stdout=execution.stdout or "",
        stderr=execution.stderr or "",
        duration_seconds=duration,
        policy_name=execution.sandbox_policy,
        timed_out=execution.timed_out,
    )

    # Extract insights using agent
    agent = DataScientistAgent()
    insights = agent._extract_insights(result, state)
    recommendations = agent._extract_recommendations(result)

    # Persist if session available
    if session and insights:
        repo = InsightRepository(session)
        for insight_data in insights:
            try:
                insight_type = InsightType(insight_data.get("type", "energy_optimization"))
            except ValueError:
                insight_type = InsightType.ENERGY_OPTIMIZATION

            await repo.create(
                type=insight_type,
                title=insight_data.get("title", "Analysis Result"),
                description=insight_data.get("description", ""),
                evidence=insight_data.get("evidence", {}),
                confidence=insight_data.get("confidence", 0.5),
                impact=insight_data.get("impact", "medium"),
                entities=insight_data.get("entities", state.entity_ids),
                mlflow_run_id=state.mlflow_run_id,
            )

    return {
        "insights": insights,
        "recommendations": recommendations,
        "messages": [
            AIMessage(
                content=f"Extracted {len(insights)} insights and {len(recommendations)} recommendations"
            )
        ],
    }


async def analysis_error_node(
    state: AnalysisState,
    error: Exception,
) -> dict[str, object]:
    """Handle errors in analysis workflow.

    Args:
        state: Current state
        error: The exception that occurred

    Returns:
        State updates with error info
    """
    error_msg = f"{type(error).__name__}: {error}"

    return {
        "insights": [
            {
                "type": "error",
                "title": "Analysis Failed",
                "description": error_msg,
                "confidence": 0.0,
                "impact": "low",
                "evidence": {"error": str(error)},
                "entities": state.entity_ids,
            }
        ],
        "messages": [
            AIMessage(
                content=f"Analysis encountered an error: {error_msg}. "
                "Please check your entity selection and try again."
            )
        ],
    }


# =============================================================================
# OPTIMIZATION NODES (Feature 03: Intelligent Optimization)
# =============================================================================


async def collect_behavioral_data_node(
    state: AnalysisState,
    ha_client: HAClient | None = None,
) -> dict[str, object]:
    """Collect behavioral data from logbook for optimization analysis.

    Uses BehavioralAnalysisClient to gather logbook-based data
    for behavioral pattern detection.

    Args:
        state: Current analysis state
        ha_client: Optional HA client

    Returns:
        State updates with collected data in messages
    """
    from src.ha import BehavioralAnalysisClient, LogbookHistoryClient, get_ha_client

    ha = ha_client or get_ha_client()
    logbook = LogbookHistoryClient(ha)

    try:
        stats = await logbook.get_stats(hours=state.time_range_hours)

        return {
            "messages": [
                AIMessage(
                    content=(
                        f"Collected behavioral data: {stats.total_entries} entries, "
                        f"{stats.automation_triggers} automation triggers, "
                        f"{stats.manual_actions} manual actions, "
                        f"{stats.unique_entities} unique entities."
                    )
                )
            ],
        }
    except Exception as e:
        return {
            "messages": [
                AIMessage(content=f"Failed to collect behavioral data: {e}")
            ],
        }


async def analyze_and_suggest_node(
    state: AnalysisState,
    session: AsyncSession | None = None,
) -> dict[str, object]:
    """Run Data Scientist analysis and generate suggestions.

    Delegates to DataScientistAgent.invoke() which handles
    both energy and behavioral analysis based on analysis_type.

    Args:
        state: Current analysis state
        session: Optional database session

    Returns:
        State updates with insights, recommendations, and automation suggestion
    """
    from src.agents import DataScientistAgent

    agent = DataScientistAgent()
    from src.api.metrics import get_metrics_collector

    metrics = get_metrics_collector()
    metrics.record_agent_invocation(agent.role.value)

    try:
        updates = await agent.invoke(state, session=session)
        return updates
    except Exception as e:
        return {
            "insights": [{
                "type": "error",
                "title": "Analysis Failed",
                "description": str(e),
                "confidence": 0.0,
                "impact": "low",
                "evidence": {},
                "entities": state.entity_ids,
            }],
        }


async def architect_review_node(
    state: AnalysisState,
    session: AsyncSession | None = None,
) -> dict[str, object]:
    """Have the Architect review DS suggestions and create proposals.

    If the Data Scientist generated an AutomationSuggestion,
    passes it to the Architect for refinement into a full proposal.

    Args:
        state: Current analysis state with automation_suggestion
        session: Database session for proposal creation

    Returns:
        State updates with Architect's response
    """
    suggestion = state.automation_suggestion
    if not suggestion:
        return {
            "messages": [
                AIMessage(
                    content="No automation suggestions to review."
                )
            ],
        }

    from src.agents import ArchitectAgent

    architect = ArchitectAgent()

    try:
        result = await architect.receive_suggestion(suggestion, session)

        response_text = result.get("response", "No response from Architect")
        proposal_name = result.get("proposal_name")
        proposal_yaml = result.get("proposal_yaml")

        parts = []
        if proposal_name:
            parts.append(f"Architect created proposal: {proposal_name}")
        if proposal_yaml:
            parts.append(f"YAML:\n{proposal_yaml}")
        parts.append(response_text[:500])

        return {
            "messages": [
                AIMessage(content="\n".join(parts))
            ],
        }
    except Exception as e:
        return {
            "messages": [
                AIMessage(content=f"Architect review failed: {e}")
            ],
        }


async def present_recommendations_node(
    state: AnalysisState,
) -> dict[str, object]:
    """Format final optimization output for the user.

    Combines insights, recommendations, and automation suggestions
    into a final summary message.

    Args:
        state: Final analysis state

    Returns:
        State updates with formatted summary
    """
    insights = state.insights or []
    recommendations = state.recommendations or []

    parts = [f"**Optimization Analysis Complete**"]
    parts.append(f"Found {len(insights)} insight(s) and {len(recommendations)} recommendation(s).")

    if insights:
        parts.append("\n**Top Insights:**")
        for i, insight in enumerate(insights[:5], 1):
            title = insight.get("title", "Finding")
            impact = insight.get("impact", "medium")
            parts.append(f"{i}. [{impact.upper()}] {title}")

    if recommendations:
        parts.append("\n**Recommendations:**")
        for rec in recommendations[:5]:
            parts.append(f"• {rec}")

    suggestion = state.automation_suggestion
    if suggestion:
        parts.append(f"\n**Automation Proposal:** {suggestion.pattern[:200]}")

    return {
        "messages": [
            AIMessage(content="\n".join(parts))
        ],
    }
