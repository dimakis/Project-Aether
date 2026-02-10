"""Home Assistant scene YAML schema.

Defines Pydantic models for HA scene configurations.

Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HAScene(BaseModel):
    """Home Assistant scene configuration.

    Scenes define a set of entity states that can be activated
    together.
    """

    name: str = Field(..., description="Scene display name")
    id: str | None = Field(default=None, description="Scene ID")
    icon: str | None = None
    entities: dict[str, Any] = Field(
        ..., description="Entity states map (entity_id -> state or state dict)"
    )

    model_config = {"extra": "allow"}


__all__ = ["HAScene"]
