"""Home Assistant condition models for automation YAML schema.

All condition types discriminated by 'condition' field.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class _ConditionBase(BaseModel):
    """Base for all condition types."""

    alias: str | None = None
    enabled: bool | None = None

    model_config = {"extra": "allow"}


class StateCondition(_ConditionBase):
    """State condition."""

    condition: Literal["state"]
    entity_id: str | list[str] = Field(..., description="Entity to check")
    state: str | list[str] = Field(..., description="Expected state(s)")
    attribute: str | None = None
    for_: str | dict[str, Any] | None = Field(default=None, alias="for")


class TimeCondition(_ConditionBase):
    """Time condition."""

    condition: Literal["time"]
    after: str | None = None
    before: str | None = None
    weekday: list[str] | None = None


class SunCondition(_ConditionBase):
    """Sun condition."""

    condition: Literal["sun"]
    after: str | None = None
    before: str | None = None
    after_offset: str | None = None
    before_offset: str | None = None


class NumericStateCondition(_ConditionBase):
    """Numeric state condition."""

    condition: Literal["numeric_state"]
    entity_id: str | list[str] = Field(..., description="Entity to check")
    above: float | int | str | None = None
    below: float | int | str | None = None
    attribute: str | None = None
    value_template: str | None = None


class TemplateCondition(_ConditionBase):
    """Template condition."""

    condition: Literal["template"]
    value_template: str = Field(..., description="Jinja2 template")


class ZoneCondition(_ConditionBase):
    """Zone condition."""

    condition: Literal["zone"]
    entity_id: str = Field(..., description="Person/device tracker entity")
    zone: str = Field(..., description="Zone entity ID")


class TriggerCondition(_ConditionBase):
    """Trigger ID condition."""

    condition: Literal["trigger"]
    id: str | list[str] = Field(..., description="Trigger ID(s) to match")


class DeviceCondition(_ConditionBase):
    """Device condition."""

    condition: Literal["device"]
    device_id: str = Field(..., description="Device ID")
    domain: str = Field(..., description="Integration domain")
    type: str = Field(..., description="Condition type")
    entity_id: str | None = None


class AndCondition(_ConditionBase):
    """Logical AND condition."""

    condition: Literal["and"]
    conditions: list[dict[str, Any]] = Field(..., description="Sub-conditions (all must be true)")


class OrCondition(_ConditionBase):
    """Logical OR condition."""

    condition: Literal["or"]
    conditions: list[dict[str, Any]] = Field(..., description="Sub-conditions (any must be true)")


class NotCondition(_ConditionBase):
    """Logical NOT condition."""

    condition: Literal["not"]
    conditions: list[dict[str, Any]] = Field(..., description="Sub-conditions (all must be false)")


class GenericCondition(_ConditionBase):
    """Fallback for unrecognized condition types."""

    condition: str = Field(..., description="Condition type")


Condition = (
    StateCondition
    | TimeCondition
    | SunCondition
    | NumericStateCondition
    | TemplateCondition
    | ZoneCondition
    | TriggerCondition
    | DeviceCondition
    | AndCondition
    | OrCondition
    | NotCondition
    | GenericCondition
)


CONDITION_MODEL_MAP: dict[str, type[_ConditionBase]] = {
    "state": StateCondition,
    "time": TimeCondition,
    "sun": SunCondition,
    "numeric_state": NumericStateCondition,
    "template": TemplateCondition,
    "zone": ZoneCondition,
    "trigger": TriggerCondition,
    "device": DeviceCondition,
    "and": AndCondition,
    "or": OrCondition,
    "not": NotCondition,
}
