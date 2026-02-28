"""Architect A2A service entrypoint (Phase 4).

Wraps the ArchitectAgent as a single-agent A2A service.
The primary conversational agent that handles user intent,
generates proposals, and delegates to the DS team.

Entrypoint: ``uvicorn src.services.architect:app``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.a2a_service import create_a2a_service

if TYPE_CHECKING:
    from starlette.applications import Starlette

_SKILLS = [
    {
        "id": "automation_design",
        "name": "Automation Design",
        "description": "Design Home Assistant automations from natural language requests",
    },
    {
        "id": "entity_queries",
        "name": "Entity Queries",
        "description": "Query and control Home Assistant entities, devices, and areas",
    },
    {
        "id": "proposal_management",
        "name": "Proposal Management",
        "description": "Create, review, and deploy automation proposals with HITL approval",
    },
]


def create_architect_service() -> Starlette:
    from src.agents.architect import ArchitectAgent

    agent = ArchitectAgent()

    return create_a2a_service(
        agent_name="architect",
        agent_description="Primary conversational agent for home automation design and control",
        agent_skills=_SKILLS,
        agent=agent,
    )


app = create_architect_service()
