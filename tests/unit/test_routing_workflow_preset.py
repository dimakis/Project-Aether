"""Unit tests for workflow preset routing (wiring audit fix).

Verifies that resolve_agent_routing and apply_routing_to_state
correctly propagate workflow_preset and disabled_agents.
"""

from __future__ import annotations

from src.agents.routing import (
    apply_routing_to_state,
    resolve_agent_routing,
)


class TestWorkflowPresetRouting:
    """resolve_agent_routing propagates workflow_preset and disabled_agents."""

    def test_auto_with_preset(self):
        decision = resolve_agent_routing(
            agent="auto",
            workflow_preset="full-analysis",
            disabled_agents=["diagnostic_analyst"],
        )
        assert decision.needs_orchestrator is True
        assert decision.workflow_preset == "full-analysis"
        assert decision.disabled_agents == ("diagnostic_analyst",)

    def test_specific_agent_with_preset(self):
        decision = resolve_agent_routing(
            agent="architect",
            workflow_preset="energy-only",
        )
        assert decision.active_agent == "architect"
        assert decision.workflow_preset == "energy-only"
        assert decision.disabled_agents == ()

    def test_no_preset(self):
        decision = resolve_agent_routing(agent="auto")
        assert decision.workflow_preset is None
        assert decision.disabled_agents == ()


class TestApplyRoutingWithWorkflow:
    """apply_routing_to_state sets workflow fields on ConversationState."""

    def test_sets_workflow_fields(self):
        from src.graph.state import ConversationState

        state = ConversationState()
        decision = resolve_agent_routing(
            agent="architect",
            workflow_preset="dashboard",
            disabled_agents=["energy_analyst", "behavioral_analyst"],
        )
        apply_routing_to_state(state, decision)

        assert state.workflow_preset == "dashboard"
        assert state.disabled_agents == ["energy_analyst", "behavioral_analyst"]

    def test_clears_when_no_preset(self):
        from src.graph.state import ConversationState

        state = ConversationState(
            workflow_preset="old-preset",
            disabled_agents=["some_agent"],
        )
        decision = resolve_agent_routing(agent="auto")
        apply_routing_to_state(state, decision)

        assert state.workflow_preset is None
        assert state.disabled_agents == []
