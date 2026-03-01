"""Librarian A2A service entrypoint (Phase 5).

Wraps the LibrarianAgent for HA entity discovery and sync.

Entrypoint: ``uvicorn src.services.librarian:app``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.a2a_service import create_a2a_service

if TYPE_CHECKING:
    from starlette.applications import Starlette

_SKILLS = [
    {
        "id": "entity_discovery",
        "name": "Entity Discovery",
        "description": "Discover and catalog Home Assistant entities, devices, and areas",
    },
    {
        "id": "entity_sync",
        "name": "Entity Sync",
        "description": "Synchronize entity state from Home Assistant to the local database",
    },
]


def create_librarian_service() -> Starlette:
    from src.agents.librarian import LibrarianAgent

    return create_a2a_service(
        agent_name="librarian",
        agent_description="Home Assistant entity discovery, cataloging, and synchronization",
        agent_skills=_SKILLS,
        agent=LibrarianAgent(),
    )


app = create_librarian_service()
