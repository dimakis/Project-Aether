"""Home Assistant script YAML schema.

Defines Pydantic models for HA script configurations.

Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.schema.ha.common import Mode


class HAScript(BaseModel):
    """Home Assistant script configuration.

    Scripts have a sequence of actions, optional input fields,
    and an execution mode.
    """

    alias: str = Field(..., description="Script display name")
    description: str | None = None
    icon: str | None = None
    sequence: list[dict[str, Any]] = Field(..., description="Action sequence")
    mode: Mode = Field(default=Mode.SINGLE, description="Execution mode")
    max: int | None = Field(default=None, description="Max parallel runs")
    max_exceeded: str | None = None
    fields: dict[str, Any] | None = Field(default=None, description="Input field definitions")
    variables: dict[str, Any] | None = Field(default=None, description="Script variables")
    trace: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


__all__ = ["HAScript"]
