"""Shared types for Home Assistant YAML schemas.

Common constrained types, enums, and base models used across
HA automation, script, scene, and dashboard schemas.

Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

# =============================================================================
# ENUMS
# =============================================================================


class Mode(str, Enum):
    """Home Assistant automation/script execution mode.

    Controls how HA handles new triggers while a previous run is active.
    """

    SINGLE = "single"
    RESTART = "restart"
    QUEUED = "queued"
    PARALLEL = "parallel"


# =============================================================================
# CONSTRAINED TYPES
# =============================================================================


# Entity IDs: domain.object_id, lowercase with underscores/digits.
EntityId = Annotated[
    str,
    Field(
        pattern=r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$",
        description="Home Assistant entity ID (e.g., 'light.living_room')",
    ),
]

# Service names: domain.service, same format as entity IDs.
ServiceName = Annotated[
    str,
    Field(
        pattern=r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$",
        description="Home Assistant service name (e.g., 'light.turn_on')",
    ),
]


# =============================================================================
# COMMON MODELS
# =============================================================================


class ServiceTarget(BaseModel):
    """Target specification for HA service calls.

    At least one of entity_id, device_id, or area_id is typically
    provided, but all are optional to match HA's flexible targeting.
    """

    entity_id: str | list[str] | None = Field(
        default=None,
        description="Entity ID(s) to target",
    )
    device_id: str | list[str] | None = Field(
        default=None,
        description="Device ID(s) to target",
    )
    area_id: str | list[str] | None = Field(
        default=None,
        description="Area ID(s) to target",
    )
    floor_id: str | list[str] | None = Field(
        default=None,
        description="Floor ID(s) to target",
    )
    label_id: str | list[str] | None = Field(
        default=None,
        description="Label ID(s) to target",
    )

    model_config = {"extra": "allow"}


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "EntityId",
    "Mode",
    "ServiceName",
    "ServiceTarget",
]
