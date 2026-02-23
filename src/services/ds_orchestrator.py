"""DS Orchestrator A2A service entrypoint (Phase 4).

Wraps the DataScientistAgent as a single-agent A2A service.
Coordinates the DS Analysts container and synthesizes findings.

When DEPLOYMENT_MODE=distributed, delegates to the analysts
container via A2ARemoteClient. Otherwise, runs analysts in-process.

Entrypoint: ``uvicorn src.services.ds_orchestrator:app``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.a2a_service import create_a2a_service

if TYPE_CHECKING:
    from starlette.applications import Starlette

_SKILLS = [
    {
        "id": "team_analysis",
        "name": "Team Analysis",
        "description": "Coordinate energy, behavioral, and diagnostic analysts for comprehensive home analysis",
    },
    {
        "id": "synthesis",
        "name": "Synthesis",
        "description": "Synthesize findings from multiple analysts into actionable recommendations",
    },
]


def create_ds_orchestrator_service() -> Starlette:
    """Create the DS Orchestrator A2A service."""
    from src.agents.data_scientist import DataScientistAgent

    agent = DataScientistAgent()

    return create_a2a_service(
        agent_name="ds-orchestrator",
        agent_description="Data Science team coordinator — manages analysts and synthesizes findings",
        agent_skills=_SKILLS,
        agent=agent,
    )


app = create_ds_orchestrator_service()
