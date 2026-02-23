"""Orchestrator A2A service entrypoint (Phase 5).

Wraps the OrchestratorAgent for intent classification and routing.

Entrypoint: ``uvicorn src.services.orchestrator:app``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.a2a_service import create_a2a_service

if TYPE_CHECKING:
    from starlette.applications import Starlette

_SKILLS = [
    {
        "id": "intent_classification",
        "name": "Intent Classification",
        "description": "Classify user intent and determine which domain agent should handle the request",
    },
    {
        "id": "agent_routing",
        "name": "Agent Routing",
        "description": "Route messages to the appropriate agent based on intent confidence scores",
    },
]


def create_orchestrator_service() -> Starlette:
    """Create the Orchestrator A2A service."""
    from src.agents.orchestrator import OrchestratorAgent

    return create_a2a_service(
        agent_name="orchestrator",
        agent_description="Intent classification and multi-agent routing",
        agent_skills=_SKILLS,
        agent=OrchestratorAgent(),
    )


app = create_orchestrator_service()
