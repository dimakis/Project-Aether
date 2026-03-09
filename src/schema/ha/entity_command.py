"""Home Assistant entity_command proposal schema.

Validates the service_call payload stored in entity_command proposals
before it reaches HA. Catches malformed entity IDs, missing required
fields, and invalid entity_updates structures.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

_ENTITY_ID_PATTERN = r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$"


class EntityUpdate(BaseModel):
    """A single entity update within a batch entity_command.

    Used inside ``data.entity_updates`` when a single proposal
    updates multiple entities (e.g. tariff rate changes).
    """

    entity_id: Annotated[
        str,
        Field(pattern=_ENTITY_ID_PATTERN, description="Target entity ID"),
    ]
    value: str | int | float = Field(..., description="Value to set")


class EntityCommandData(BaseModel):
    """Optional nested data for entity_command payloads.

    Allows arbitrary metadata keys alongside the structured
    ``entity_updates`` list.
    """

    entity_updates: list[EntityUpdate] | None = Field(
        default=None,
        description="Batch entity updates",
    )

    model_config = {"extra": "allow"}


class EntityCommandPayload(BaseModel):
    """Top-level schema for entity_command proposal service_call.

    Validates the shape our system stores in the DB — not the
    raw HA service call format.
    """

    domain: str = Field(..., min_length=1, description="HA service domain")
    service: str = Field(..., min_length=1, description="HA service action")
    entity_id: Annotated[
        str | None,
        Field(
            default=None,
            pattern=_ENTITY_ID_PATTERN,
            description="Primary target entity ID",
        ),
    ] = None
    data: EntityCommandData | None = Field(
        default=None,
        description="Service call data payload",
    )

    model_config = {"extra": "allow"}


__all__ = [
    "EntityCommandData",
    "EntityCommandPayload",
    "EntityUpdate",
]
