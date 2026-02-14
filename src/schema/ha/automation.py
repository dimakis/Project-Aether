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

from typing import Any

from pydantic import BaseModel, Field

# Re-export actions
from src.schema.ha.actions import (
    ACTION_KEY_MAP,
    Action,
    ChooseAction,
    ConditionAction,
    DelayAction,
    EventAction,
    GenericAction,
    IfAction,
    ParallelAction,
    RepeatAction,
    ServiceAction,
    StopAction,
    VariablesAction,
    WaitForTriggerAction,
    WaitTemplateAction,
)
from src.schema.ha.common import Mode

# Re-export conditions
from src.schema.ha.conditions import (
    CONDITION_MODEL_MAP,
    AndCondition,
    Condition,
    DeviceCondition,
    GenericCondition,
    NotCondition,
    NumericStateCondition,
    OrCondition,
    StateCondition,
    SunCondition,
    TemplateCondition,
    TimeCondition,
    TriggerCondition,
    ZoneCondition,
)

# Re-export triggers
from src.schema.ha.triggers import (
    TRIGGER_MODEL_MAP,
    CalendarTrigger,
    ConversationTrigger,
    DeviceTrigger,
    EventTrigger,
    GenericTrigger,
    GeoLocationTrigger,
    HomeassistantTrigger,
    MqttTrigger,
    NumericStateTrigger,
    PersistentNotificationTrigger,
    StateTrigger,
    SunTrigger,
    TagTrigger,
    TemplateTrigger,
    TimePatternTrigger,
    TimeTrigger,
    Trigger,
    WebhookTrigger,
    ZoneTrigger,
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
# EXPORTS (backwards compatibility)
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
