"""Team analysis workflow - multi-specialist DS pipeline.

Runs Energy → Behavioral → Diagnostic → Synthesis pipeline.
The Architect can invoke this for comprehensive home analysis.
"""

from __future__ import annotations

from src.graph import END, START, StateGraph, create_graph
from src.graph.state import AnalysisState, TeamAnalysis


def build_team_analysis_graph() -> StateGraph:
    """Build the multi-specialist team analysis workflow graph.

    Runs all three DS team specialists sequentially, then synthesizes
    findings using the programmatic synthesizer.

    Graph structure:
    START -> energy -> behavioral -> diagnostic -> synthesize -> END
    """
    from src.agents.behavioral_analyst import BehavioralAnalyst
    from src.agents.diagnostic_analyst import DiagnosticAnalyst
    from src.agents.energy_analyst import EnergyAnalyst
    from src.tracing import traced_node

    graph = create_graph(AnalysisState)

    async def _energy_analysis(state: AnalysisState) -> dict:
        analyst = EnergyAnalyst()
        return await analyst.invoke(state)

    async def _behavioral_analysis(state: AnalysisState) -> dict:
        analyst = BehavioralAnalyst()
        return await analyst.invoke(state)

    async def _diagnostic_analysis(state: AnalysisState) -> dict:
        analyst = DiagnosticAnalyst()
        return await analyst.invoke(state)

    async def _synthesize(state: AnalysisState) -> dict:
        from src.agents.synthesis import SynthesisStrategy, synthesize

        if state.team_analysis:
            result = synthesize(state.team_analysis, strategy=SynthesisStrategy.PROGRAMMATIC)
            return {"team_analysis": result}
        return {}

    graph.add_node("energy", traced_node("energy", _energy_analysis))
    graph.add_node("behavioral", traced_node("behavioral", _behavioral_analysis))
    graph.add_node("diagnostic", traced_node("diagnostic", _diagnostic_analysis))
    graph.add_node("synthesize", traced_node("synthesize", _synthesize))

    graph.add_edge(START, "energy")
    graph.add_edge("energy", "behavioral")
    graph.add_edge("behavioral", "diagnostic")
    graph.add_edge("diagnostic", "synthesize")
    graph.add_edge("synthesize", END)

    return graph


class TeamAnalysisWorkflow:
    """Convenience wrapper for the multi-specialist team analysis.

    Runs Energy -> Behavioral -> Diagnostic -> Synthesis pipeline.
    The Architect can invoke this for comprehensive home analysis.
    """

    def __init__(self) -> None:
        """Initialize with specialist instances."""
        from src.agents.behavioral_analyst import BehavioralAnalyst
        from src.agents.diagnostic_analyst import DiagnosticAnalyst
        from src.agents.energy_analyst import EnergyAnalyst

        self._energy = EnergyAnalyst()
        self._behavioral = BehavioralAnalyst()
        self._diagnostic = DiagnosticAnalyst()

    async def run(
        self,
        query: str = "Full home analysis",
        hours: int = 24,
        entity_ids: list[str] | None = None,
    ) -> TeamAnalysis:
        """Run the full multi-specialist analysis pipeline.

        Args:
            query: What to analyze.
            hours: Hours of history.
            entity_ids: Specific entities to focus on.

        Returns:
            Synthesized TeamAnalysis.
        """
        from uuid import uuid4

        from src.agents.synthesis import SynthesisStrategy, synthesize

        # Create initial state with shared TeamAnalysis
        ta = TeamAnalysis(
            request_id=str(uuid4()),
            request_summary=query,
        )
        state = AnalysisState(
            entity_ids=entity_ids or [],
            time_range_hours=hours,
            custom_query=query,
            team_analysis=ta,
        )

        # Run specialists sequentially (each reads prior findings)
        energy_result = await self._energy.invoke(state)
        if energy_result.get("team_analysis"):
            state.team_analysis = energy_result["team_analysis"]

        behavioral_result = await self._behavioral.invoke(state)
        if behavioral_result.get("team_analysis"):
            state.team_analysis = behavioral_result["team_analysis"]

        diagnostic_result = await self._diagnostic.invoke(state)
        if diagnostic_result.get("team_analysis"):
            state.team_analysis = diagnostic_result["team_analysis"]

        # Synthesize findings
        if state.team_analysis:
            return synthesize(state.team_analysis, strategy=SynthesisStrategy.PROGRAMMATIC)

        return ta
