"""LangGraph workflows for agent orchestration.

Defines the graph structures that connect nodes into complete workflows.
All workflow entry points start a trace session for correlation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from langgraph.checkpoint.memory import MemorySaver

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.ha.client import HAClient

from src.graph import END, START, StateGraph, create_graph
from src.graph.nodes import (
    # Discovery nodes
    fetch_entities_node,
    finalize_discovery_node,
    infer_areas_node,
    infer_devices_node,
    initialize_discovery_node,
    persist_entities_node,
    sync_automations_node,
    # Conversation nodes
    approval_gate_node,
    architect_propose_node,
    conversation_error_node,
    developer_deploy_node,
    developer_rollback_node,
    process_approval_node,
    # Analysis nodes (User Story 3)
    analysis_error_node,
    collect_energy_data_node,
    execute_sandbox_node,
    extract_insights_node,
    generate_script_node,
)
from src.graph.state import (
    AgentRole,
    AnalysisState,
    AnalysisType,
    ConversationState,
    ConversationStatus,
    DiscoveryState,
    DiscoveryStatus,
    TeamAnalysis,
)
from src.tracing import start_experiment_run, trace_with_uri


def build_discovery_graph(
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
) -> StateGraph:
    """Build the entity discovery workflow graph.

    Graph structure:
    ```
    START
      │
      ▼
    initialize
      │
      ▼
    fetch_entities
      │
      ├─────────────┐
      ▼             ▼
    infer_devices  infer_areas
      │             │
      └──────┬──────┘
             ▼
       sync_automations
             │
             ▼
       persist_entities
             │
             ▼
       finalize
             │
             ▼
           END
    ```

    Args:
        ha_client: Optional HA client to inject
        session: Optional database session to inject

    Returns:
        Configured StateGraph
    """
    graph = create_graph(DiscoveryState)

    # Define node wrappers that inject dependencies
    async def _initialize(state: DiscoveryState) -> dict[str, object]:
        return await initialize_discovery_node(state)

    async def _fetch_entities(state: DiscoveryState) -> dict[str, object]:
        return await fetch_entities_node(state, ha_client=ha_client)

    async def _infer_devices(state: DiscoveryState) -> dict[str, object]:
        return await infer_devices_node(state, ha_client=ha_client)

    async def _infer_areas(state: DiscoveryState) -> dict[str, object]:
        return await infer_areas_node(state, ha_client=ha_client)

    async def _sync_automations(state: DiscoveryState) -> dict[str, object]:
        return await sync_automations_node(state, ha_client=ha_client)

    async def _persist_entities(state: DiscoveryState) -> dict[str, object]:
        return await persist_entities_node(
            state, session=session, ha_client=ha_client
        )

    async def _finalize(state: DiscoveryState) -> dict[str, object]:
        return await finalize_discovery_node(state)

    # Add nodes
    graph.add_node("initialize", _initialize)
    graph.add_node("fetch_entities", _fetch_entities)
    graph.add_node("infer_devices", _infer_devices)
    graph.add_node("infer_areas", _infer_areas)
    graph.add_node("sync_automations", _sync_automations)
    graph.add_node("persist_entities", _persist_entities)
    graph.add_node("finalize", _finalize)

    # Define edges
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "fetch_entities")

    # Parallel inference (conceptually - LangGraph handles sequentially)
    graph.add_edge("fetch_entities", "infer_devices")
    graph.add_edge("infer_devices", "infer_areas")

    # Continue to automation sync
    graph.add_edge("infer_areas", "sync_automations")
    graph.add_edge("sync_automations", "persist_entities")
    graph.add_edge("persist_entities", "finalize")
    graph.add_edge("finalize", END)

    return graph


@trace_with_uri(name="workflow.run_discovery", span_type="CHAIN")
async def run_discovery_workflow(
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
    initial_state: DiscoveryState | None = None,
) -> DiscoveryState:
    """Execute the discovery workflow.

    Starts a trace session for correlation across all operations.

    Args:
        ha_client: Optional HA client
        session: Optional database session
        initial_state: Optional initial state

    Returns:
        Final discovery state
    """
    # Start a trace session for this workflow
    from src.tracing.context import session_context

    # Build the graph with injected dependencies
    graph = build_discovery_graph(ha_client=ha_client, session=session)

    # Compile the graph
    compiled = graph.compile()

    # Initialize state
    if initial_state is None:
        initial_state = DiscoveryState()

    # Run with MLflow tracking and session context
    import mlflow

    with session_context() as session_id:
        with start_experiment_run("discovery_workflow") as run:
            mlflow.set_tag("workflow", "discovery")
            mlflow.set_tag("session.id", session_id)

            try:
                # Execute the graph
                final_state = await compiled.ainvoke(initial_state)

                # Handle the result
                if isinstance(final_state, dict):
                    # Merge into state
                    result = initial_state.model_copy(update=final_state)
                else:
                    result = final_state

                mlflow.set_tag("status", result.status.value)
                return result

            except Exception as e:
                mlflow.set_tag("status", "failed")
                mlflow.log_param("error", str(e)[:500])
                raise


def build_simple_discovery_graph() -> StateGraph:
    """Build a simplified discovery graph for testing.

    This version doesn't require external dependencies and
    is useful for unit testing the graph structure.

    Returns:
        Simple StateGraph
    """
    graph = create_graph(DiscoveryState)

    async def mock_discover(state: DiscoveryState) -> dict[str, object]:
        return {
            "status": DiscoveryStatus.COMPLETED,
            "entities_added": 0,
            "entities_updated": 0,
        }

    graph.add_node("discover", mock_discover)
    graph.add_edge(START, "discover")
    graph.add_edge("discover", END)

    return graph


# =============================================================================
# CONVERSATION WORKFLOW (User Story 2: Architect/Developer)
# =============================================================================


def build_conversation_graph(
    session: AsyncSession | None = None,
    checkpointer: object | None = None,
) -> StateGraph:
    """Build the conversation workflow graph for automation design.

    Graph structure:
    ```
    START
      │
      ▼
    architect_propose  ◄────────┐
      │                        │
      ▼                        │
    [has_proposal?]            │
      │     │                  │
      Y     N──────► END       │
      │                        │
      ▼                        │
    approval_gate (HITL)       │
      │                        │
      ▼                        │
    process_approval           │
      │                        │
      ├── approved ───► deploy │
      │                   │    │
      │                   ▼    │
      │                  END   │
      │                        │
      └── rejected ────────────┘ (refine loop)
    ```

    Constitution: Safety First - HITL approval required before deployment.

    Args:
        session: Database session for persistence
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Configured StateGraph with HITL interrupt
    """
    graph = create_graph(ConversationState)

    # Define node wrappers with injected dependencies
    async def _architect_propose(state: ConversationState) -> dict[str, object]:
        return await architect_propose_node(state, session=session)

    async def _approval_gate(state: ConversationState) -> dict[str, object]:
        return await approval_gate_node(state)

    async def _process_approval(state: ConversationState) -> dict[str, object]:
        # Default to rejection if no explicit approval
        # Real approval happens via external input before resuming
        approved = state.status == ConversationStatus.APPROVED
        return await process_approval_node(
            state,
            approved=approved,
            session=session,
        )

    async def _deploy(state: ConversationState) -> dict[str, object]:
        if state.approved_items:
            proposal_id = state.approved_items[-1]
            return await developer_deploy_node(state, proposal_id, session=session)
        return {"error": "No approved proposals to deploy"}

    # Add nodes
    graph.add_node("architect_propose", _architect_propose)
    graph.add_node("approval_gate", _approval_gate)
    graph.add_node("process_approval", _process_approval)
    graph.add_node("deploy", _deploy)

    # Define routing
    def route_after_propose(
        state: ConversationState,
    ) -> Literal["approval_gate", "__end__"]:
        """Route based on whether proposal was created."""
        if state.pending_approvals:
            return "approval_gate"
        return END

    def route_after_approval(
        state: ConversationState,
    ) -> Literal["deploy", "architect_propose", "__end__"]:
        """Route based on approval decision."""
        if state.status == ConversationStatus.APPROVED:
            return "deploy"
        elif state.status == ConversationStatus.REJECTED:
            # Allow refinement loop
            return "architect_propose"
        return END

    # Define edges
    graph.add_edge(START, "architect_propose")
    graph.add_conditional_edges("architect_propose", route_after_propose)
    graph.add_edge("approval_gate", "process_approval")
    graph.add_conditional_edges("process_approval", route_after_approval)
    graph.add_edge("deploy", END)

    return graph


def compile_conversation_graph(
    session: AsyncSession | None = None,
    thread_id: str | None = None,
) -> object:
    """Compile the conversation graph with HITL interrupt.

    Constitution: Safety First - interrupt_before at approval_gate
    ensures human approval before any deployment.

    Args:
        session: Database session
        thread_id: Optional thread ID for checkpointing

    Returns:
        Compiled graph with checkpointing and HITL interrupts
    """
    # Create checkpointer for state persistence
    checkpointer = MemorySaver()

    # Build graph
    graph = build_conversation_graph(session=session)

    # Compile with interrupt_before at approval gate
    # This pauses execution for HITL approval
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval_gate"],  # HITL: Pause before approval
    )

    return compiled


@trace_with_uri(name="workflow.run_conversation", span_type="CHAIN")
async def run_conversation_workflow(
    user_message: str,
    session: AsyncSession | None = None,
    thread_id: str | None = None,
    existing_state: ConversationState | None = None,
) -> ConversationState:
    """Execute the conversation workflow.

    Starts a trace session for correlation across all operations.

    Args:
        user_message: User's message
        session: Database session
        thread_id: Thread ID for checkpointing
        existing_state: Optional existing state to continue

    Returns:
        Updated conversation state
    """
    from langchain_core.messages import HumanMessage

    from src.tracing.context import session_context

    # Compile graph
    compiled = compile_conversation_graph(session=session, thread_id=thread_id)

    # Initialize or update state
    if existing_state:
        # Add new user message
        state = existing_state.model_copy()
        state.messages.append(HumanMessage(content=user_message))
    else:
        state = ConversationState(
            messages=[HumanMessage(content=user_message)],
        )

    # Run with MLflow tracking and session context
    import mlflow

    with session_context() as session_id:
        with start_experiment_run("conversation_workflow") as run:
            mlflow.set_tag("workflow", "conversation")
            mlflow.set_tag("thread_id", thread_id or state.conversation_id)
            mlflow.set_tag("session.id", session_id)

            try:
                # Execute the graph
                config = {
                    "configurable": {"thread_id": thread_id or state.conversation_id}
                }
                final_state = await compiled.ainvoke(state, config=config)

                # Handle the result
                if isinstance(final_state, dict):
                    result = state.model_copy(update=final_state)
                else:
                    result = final_state

                mlflow.set_tag("status", result.status.value)
                return result

            except Exception as e:
                mlflow.set_tag("status", "failed")
                mlflow.log_param("error", str(e)[:500])
                raise


@trace_with_uri(name="workflow.resume_after_approval", span_type="CHAIN")
async def resume_after_approval(
    thread_id: str,
    approved: bool,
    approved_by: str = "user",
    rejection_reason: str | None = None,
    session: AsyncSession | None = None,
) -> ConversationState:
    """Resume conversation workflow after HITL approval decision.

    Restores the trace session from the original workflow.

    Args:
        thread_id: Thread ID to resume
        approved: Whether proposal was approved
        approved_by: Who approved
        rejection_reason: Why rejected (if applicable)
        session: Database session

    Returns:
        Updated conversation state after resumption
    """
    from src.dal import ProposalRepository
    from src.tracing.context import session_context

    # Compile graph with same checkpointer
    compiled = compile_conversation_graph(session=session, thread_id=thread_id)
    config = {"configurable": {"thread_id": thread_id}}

    # Get current state
    state_snapshot = compiled.get_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise ValueError(f"No state found for thread {thread_id}")

    current_state = ConversationState(**state_snapshot.values)

    # Process approvals in database
    if session and current_state.pending_approvals:
        repo = ProposalRepository(session)
        for approval in current_state.pending_approvals:
            if approved:
                await repo.approve(approval.id, approved_by)
            else:
                await repo.reject(approval.id, rejection_reason or "User rejected")

    # Update state with approval decision
    if approved:
        current_state.status = ConversationStatus.APPROVED
        current_state.approved_items.extend(
            [a.id for a in current_state.pending_approvals]
        )
    else:
        current_state.status = ConversationStatus.REJECTED
        current_state.rejected_items.extend(
            [a.id for a in current_state.pending_approvals]
        )

    # Update the state in the graph
    compiled.update_state(config, current_state.model_dump())

    # Resume execution with session context
    import mlflow

    with session_context() as session_id:
        with start_experiment_run("conversation_workflow_resume") as run:
            mlflow.set_tag("workflow", "conversation_resume")
            mlflow.set_tag("thread_id", thread_id)
            mlflow.set_tag("session.id", session_id)
            mlflow.set_tag("approval.decision", "approved" if approved else "rejected")

            final_state = await compiled.ainvoke(None, config=config)

            if isinstance(final_state, dict):
                return current_state.model_copy(update=final_state)
            return final_state


# =============================================================================
# ANALYSIS WORKFLOW (User Story 3: Energy Optimization)
# =============================================================================


def build_analysis_graph(
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
) -> StateGraph:
    """Build the energy analysis workflow graph.

    Graph structure:
    ```
    START
      │
      ▼
    collect_data
      │
      ▼
    generate_script
      │
      ▼
    execute_sandbox
      │
      ▼
    extract_insights
      │
      ▼
    END
    ```

    Constitution: Isolation - scripts run in gVisor sandbox.

    Args:
        ha_client: Optional HA client to inject
        session: Optional database session for insight persistence

    Returns:
        Configured StateGraph
    """
    graph = create_graph(AnalysisState)

    # Define node wrappers with dependency injection
    async def _collect_data(state: AnalysisState) -> dict[str, object]:
        return await collect_energy_data_node(state, ha_client=ha_client)

    async def _generate_script(state: AnalysisState) -> dict[str, object]:
        return await generate_script_node(state, session=session)

    async def _execute_sandbox(state: AnalysisState) -> dict[str, object]:
        return await execute_sandbox_node(state)

    async def _extract_insights(state: AnalysisState) -> dict[str, object]:
        return await extract_insights_node(state, session=session)

    async def _handle_error(state: AnalysisState) -> dict[str, object]:
        # Get error from state if available
        error = Exception("Unknown error")
        return await analysis_error_node(state, error)

    # Add nodes
    graph.add_node("collect_data", _collect_data)
    graph.add_node("generate_script", _generate_script)
    graph.add_node("execute_sandbox", _execute_sandbox)
    graph.add_node("extract_insights", _extract_insights)
    graph.add_node("error", _handle_error)

    # Define flow
    graph.add_edge(START, "collect_data")
    graph.add_edge("collect_data", "generate_script")
    graph.add_edge("generate_script", "execute_sandbox")
    graph.add_edge("execute_sandbox", "extract_insights")
    graph.add_edge("extract_insights", END)
    graph.add_edge("error", END)

    return graph


async def run_analysis_workflow(
    analysis_type: str = "energy_optimization",
    entity_ids: list[str] | None = None,
    hours: int = 24,
    custom_query: str | None = None,
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
) -> AnalysisState:
    """Run an energy analysis workflow.

    Entry point for energy analysis. Starts a trace session
    for correlation across the workflow.

    Args:
        analysis_type: Type of analysis to perform
        entity_ids: Specific entities to analyze (None = auto-discover)
        hours: Hours of history to analyze
        custom_query: Custom analysis query
        ha_client: Optional HA client
        session: Database session for persistence

    Returns:
        Final analysis state with insights
    """
    import mlflow

    from src.graph.state import AnalysisType
    from src.tracing.context import session_context

    # Map string to enum
    try:
        analysis_enum = AnalysisType(analysis_type)
    except ValueError:
        analysis_enum = AnalysisType.ENERGY_OPTIMIZATION

    # Build initial state
    initial_state = AnalysisState(
        analysis_type=analysis_enum,
        entity_ids=entity_ids or [],
        time_range_hours=hours,
        custom_query=custom_query,
    )

    # Build and compile graph
    graph = build_analysis_graph(ha_client=ha_client, session=session)
    compiled = graph.compile()

    # Run with tracing
    with session_context() as session_id:
        with start_experiment_run("analysis_workflow") as run:
            if run:
                initial_state.mlflow_run_id = run.info.run_id if hasattr(run, "info") else None

            mlflow.set_tag("workflow", "analysis")
            mlflow.set_tag("session.id", session_id)
            mlflow.set_tag("analysis_type", analysis_type)

            final_state = await compiled.ainvoke(initial_state)

            if isinstance(final_state, dict):
                return initial_state.model_copy(update=final_state)
            return final_state


# =============================================================================
# OPTIMIZATION WORKFLOW (Feature 03: Intelligent Optimization)
# =============================================================================


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
        final_state = await compiled.ainvoke(initial_state)

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


# =============================================================================
# TEAM ANALYSIS WORKFLOW (DS Team Multi-Specialist)
# =============================================================================


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
        from src.agents.synthesis import synthesize, SynthesisStrategy

        if state.team_analysis:
            result = synthesize(state.team_analysis, strategy=SynthesisStrategy.PROGRAMMATIC)
            return {"team_analysis": result}
        return {}

    graph.add_node("energy", _energy_analysis)
    graph.add_node("behavioral", _behavioral_analysis)
    graph.add_node("diagnostic", _diagnostic_analysis)
    graph.add_node("synthesize", _synthesize)

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

    def __init__(self):
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
    ) -> "TeamAnalysis":
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


# =============================================================================
# DASHBOARD WORKFLOW
# =============================================================================


def build_dashboard_graph() -> StateGraph:
    """Build the dashboard designer workflow graph.

    Simple conversational loop: user <-> dashboard_designer agent.
    """
    from src.graph.state import DashboardState

    graph = StateGraph(DashboardState)

    async def dashboard_designer_node(state: DashboardState) -> dict:
        from src.agents.dashboard_designer import DashboardDesignerAgent

        agent = DashboardDesignerAgent()
        return await agent.invoke(state)

    graph.add_node("dashboard_designer", dashboard_designer_node)
    graph.add_edge(START, "dashboard_designer")
    graph.add_edge("dashboard_designer", END)

    return graph


class DashboardWorkflow:
    """High-level wrapper for the dashboard designer workflow."""

    def __init__(self) -> None:
        self.graph = build_dashboard_graph()

    async def run(self, user_message: str) -> dict:
        """Run the dashboard workflow with a user message.

        Args:
            user_message: The user's dashboard design request.

        Returns:
            Final state dict with messages and dashboard config.
        """
        from langchain_core.messages import HumanMessage
        from src.agents.dashboard_designer import DashboardDesignerAgent

        agent = DashboardDesignerAgent()
        from src.graph.state import DashboardState

        state = DashboardState()
        state.messages = [HumanMessage(content=user_message)]
        result = await agent.invoke(state)
        return result


# =============================================================================
# GRAPH REGISTRY
# =============================================================================

# Registry of available workflows
WORKFLOW_REGISTRY = {
    "discovery": build_discovery_graph,
    "discovery_simple": build_simple_discovery_graph,
    "conversation": build_conversation_graph,
    "analysis": build_analysis_graph,
    "optimization": build_optimization_graph,
    "team_analysis": build_team_analysis_graph,
    "dashboard": build_dashboard_graph,
}


def get_workflow(name: str, **kwargs: object) -> StateGraph:
    """Get a workflow graph by name.

    Args:
        name: Workflow name
        **kwargs: Arguments to pass to the builder

    Returns:
        Configured StateGraph

    Raises:
        ValueError: If workflow name is not found
    """
    if name not in WORKFLOW_REGISTRY:
        available = ", ".join(WORKFLOW_REGISTRY.keys())
        raise ValueError(f"Unknown workflow '{name}'. Available: {available}")

    return WORKFLOW_REGISTRY[name](**kwargs)
