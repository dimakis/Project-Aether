"""Unit tests for HA automation schema.

T204: Tests for HAAutomation with trigger/action/condition discriminated unions.
Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

# =============================================================================
# TRIGGER SCHEMA TESTS
# =============================================================================


class TestStateTrigger:
    """Test state trigger schema."""

    def test_valid_state_trigger(self) -> None:
        from src.schema.ha.automation import StateTrigger

        t = StateTrigger(platform="state", entity_id="binary_sensor.motion", to="on")
        assert t.platform == "state"
        assert t.entity_id == "binary_sensor.motion"
        assert t.to == "on"

    def test_state_trigger_with_from_and_for(self) -> None:
        from src.schema.ha.automation import StateTrigger

        t = StateTrigger(
            platform="state",
            entity_id="light.bedroom",
            to="off",
            **{"from": "on", "for": "00:05:00"},
        )
        assert t.from_ == "on"
        assert t.for_ == "00:05:00"

    def test_state_trigger_entity_list(self) -> None:
        from src.schema.ha.automation import StateTrigger

        t = StateTrigger(
            platform="state",
            entity_id=["light.a", "light.b"],
            to="on",
        )
        assert t.entity_id == ["light.a", "light.b"]

    def test_state_trigger_missing_entity_id(self) -> None:
        from src.schema.ha.automation import StateTrigger

        with pytest.raises(ValidationError, match="entity_id"):
            StateTrigger(platform="state")

    def test_state_trigger_not_to_and_not_from(self) -> None:
        """not_to and not_from fields are accepted."""
        from src.schema.ha.automation import StateTrigger

        t = StateTrigger(
            platform="state",
            entity_id="vacuum.test",
            not_from=["unknown", "unavailable"],
            to="on",
        )
        assert t.not_from == ["unknown", "unavailable"]


class TestTimeTrigger:
    """Test time trigger schema."""

    def test_valid_time_trigger(self) -> None:
        from src.schema.ha.automation import TimeTrigger

        t = TimeTrigger(platform="time", at="08:00:00")
        assert t.platform == "time"
        assert t.at == "08:00:00"

    def test_time_trigger_list(self) -> None:
        from src.schema.ha.automation import TimeTrigger

        t = TimeTrigger(platform="time", at=["08:00:00", "20:00:00"])
        assert t.at == ["08:00:00", "20:00:00"]

    def test_time_trigger_with_offset_dict(self) -> None:
        """HA 2024+ supports dict with entity_id + offset."""
        from src.schema.ha.automation import TimeTrigger

        t = TimeTrigger(
            platform="time",
            at={"entity_id": "sensor.phone_alarm", "offset": "-00:05:00"},
        )
        assert isinstance(t.at, dict)
        assert t.at["entity_id"] == "sensor.phone_alarm"

    def test_time_trigger_mixed_list(self) -> None:
        """List mixing strings and dicts."""
        from src.schema.ha.automation import TimeTrigger

        t = TimeTrigger(
            platform="time",
            at=[
                "08:00:00",
                {"entity_id": "sensor.bus_arrival", "offset": "-00:10:00"},
            ],
        )
        assert len(t.at) == 2

    def test_time_trigger_weekday(self) -> None:
        """Weekday filtering on time trigger."""
        from src.schema.ha.automation import TimeTrigger

        t = TimeTrigger(
            platform="time",
            at="08:00:00",
            weekday=["mon", "tue", "wed", "thu", "fri"],
        )
        assert len(t.weekday) == 5


class TestSunTrigger:
    """Test sun trigger schema."""

    def test_valid_sun_trigger(self) -> None:
        from src.schema.ha.automation import SunTrigger

        t = SunTrigger(platform="sun", event="sunset")
        assert t.event == "sunset"

    def test_sun_trigger_with_offset(self) -> None:
        from src.schema.ha.automation import SunTrigger

        t = SunTrigger(platform="sun", event="sunrise", offset="-00:30:00")
        assert t.offset == "-00:30:00"


class TestNumericStateTrigger:
    """Test numeric_state trigger schema."""

    def test_above(self) -> None:
        from src.schema.ha.automation import NumericStateTrigger

        t = NumericStateTrigger(
            platform="numeric_state",
            entity_id="sensor.temperature",
            above=25.0,
        )
        assert t.above == 25.0

    def test_below(self) -> None:
        from src.schema.ha.automation import NumericStateTrigger

        t = NumericStateTrigger(
            platform="numeric_state",
            entity_id="sensor.humidity",
            below=30,
        )
        assert t.below == 30


class TestEventTrigger:
    """Test event trigger schema."""

    def test_valid_event_trigger(self) -> None:
        from src.schema.ha.automation import EventTrigger

        t = EventTrigger(platform="event", event_type="call_service")
        assert t.event_type == "call_service"

    def test_event_trigger_with_data(self) -> None:
        from src.schema.ha.automation import EventTrigger

        t = EventTrigger(
            platform="event",
            event_type="zha_event",
            event_data={"device_ieee": "00:11:22"},
        )
        assert t.event_data == {"device_ieee": "00:11:22"}


class TestTemplateTrigger:
    """Test template trigger schema."""

    def test_valid_template_trigger(self) -> None:
        from src.schema.ha.automation import TemplateTrigger

        t = TemplateTrigger(
            platform="template",
            value_template="{{ states('sensor.temp') | float > 25 }}",
        )
        assert "sensor.temp" in t.value_template


class TestWebhookTrigger:
    """Test webhook trigger schema."""

    def test_valid_webhook_trigger(self) -> None:
        from src.schema.ha.automation import WebhookTrigger

        t = WebhookTrigger(platform="webhook", webhook_id="my_hook")
        assert t.webhook_id == "my_hook"


class TestMqttTrigger:
    """Test MQTT trigger schema."""

    def test_valid_mqtt_trigger(self) -> None:
        from src.schema.ha.automation import MqttTrigger

        t = MqttTrigger(platform="mqtt", topic="home/sensor/temp")
        assert t.topic == "home/sensor/temp"


class TestDeviceTrigger:
    """Test device trigger schema."""

    def test_valid_device_trigger(self) -> None:
        from src.schema.ha.automation import DeviceTrigger

        t = DeviceTrigger(
            platform="device",
            device_id="abc123",
            domain="light",
            type="turned_on",
        )
        assert t.device_id == "abc123"


class TestZoneTrigger:
    """Test zone trigger schema."""

    def test_valid_zone_trigger(self) -> None:
        from src.schema.ha.automation import ZoneTrigger

        t = ZoneTrigger(
            platform="zone",
            entity_id="person.john",
            zone="zone.home",
            event="enter",
        )
        assert t.event == "enter"


class TestGeoLocationTrigger:
    """Test geolocation trigger schema."""

    def test_valid_geo_trigger(self) -> None:
        from src.schema.ha.automation import GeoLocationTrigger

        t = GeoLocationTrigger(
            platform="geo_location",
            source="nsw_rural_fire_service_feed",
            zone="zone.bushfire_monitoring",
            event="enter",
        )
        assert t.source == "nsw_rural_fire_service_feed"
        assert t.event == "enter"

    def test_geo_trigger_missing_source(self) -> None:
        from src.schema.ha.automation import GeoLocationTrigger

        with pytest.raises(ValidationError, match="source"):
            GeoLocationTrigger(
                platform="geo_location",
                zone="zone.home",
                event="enter",
            )


class TestConversationTrigger:
    """Test conversation/sentence trigger schema."""

    def test_valid_conversation_trigger(self) -> None:
        from src.schema.ha.automation import ConversationTrigger

        t = ConversationTrigger(
            platform="conversation",
            command="turn on the lights",
        )
        assert t.command == "turn on the lights"

    def test_conversation_trigger_list(self) -> None:
        from src.schema.ha.automation import ConversationTrigger

        t = ConversationTrigger(
            platform="conversation",
            command=["turn on the lights", "lights on"],
        )
        assert len(t.command) == 2


# =============================================================================
# ACTION SCHEMA TESTS
# =============================================================================


class TestServiceAction:
    """Test service call action schema."""

    def test_valid_service_action(self) -> None:
        from src.schema.ha.automation import ServiceAction

        a = ServiceAction(
            service="light.turn_on",
            target={"entity_id": "light.bedroom"},
        )
        assert a.service == "light.turn_on"

    def test_service_action_with_data(self) -> None:
        from src.schema.ha.automation import ServiceAction

        a = ServiceAction(
            service="light.turn_on",
            target={"entity_id": "light.bedroom"},
            data={"brightness": 255, "color_temp": 300},
        )
        assert a.data["brightness"] == 255

    def test_service_action_missing_service(self) -> None:
        from src.schema.ha.automation import ServiceAction

        with pytest.raises(ValidationError, match="service"):
            ServiceAction()


class TestDelayAction:
    """Test delay action schema."""

    def test_string_delay(self) -> None:
        from src.schema.ha.automation import DelayAction

        a = DelayAction(delay="00:00:30")
        assert a.delay == "00:00:30"

    def test_dict_delay(self) -> None:
        from src.schema.ha.automation import DelayAction

        a = DelayAction(delay={"seconds": 30})
        assert a.delay == {"seconds": 30}


class TestWaitTemplateAction:
    """Test wait_template action schema."""

    def test_valid_wait_template(self) -> None:
        from src.schema.ha.automation import WaitTemplateAction

        a = WaitTemplateAction(
            wait_template="{{ is_state('light.bedroom', 'off') }}",
        )
        assert "light.bedroom" in a.wait_template


class TestEventAction:
    """Test event fire action schema."""

    def test_valid_event_action(self) -> None:
        from src.schema.ha.automation import EventAction

        a = EventAction(event="custom_event", event_data={"key": "value"})
        assert a.event == "custom_event"


class TestWaitForTriggerAction:
    """Test wait_for_trigger action schema."""

    def test_valid_wait_for_trigger(self) -> None:
        from src.schema.ha.automation import WaitForTriggerAction

        a = WaitForTriggerAction(
            wait_for_trigger=[
                {"platform": "state", "entity_id": "light.bedroom", "to": "on"},
            ],
            timeout="00:01:00",
            continue_on_timeout=True,
        )
        assert len(a.wait_for_trigger) == 1
        assert a.timeout == "00:01:00"
        assert a.continue_on_timeout is True

    def test_wait_for_trigger_missing_triggers(self) -> None:
        from src.schema.ha.automation import WaitForTriggerAction

        with pytest.raises(ValidationError, match="wait_for_trigger"):
            WaitForTriggerAction()


# =============================================================================
# CONDITION SCHEMA TESTS
# =============================================================================


class TestStateCondition:
    """Test state condition schema."""

    def test_valid_state_condition(self) -> None:
        from src.schema.ha.automation import StateCondition

        c = StateCondition(
            condition="state",
            entity_id="binary_sensor.motion",
            state="on",
        )
        assert c.entity_id == "binary_sensor.motion"
        assert c.state == "on"


class TestTimeCondition:
    """Test time condition schema."""

    def test_valid_time_condition(self) -> None:
        from src.schema.ha.automation import TimeCondition

        c = TimeCondition(
            condition="time",
            after="18:00:00",
            before="23:00:00",
        )
        assert c.after == "18:00:00"


class TestNumericStateCondition:
    """Test numeric_state condition schema."""

    def test_valid_numeric_condition(self) -> None:
        from src.schema.ha.automation import NumericStateCondition

        c = NumericStateCondition(
            condition="numeric_state",
            entity_id="sensor.temperature",
            above=20,
        )
        assert c.above == 20


class TestTemplateCondition:
    """Test template condition schema."""

    def test_valid_template_condition(self) -> None:
        from src.schema.ha.automation import TemplateCondition

        c = TemplateCondition(
            condition="template",
            value_template="{{ is_state('input_boolean.guest', 'on') }}",
        )
        assert "guest" in c.value_template


class TestLogicalConditions:
    """Test and/or/not conditions."""

    def test_and_condition(self) -> None:
        from src.schema.ha.automation import AndCondition

        c = AndCondition(
            condition="and",
            conditions=[
                {"condition": "state", "entity_id": "light.a", "state": "on"},
                {"condition": "state", "entity_id": "light.b", "state": "on"},
            ],
        )
        assert len(c.conditions) == 2

    def test_or_condition(self) -> None:
        from src.schema.ha.automation import OrCondition

        c = OrCondition(
            condition="or",
            conditions=[
                {"condition": "state", "entity_id": "light.a", "state": "on"},
            ],
        )
        assert c.condition == "or"

    def test_not_condition(self) -> None:
        from src.schema.ha.automation import NotCondition

        c = NotCondition(
            condition="not",
            conditions=[
                {"condition": "state", "entity_id": "light.a", "state": "off"},
            ],
        )
        assert c.condition == "not"


# =============================================================================
# FULL AUTOMATION SCHEMA TESTS
# =============================================================================


class TestHAAutomation:
    """Test full HAAutomation model."""

    def test_minimal_automation(self) -> None:
        """Minimum valid automation: trigger + action (alias is optional)."""
        from src.schema.ha.automation import HAAutomation

        auto = HAAutomation(
            trigger=[{"platform": "time", "at": "08:00:00"}],
            action=[{"service": "light.turn_on"}],
        )
        assert auto.alias is None
        assert auto.mode.value == "single"  # default

    def test_automation_with_alias(self) -> None:
        """Alias can be provided."""
        from src.schema.ha.automation import HAAutomation

        auto = HAAutomation(
            alias="Test Automation",
            trigger=[{"platform": "time", "at": "08:00:00"}],
            action=[{"service": "light.turn_on"}],
        )
        assert auto.alias == "Test Automation"

    def test_full_automation(self) -> None:
        """Full automation with all fields."""
        from src.schema.ha.automation import HAAutomation

        auto = HAAutomation(
            id="morning_lights",
            alias="Morning Lights",
            description="Turn on lights at sunrise",
            trigger=[
                {"platform": "sun", "event": "sunrise", "offset": "00:15:00"},
            ],
            condition=[
                {"condition": "state", "entity_id": "input_boolean.vacation", "state": "off"},
            ],
            action=[
                {
                    "service": "light.turn_on",
                    "target": {"entity_id": "light.bedroom"},
                    "data": {"brightness": 128},
                },
            ],
            mode="restart",
            trigger_variables={"my_var": "test"},
            initial_state=True,
        )
        assert auto.id == "morning_lights"
        assert auto.description == "Turn on lights at sunrise"
        assert auto.mode.value == "restart"
        assert auto.trigger_variables == {"my_var": "test"}
        assert auto.initial_state is True

    def test_automation_missing_trigger(self) -> None:
        """Missing trigger should fail validation."""
        from src.schema.ha.automation import HAAutomation

        with pytest.raises(ValidationError, match="trigger"):
            HAAutomation(
                alias="Test",
                action=[{"service": "light.turn_on"}],
            )

    def test_automation_missing_action(self) -> None:
        """Missing action should fail validation."""
        from src.schema.ha.automation import HAAutomation

        with pytest.raises(ValidationError, match="action"):
            HAAutomation(
                alias="Test",
                trigger=[{"platform": "time", "at": "08:00"}],
            )

    def test_automation_invalid_mode(self) -> None:
        """Invalid mode value should fail."""
        from src.schema.ha.automation import HAAutomation

        with pytest.raises(ValidationError):
            HAAutomation(
                alias="Test",
                trigger=[{"platform": "time", "at": "08:00"}],
                action=[{"service": "light.turn_on"}],
                mode="invalid_mode",
            )

    def test_automation_single_trigger_not_list(self) -> None:
        """Single trigger dict (not list) should be accepted."""
        from src.schema.ha.automation import HAAutomation

        auto = HAAutomation(
            alias="Test",
            trigger={"platform": "time", "at": "08:00"},
            action=[{"service": "light.turn_on"}],
        )
        assert auto.trigger is not None

    def test_automation_single_action_not_list(self) -> None:
        """Single action dict (not list) should be accepted."""
        from src.schema.ha.automation import HAAutomation

        auto = HAAutomation(
            alias="Test",
            trigger=[{"platform": "time", "at": "08:00"}],
            action={"service": "light.turn_on"},
        )
        assert auto.action is not None


class TestHAAutomationYAMLRoundTrip:
    """Test validating real-world YAML strings through the schema."""

    def test_validate_yaml_via_registry(self) -> None:
        """Register and validate automation YAML via SchemaRegistry."""
        from src.schema.core import SchemaRegistry
        from src.schema.ha.automation import HAAutomation

        registry = SchemaRegistry()
        registry.register("ha.automation", HAAutomation)

        yaml_str = """\
