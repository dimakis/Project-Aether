"""Home Assistant automation YAML schema.

Defines Pydantic models for HA automation configs including
trigger, action, and condition types.

HA automations use a flexible structure where triggers, actions,
and conditions can be single dicts or lists. Trigger types are
discriminated by the 'platform' field, conditions by 'condition'.

Both old-style (pre-2024.1) syntax and new-style (2024.1+) syntax
are supported after normalization in core.validate_yaml().

Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schema.ha.common import Mode

# =============================================================================
# TRIGGERS
# =============================================================================


class _TriggerBase(BaseModel):
    """Base for all trigger types. Extra fields allowed for forward compat."""

    id: str | None = None
    enabled: bool | None = None
    variables: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class StateTrigger(_TriggerBase):
    """State change trigger."""

    platform: Literal["state"]
    entity_id: str | list[str] = Field(..., description="Entity to watch")
    to: str | list[str] | None = None
    from_: str | list[str] | None = Field(default=None, alias="from")
    for_: str | dict[str, Any] | None = Field(default=None, alias="for")
    attribute: str | None = None
    not_to: str | list[str] | None = None
    not_from: str | list[str] | None = None


class TimeTrigger(_TriggerBase):
    """Time trigger."""

    platform: Literal["time"]
    at: str | dict[str, Any] | list[str | dict[str, Any]] = Field(
        ...,
        description=("Time(s) in HH:MM:SS, input_datetime entity, or dict with entity_id + offset"),
    )
    weekday: str | list[str] | None = None


class SunTrigger(_TriggerBase):
    """Sun event trigger."""

    platform: Literal["sun"]
    event: str = Field(..., description="'sunrise' or 'sunset'")
    offset: str | None = None


class NumericStateTrigger(_TriggerBase):
    """Numeric state trigger."""

    platform: Literal["numeric_state"]
    entity_id: str | list[str] = Field(..., description="Entity to watch")
    above: float | int | str | None = None
    below: float | int | str | None = None
    attribute: str | None = None
    value_template: str | None = None
    for_: str | dict[str, Any] | None = Field(default=None, alias="for")


class EventTrigger(_TriggerBase):
    """Event trigger."""

    platform: Literal["event"]
    event_type: str | list[str] = Field(..., description="Event type(s)")
    event_data: dict[str, Any] | None = None
    context: dict[str, Any] | None = None


class TemplateTrigger(_TriggerBase):
    """Template trigger."""

    platform: Literal["template"]
    value_template: str = Field(..., description="Jinja2 template")
    for_: str | dict[str, Any] | None = Field(default=None, alias="for")


class WebhookTrigger(_TriggerBase):
    """Webhook trigger."""

    platform: Literal["webhook"]
    webhook_id: str = Field(..., description="Unique webhook ID")
    allowed_methods: list[str] | None = None
    local_only: bool | None = None


class MqttTrigger(_TriggerBase):
    """MQTT message trigger."""

    platform: Literal["mqtt"]
    topic: str = Field(..., description="MQTT topic")
    payload: str | None = None
    qos: int | None = None
    encoding: str | None = None
    value_template: str | None = None


class DeviceTrigger(_TriggerBase):
    """Device trigger (device automation)."""

    platform: Literal["device"]
    device_id: str = Field(..., description="Device ID")
    domain: str = Field(..., description="Integration domain")
    type: str = Field(..., description="Trigger type")
    subtype: str | None = None
    entity_id: str | None = None


class ZoneTrigger(_TriggerBase):
    """Zone trigger."""

    platform: Literal["zone"]
    entity_id: str = Field(..., description="Person/device tracker entity")
    zone: str = Field(..., description="Zone entity ID")
    event: str = Field(..., description="'enter' or 'leave'")


class TagTrigger(_TriggerBase):
    """NFC tag trigger."""

    platform: Literal["tag"]
    tag_id: str = Field(..., description="Tag ID")
    device_id: str | list[str] | None = None


class CalendarTrigger(_TriggerBase):
    """Calendar trigger."""

    platform: Literal["calendar"]
    entity_id: str = Field(..., description="Calendar entity")
    event: str = Field(..., description="'start' or 'end'")
    offset: str | None = None


class HomeassistantTrigger(_TriggerBase):
    """Home Assistant start/stop trigger."""

    platform: Literal["homeassistant"]
    event: str = Field(..., description="'start' or 'shutdown'")


class TimePatternTrigger(_TriggerBase):
    """Time pattern trigger (cron-like)."""

    platform: Literal["time_pattern"]
    hours: str | int | None = None
    minutes: str | int | None = None
    seconds: str | int | None = None


class PersistentNotificationTrigger(_TriggerBase):
    """Persistent notification trigger."""

    platform: Literal["persistent_notification"]
    notification_id: str | None = None
    update_type: str | list[str] | None = None


class GeoLocationTrigger(_TriggerBase):
    """Geolocation trigger."""

    platform: Literal["geo_location"]
    source: str = Field(..., description="Geolocation source")
    zone: str = Field(..., description="Zone entity ID")
    event: str = Field(..., description="'enter' or 'leave'")


class ConversationTrigger(_TriggerBase):
    """Conversation/sentence trigger (HA 2023.8+)."""

    platform: Literal["conversation"]
    command: str | list[str] = Field(..., description="Sentence(s) to match")


class GenericTrigger(_TriggerBase):
    """Fallback for unrecognized trigger platforms.

    Accepts any platform string not covered by the specific models.
    Ensures forward compatibility with new HA trigger types.
    """

    platform: str = Field(..., description="Trigger platform")


# Union of all trigger types. We don't use discriminated union here
# because HA YAML may use 'trigger' key (HA 2024.1+) instead of 'platform'.
Trigger = (
    StateTrigger
    | TimeTrigger
    | SunTrigger
    | NumericStateTrigger
    | EventTrigger
    | TemplateTrigger
    | WebhookTrigger
    | MqttTrigger
    | DeviceTrigger
    | ZoneTrigger
    | TagTrigger
    | CalendarTrigger
    | HomeassistantTrigger
    | TimePatternTrigger
    | PersistentNotificationTrigger
    | GeoLocationTrigger
    | ConversationTrigger
    | GenericTrigger
)


# =============================================================================
# ACTIONS
# =============================================================================


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


# =============================================================================
# CONDITIONS
# =============================================================================


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


# =============================================================================
# TOP-LEVEL AUTOMATION
# =============================================================================


class HAAutomation(BaseModel):
    """Home Assistant automation configuration.

    Matches the structure expected in HA's automations.yaml.
    Triggers, actions, and conditions accept either a single
    dict or a list of dicts for convenience. Both the old-style
    singular keys (trigger/condition/action) and the 2024.1+
    plural keys (triggers/conditions/actions) are accepted after
    normalization in core.validate_yaml().
    """

    alias: str | None = Field(default=None, description="Automation display name")
    id: str | None = Field(default=None, description="Optional automation ID")
    description: str | None = None
    trigger: list[dict[str, Any]] | dict[str, Any] = Field(
        ..., description="Trigger configuration(s)"
    )
    action: list[dict[str, Any]] | dict[str, Any] = Field(
        ..., description="Action configuration(s)"
    )
    condition: list[dict[str, Any]] | dict[str, Any] | None = Field(
        default=None, description="Condition configuration(s)"
    )
    mode: Mode = Field(default=Mode.SINGLE, description="Execution mode")
    max: int | None = Field(default=None, description="Max parallel runs (queued/parallel mode)")
    max_exceeded: str | None = Field(
        default=None, description="Behaviour when max exceeded (silent/warning/error)"
    )
    variables: dict[str, Any] | None = Field(
        default=None, description="Variables available in the automation"
    )
    trigger_variables: dict[str, Any] | None = Field(
        default=None, description="Variables available in trigger templates"
    )
    initial_state: bool | None = Field(
        default=None, description="Automation state at startup (default: restored from last run)"
    )
    trace: dict[str, Any] | None = Field(default=None, description="Trace configuration")

    model_config = {"extra": "allow"}


# =============================================================================
# MODEL MAPS (used by content validation in core.py)
# =============================================================================

TRIGGER_MODEL_MAP: dict[str, type[_TriggerBase]] = {
    "state": StateTrigger,
    "time": TimeTrigger,
    "sun": SunTrigger,
    "numeric_state": NumericStateTrigger,
    "event": EventTrigger,
    "template": TemplateTrigger,
    "webhook": WebhookTrigger,
    "mqtt": MqttTrigger,
    "device": DeviceTrigger,
    "zone": ZoneTrigger,
    "tag": TagTrigger,
    "calendar": CalendarTrigger,
    "homeassistant": HomeassistantTrigger,
    "time_pattern": TimePatternTrigger,
    "persistent_notification": PersistentNotificationTrigger,
    "geo_location": GeoLocationTrigger,
    "conversation": ConversationTrigger,
}

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


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ACTION_KEY_MAP",
    "CONDITION_MODEL_MAP",
    "TRIGGER_MODEL_MAP",
    "Action",
    "AndCondition",
    "CalendarTrigger",
    "ChooseAction",
    "Condition",
    "ConditionAction",
    "ConversationTrigger",
    "DelayAction",
    "DeviceCondition",
    "DeviceTrigger",
    "EventAction",
    "EventTrigger",
    "GenericAction",
    "GenericCondition",
    "GenericTrigger",
    "GeoLocationTrigger",
    "HAAutomation",
    "HomeassistantTrigger",
    "IfAction",
    "MqttTrigger",
    "NotCondition",
    "NumericStateCondition",
    "NumericStateTrigger",
    "OrCondition",
    "ParallelAction",
    "PersistentNotificationTrigger",
    "RepeatAction",
    "ServiceAction",
    "StateCondition",
    "StateTrigger",
    "StopAction",
    "SunCondition",
    "SunTrigger",
    "TagTrigger",
    "TemplateCondition",
    "TemplateTrigger",
    "TimeCondition",
    "TimePatternTrigger",
    "TimeTrigger",
    "Trigger",
    "TriggerCondition",
    "VariablesAction",
    "WaitForTriggerAction",
    "WaitTemplateAction",
    "WebhookTrigger",
    "ZoneCondition",
    "ZoneTrigger",
]
