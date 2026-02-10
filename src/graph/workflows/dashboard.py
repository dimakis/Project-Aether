"""Dashboard workflow - conversational dashboard designer.

Simple conversational loop: user ↔ dashboard_designer agent.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph


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