alias: Motion Lights
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
condition:
  - condition: time
    after: "18:00:00"
    before: "23:00:00"
mode: single
"""
        data = yaml.safe_load(yaml_str)
        result = registry.validate("ha.automation", data)
        assert result.valid is True, f"Errors: {result.errors}"

    def test_validate_invalid_yaml_via_registry(self) -> None:
        """Invalid YAML (missing trigger and action) caught by schema."""
        from src.schema.core import SchemaRegistry
        from src.schema.ha.automation import HAAutomation

        registry = SchemaRegistry()
        registry.register("ha.automation", HAAutomation)

        data = {
            "alias": "Test",
            # missing trigger and action
        }
        result = registry.validate("ha.automation", data)
        assert result.valid is False
        assert any("trigger" in e.message for e in result.errors)

    def test_validate_automation_without_alias(self) -> None:
        """Automation without alias passes validation (alias is optional in HA)."""
        from src.schema.core import SchemaRegistry
        from src.schema.ha.automation import HAAutomation

        registry = SchemaRegistry()
        registry.register("ha.automation", HAAutomation)

        data = {
            "trigger": [{"platform": "time", "at": "08:00"}],
            "action": [{"service": "light.turn_on"}],
        }
        result = registry.validate("ha.automation", data)
        assert result.valid is True, f"Errors: {result.errors}"


# =============================================================================
# MODEL MAP TESTS
# =============================================================================


class TestModelMaps:
    """Test that model maps are complete and consistent."""

    def test_trigger_model_map_keys(self) -> None:
        """TRIGGER_MODEL_MAP covers all non-generic trigger types."""
        from src.schema.ha.automation import TRIGGER_MODEL_MAP

        expected = {
            "state",
            "time",
            "sun",
            "numeric_state",
            "event",
            "template",
            "webhook",
            "mqtt",
            "device",
            "zone",
            "tag",
            "calendar",
            "homeassistant",
            "time_pattern",
            "persistent_notification",
            "geo_location",
            "conversation",
        }
        assert set(TRIGGER_MODEL_MAP.keys()) == expected

    def test_action_key_map_keys(self) -> None:
        """ACTION_KEY_MAP covers all non-generic action types."""
        from src.schema.ha.automation import ACTION_KEY_MAP

        expected = {
            "service",
            "delay",
            "wait_template",
            "event",
            "condition",
            "repeat",
            "choose",
            "if",
            "stop",
            "parallel",
            "variables",
            "wait_for_trigger",
        }
        assert set(ACTION_KEY_MAP.keys()) == expected

    def test_condition_model_map_keys(self) -> None:
        """CONDITION_MODEL_MAP covers all non-generic condition types."""
        from src.schema.ha.automation import CONDITION_MODEL_MAP

        expected = {
            "state",
            "time",
            "sun",
            "numeric_state",
            "template",
            "zone",
            "trigger",
            "device",
            "and",
            "or",
            "not",
        }
        assert set(CONDITION_MODEL_MAP.keys()) == expected
