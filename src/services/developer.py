"""Developer A2A service entrypoint (Phase 5).

Wraps the DeveloperAgent for automation deployment and rollback.

Entrypoint: ``uvicorn src.services.developer:app``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.a2a_service import create_a2a_service

if TYPE_CHECKING:
    from starlette.applications import Starlette

_SKILLS = [
    {
        "id": "automation_deployment",
        "name": "Automation Deployment",
        "description": "Deploy approved automations to Home Assistant via HA REST API",
    },
    {
        "id": "rollback",
        "name": "Rollback",
        "description": "Rollback deployed automations and dashboard changes",
    },
    {
        "id": "yaml_generation",
        "name": "YAML Generation",
        "description": "Generate Home Assistant automation YAML from proposals",
    },
]


def create_developer_service() -> Starlette:
    from src.agents.developer import DeveloperAgent

    return create_a2a_service(
        agent_name="developer",
        agent_description="Automation deployment, rollback, and YAML generation",
        agent_skills=_SKILLS,
        agent=DeveloperAgent(),
    )


app = create_developer_service()
