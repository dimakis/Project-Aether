"""Home Assistant action models for automation YAML schema.

All action types for automation sequences.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class _ActionBase(BaseModel):
    """Base for all action types. Extra fields allowed for forward compat."""

    alias: str | None = None
    enabled: bool | None = None

    model_config = {"extra": "allow"}


class ServiceAction(_ActionBase):
    """Service call action."""

    service: str = Field(..., description="Service to call (domain.service)")
    target: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    response_variable: str | None = None


class DelayAction(_ActionBase):
    """Delay action."""

    delay: str | dict[str, Any] = Field(..., description="Delay duration")


class WaitTemplateAction(_ActionBase):
    """Wait for template action."""

    wait_template: str = Field(..., description="Jinja2 template to wait for")
    timeout: str | dict[str, Any] | None = None
    continue_on_timeout: bool | None = None


class EventAction(_ActionBase):
    """Fire event action."""

    event: str = Field(..., description="Event type to fire")
    event_data: dict[str, Any] | None = None
    event_data_template: dict[str, Any] | None = None


class ConditionAction(_ActionBase):
    """Condition check as an action (stops execution if false)."""

    condition: str = Field(..., description="Condition type")
    # Remaining fields vary by condition type
    entity_id: str | None = None
    state: str | None = None
    value_template: str | None = None


class RepeatAction(_ActionBase):
    """Repeat action."""

    repeat: dict[str, Any] = Field(..., description="Repeat configuration")


class ChooseAction(_ActionBase):
    """Choose (if/elif/else) action."""

    choose: list[dict[str, Any]] = Field(..., description="Choice branches")
    default: list[dict[str, Any]] | None = None


class IfAction(_ActionBase):
    """If/then/else action (HA 2023.1+)."""

    if_: list[dict[str, Any]] = Field(..., alias="if", description="Conditions")
    then: list[dict[str, Any]] = Field(..., description="Actions if true")
    else_: list[dict[str, Any]] | None = Field(default=None, alias="else")


class StopAction(_ActionBase):
    """Stop action."""

    stop: str = Field(..., description="Reason for stopping")
    error: bool | None = None
    response_variable: str | None = None


class ParallelAction(_ActionBase):
    """Parallel action (run multiple sequences simultaneously)."""

    parallel: list[dict[str, Any]] = Field(..., description="Parallel action sequences")


class VariablesAction(_ActionBase):
    """Set variables action."""

    variables: dict[str, Any] = Field(..., description="Variables to set")


class WaitForTriggerAction(_ActionBase):
    """Wait for trigger action."""

    wait_for_trigger: list[dict[str, Any]] = Field(..., description="Trigger(s) to wait for")
    timeout: str | dict[str, Any] | None = None
    continue_on_timeout: bool | None = None


class GenericAction(_ActionBase):
    """Fallback for unrecognized action types.

    Accepts any dict structure for forward compatibility.
    """

    pass


# Union of action types
Action = (
    ServiceAction
    | DelayAction
    | WaitTemplateAction
    | EventAction
    | ConditionAction
    | RepeatAction
    | ChooseAction
    | IfAction
    | StopAction
    | ParallelAction
    | VariablesAction
    | WaitForTriggerAction
    | GenericAction
)


ACTION_KEY_MAP: dict[str, type[_ActionBase]] = {
    "service": ServiceAction,
    "delay": DelayAction,
    "wait_template": WaitTemplateAction,
    "event": EventAction,
    "condition": ConditionAction,
    "repeat": RepeatAction,
    "choose": ChooseAction,
    "if": IfAction,
    "stop": StopAction,
    "parallel": ParallelAction,
    "variables": VariablesAction,
    "wait_for_trigger": WaitForTriggerAction,
}
