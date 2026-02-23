"""DS Analysts A2A service entrypoint (Phase 4).

Wraps the Energy, Behavioral, and Diagnostic analysts into a
single A2A-compliant service. The analysts share AnalysisState
in-process — no inter-analyst A2A communication.

Entrypoint: ``uvicorn src.services.ds_analysts:app``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.a2a_service import create_a2a_service

if TYPE_CHECKING:
    from starlette.applications import Starlette

_SKILLS = [
    {
        "id": "energy_analysis",
        "name": "Energy Analysis",
        "description": "Energy consumption analysis, cost optimization, and usage patterns",
    },
    {
        "id": "behavioral_analysis",
        "name": "Behavioral Analysis",
        "description": "User behavior patterns, routine detection, and automation suggestions",
    },
    {
        "id": "diagnostic_analysis",
        "name": "Diagnostic Analysis",
        "description": "System health monitoring, error diagnosis, and integration troubleshooting",
    },
]


def create_ds_analysts_service() -> Starlette:
    """Create the DS Analysts A2A service.

    Wraps the EnergyAnalyst as the default handler. The DS Orchestrator
    coordinates which analyst to invoke via the specialist field in the
    AnalysisState.
    """
    from src.agents.energy_analyst import EnergyAnalyst

    agent = EnergyAnalyst()

    return create_a2a_service(
        agent_name="ds-analysts",
        agent_description="Data Science analysis specialists: energy, behavioral, and diagnostic",
        agent_skills=_SKILLS,
        agent=agent,
    )


app = create_ds_analysts_service()
