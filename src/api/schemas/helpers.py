"""Helper entity API schemas.

Schemas for creating, listing, and deleting HA helper entities.
"""

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class HelperType(StrEnum):
    """Supported helper types."""

    INPUT_BOOLEAN = "input_boolean"
    INPUT_NUMBER = "input_number"
    INPUT_TEXT = "input_text"
    INPUT_SELECT = "input_select"
    INPUT_DATETIME = "input_datetime"
    INPUT_BUTTON = "input_button"
    COUNTER = "counter"
    TIMER = "timer"


# ─── Request Schemas ──────────────────────────────────────────────────────────


class HelperCreateRequest(BaseModel):
    """Request to create a helper entity."""

    helper_type: HelperType = Field(..., description="Type of helper to create")
    input_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique ID (lowercase, underscores, no spaces)",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Display name",
    )
    icon: str | None = Field(None, description="MDI icon (e.g. mdi:toggle-switch)")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific configuration",
    )

    @field_validator("input_id")
    @classmethod
    def validate_input_id(cls, v: str) -> str:
        """Validate input_id is a safe identifier."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            msg = (
                "input_id must start with a lowercase letter and contain "
                "only lowercase letters, digits, and underscores"
            )
            raise ValueError(msg)
        return v

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, v: str | None) -> str | None:
        """Validate icon follows MDI format."""
        if v is not None and not v.startswith("mdi:"):
            msg = "icon must start with 'mdi:'"
            raise ValueError(msg)
        return v


# ─── Response Schemas ─────────────────────────────────────────────────────────


class HelperResponse(BaseModel):
    """A helper entity from Home Assistant."""

    entity_id: str = Field(..., description="Full entity ID (e.g. input_boolean.vacation)")
    domain: str = Field(..., description="Helper domain")
    name: str = Field(..., description="Display name")
    state: str = Field(..., description="Current state")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Entity attributes")


class HelperListResponse(BaseModel):
    """Response for helper list."""

    helpers: list[HelperResponse]
    total: int = Field(..., description="Total number of helpers")
    by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count per helper domain",
    )


class HelperCreateResponse(BaseModel):
    """Response from helper creation."""

    success: bool
    entity_id: str | None = None
    input_id: str
    helper_type: str
    error: str | None = None


class HelperDeleteResponse(BaseModel):
    """Response from helper deletion."""

    success: bool
    entity_id: str
    error: str | None = None
