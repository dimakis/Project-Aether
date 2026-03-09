"""Home Assistant helper proposal schema.

Validates the service_call payload stored in helper proposals before
it reaches HA. Uses a discriminated union on ``helper_type`` to apply
type-specific field requirements.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, Field, RootModel, Tag


class _HelperBase(BaseModel):
    """Shared fields for all helper types."""

    input_id: str = Field(..., min_length=1, description="Helper object ID")
    name: str = Field(..., min_length=1, description="Display name")

    model_config = {"extra": "allow"}


class InputNumberHelper(_HelperBase):
    """input_number helper: numeric slider/box."""

    helper_type: Literal["input_number"] = "input_number"
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    step: float = Field(..., description="Step increment")
    unit_of_measurement: str | None = Field(default=None, description="Unit label")


class InputTextHelper(_HelperBase):
    """input_text helper: text input field."""

    helper_type: Literal["input_text"] = "input_text"
    min_length: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=0)
    pattern: str | None = Field(default=None, description="Regex pattern")


class InputSelectHelper(_HelperBase):
    """input_select helper: dropdown selector."""

    helper_type: Literal["input_select"] = "input_select"
    options: list[str] = Field(..., min_length=1, description="Option values")


class InputBooleanHelper(_HelperBase):
    """input_boolean helper: on/off toggle."""

    helper_type: Literal["input_boolean"] = "input_boolean"


class InputDatetimeHelper(_HelperBase):
    """input_datetime helper: date/time picker."""

    helper_type: Literal["input_datetime"] = "input_datetime"
    has_date: bool = Field(default=True, description="Include date component")
    has_time: bool = Field(default=True, description="Include time component")


class InputButtonHelper(_HelperBase):
    """input_button helper: pressable button."""

    helper_type: Literal["input_button"] = "input_button"


class CounterHelper(_HelperBase):
    """counter helper: incrementable counter."""

    helper_type: Literal["counter"] = "counter"
    initial: int | None = Field(default=None, description="Initial value")
    step: int | None = Field(default=None, ge=1, description="Step increment")
    minimum: int | None = Field(default=None, description="Minimum value")
    maximum: int | None = Field(default=None, description="Maximum value")


class TimerHelper(_HelperBase):
    """timer helper: countdown timer."""

    helper_type: Literal["timer"] = "timer"
    duration: str | None = Field(default=None, description="Duration (HH:MM:SS)")


HelperPayload = Annotated[
    Annotated[InputNumberHelper, Tag("input_number")]
    | Annotated[InputTextHelper, Tag("input_text")]
    | Annotated[InputSelectHelper, Tag("input_select")]
    | Annotated[InputBooleanHelper, Tag("input_boolean")]
    | Annotated[InputDatetimeHelper, Tag("input_datetime")]
    | Annotated[InputButtonHelper, Tag("input_button")]
    | Annotated[CounterHelper, Tag("counter")]
    | Annotated[TimerHelper, Tag("timer")],
    Discriminator("helper_type"),
]
"""Discriminated union of all HA helper types."""


class HAHelper(RootModel[HelperPayload]):
    """Root model wrapping HelperPayload for SchemaRegistry compatibility.

    SchemaRegistry requires a ``BaseModel`` subclass with
    ``model_json_schema()``; ``RootModel`` provides that for
    the discriminated union type alias.
    """


__all__ = [
    "CounterHelper",
    "HAHelper",
    "HelperPayload",
    "InputBooleanHelper",
    "InputButtonHelper",
    "InputDatetimeHelper",
    "InputNumberHelper",
    "InputSelectHelper",
    "InputTextHelper",
    "TimerHelper",
]
