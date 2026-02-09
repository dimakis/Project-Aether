"""Tests for DashboardState model.

Validates the dashboard-specific state used by the Dashboard Designer agent,
including YAML storage, preview mode, and target dashboard tracking.
"""


class TestDashboardState:
    """DashboardState model tests."""

    def test_default_values(self):
        """DashboardState initialises with sensible defaults."""
        from src.graph.state import DashboardState

        state = DashboardState()
        assert state.dashboard_yaml is None
        assert state.target_dashboard_id is None
        assert state.preview_mode is True
        assert state.dashboard_title is None
        assert state.consulted_specialists == []

    def test_with_yaml_content(self):
        """Can store a Lovelace YAML dashboard config."""
        from src.graph.state import DashboardState

        yaml_content = """
views:
  - title: Energy
    cards:
      - type: gauge
        entity: sensor.power
"""
        state = DashboardState(dashboard_yaml=yaml_content)
        assert state.dashboard_yaml == yaml_content

    def test_target_dashboard_id(self):
        """Can target an existing HA dashboard for update."""
        from src.graph.state import DashboardState

        state = DashboardState(target_dashboard_id="lovelace-energy")
        assert state.target_dashboard_id == "lovelace-energy"

    def test_preview_mode_default_true(self):
        """Preview mode defaults to True (safe by default)."""
        from src.graph.state import DashboardState

        state = DashboardState()
        assert state.preview_mode is True

    def test_preview_mode_can_be_disabled(self):
        """Preview mode can be disabled for direct deployment."""
        from src.graph.state import DashboardState

        state = DashboardState(preview_mode=False)
        assert state.preview_mode is False

    def test_consulted_specialists_tracking(self):
        """Tracks which DS team specialists were consulted."""
        from src.graph.state import DashboardState

        state = DashboardState(consulted_specialists=["energy_analyst", "behavioral_analyst"])
        assert len(state.consulted_specialists) == 2
        assert "energy_analyst" in state.consulted_specialists

    def test_inherits_conversation_state(self):
        """DashboardState extends ConversationState with all its fields."""
        from src.graph.state import ConversationState, DashboardState

        state = DashboardState(user_intent="design energy dashboard")
        # Should have ConversationState fields
        assert state.user_intent == "design energy dashboard"
        assert state.conversation_id  # Auto-generated UUID
        assert isinstance(state, ConversationState)

    def test_dashboard_title(self):
        """Can set a title for the generated dashboard."""
        from src.graph.state import DashboardState

        state = DashboardState(dashboard_title="Energy Overview")
        assert state.dashboard_title == "Energy Overview"

    def test_exported_in_all(self):
        """DashboardState is listed in module __all__."""
        from src.graph import state

        assert "DashboardState" in state.__all__
