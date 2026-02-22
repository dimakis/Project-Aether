"""Tests for agent seed data with routing metadata (Feature 30).

Verifies that the seed definitions include routing fields for all
agents that should be discoverable by the Orchestrator.
"""

from __future__ import annotations


class TestSeedDefinitionsHaveRoutingFields:
    """Seed agent_defs must include routing metadata."""

    def test_architect_is_routable_with_home_domain(self):
        from src.api.routes.agents.seed import AGENT_DEFS

        architect = next(d for d in AGENT_DEFS if d["name"] == "architect")
        assert architect["domain"] == "home"
        assert architect["is_routable"] is True
        assert "home_automation" in architect["intent_patterns"]
        assert "control_devices" in architect["capabilities"]

    def test_knowledge_agent_exists_and_is_routable(self):
        from src.api.routes.agents.seed import AGENT_DEFS

        knowledge = next(d for d in AGENT_DEFS if d["name"] == "knowledge")
        assert knowledge["domain"] == "knowledge"
        assert knowledge["is_routable"] is True
        assert "general_question" in knowledge["intent_patterns"]
        assert "answer_questions" in knowledge["capabilities"]

    def test_data_scientist_is_routable_with_analytics_domain(self):
        from src.api.routes.agents.seed import AGENT_DEFS

        ds = next(d for d in AGENT_DEFS if d["name"] == "data_scientist")
        assert ds["domain"] == "analytics"
        assert ds["is_routable"] is True
        assert "energy_analysis" in ds["intent_patterns"]

    def test_dashboard_designer_is_routable(self):
        from src.api.routes.agents.seed import AGENT_DEFS

        dd = next(d for d in AGENT_DEFS if d["name"] == "dashboard_designer")
        assert dd["domain"] == "dashboard"
        assert dd["is_routable"] is True

    def test_developer_is_not_routable(self):
        from src.api.routes.agents.seed import AGENT_DEFS

        dev = next(d for d in AGENT_DEFS if d["name"] == "developer")
        assert dev.get("is_routable", False) is False

    def test_orchestrator_is_not_routable(self):
        from src.api.routes.agents.seed import AGENT_DEFS

        orch = next(d for d in AGENT_DEFS if d["name"] == "orchestrator")
        assert orch.get("is_routable", False) is False

    def test_all_routable_agents_have_required_fields(self):
        from src.api.routes.agents.seed import AGENT_DEFS

        for defn in AGENT_DEFS:
            if defn.get("is_routable"):
                assert "domain" in defn, f"{defn['name']} missing domain"
                assert "intent_patterns" in defn, f"{defn['name']} missing intent_patterns"
                assert "capabilities" in defn, f"{defn['name']} missing capabilities"
                assert len(defn["intent_patterns"]) > 0, f"{defn['name']} has empty intent_patterns"
                assert len(defn["capabilities"]) > 0, f"{defn['name']} has empty capabilities"
