"""Dashboard state for Dashboard Designer agent."""

from pydantic import Field

from .conversation import ConversationState


class DashboardState(ConversationState):
    """State for the Dashboard Designer agent.

    Extends ConversationState with dashboard-specific fields for
    Lovelace YAML generation, preview, and deployment.
    """

    # Generated dashboard configuration (Lovelace YAML)
    dashboard_yaml: str | None = None
    dashboard_title: str | None = None

    # Target HA dashboard (None = new dashboard)
    target_dashboard_id: str | None = None

    # Preview mode: True means show in UI before deploying to HA
    preview_mode: bool = True

    # Track which DS team specialists were consulted
    consulted_specialists: list[str] = Field(default_factory=list)
