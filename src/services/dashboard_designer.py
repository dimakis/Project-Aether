"""Dashboard Designer A2A service entrypoint (Phase 5).

Wraps the DashboardDesignerAgent for Lovelace dashboard generation.

Entrypoint: ``uvicorn src.services.dashboard_designer:app``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.a2a_service import create_a2a_service

if TYPE_CHECKING:
    from starlette.applications import Starlette

_SKILLS = [
    {
        "id": "dashboard_design",
        "name": "Dashboard Design",
        "description": "Design Lovelace dashboards from natural language descriptions",
    },
    {
        "id": "dashboard_deployment",
        "name": "Dashboard Deployment",
        "description": "Deploy dashboard YAML to Home Assistant with HITL approval",
    },
]


def create_dashboard_designer_service() -> Starlette:
    from src.agents.dashboard_designer import DashboardDesignerAgent

    return create_a2a_service(
        agent_name="dashboard-designer",
        agent_description="Lovelace dashboard design, generation, and deployment",
        agent_skills=_SKILLS,
        agent=DashboardDesignerAgent(),
    )


app = create_dashboard_designer_service()
