"""Home Assistant trigger models for automation YAML schema.

All trigger types discriminated by 'platform' field.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


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
