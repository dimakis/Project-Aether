"""Unit tests for previously untested HA trigger/action/condition types.

Validates that each model can be instantiated via model_validate()
with minimal valid data, following the pattern from test_schema_ha_automation.py.
"""

from __future__ import annotations

# =============================================================================
# TRIGGER TYPES
# =============================================================================


class TestTagTrigger:
    def test_valid(self) -> None:
        from src.schema.ha.triggers import TagTrigger

        t = TagTrigger.model_validate({"platform": "tag", "tag_id": "my_tag"})
        assert t.platform == "tag"
        assert t.tag_id == "my_tag"


class TestCalendarTrigger:
    def test_valid(self) -> None:
        from src.schema.ha.triggers import CalendarTrigger

        t = CalendarTrigger.model_validate(
            {"platform": "calendar", "entity_id": "calendar.holidays", "event": "start"}
        )
        assert t.platform == "calendar"
        assert t.entity_id == "calendar.holidays"
        assert t.event == "start"


class TestHomeassistantTrigger:
    def test_valid(self) -> None:
        from src.schema.ha.triggers import HomeassistantTrigger

        t = HomeassistantTrigger.model_validate({"platform": "homeassistant", "event": "start"})
        assert t.platform == "homeassistant"
        assert t.event == "start"


class TestTimePatternTrigger:
    def test_valid(self) -> None:
        from src.schema.ha.triggers import TimePatternTrigger

        t = TimePatternTrigger.model_validate({"platform": "time_pattern", "minutes": "/5"})
        assert t.platform == "time_pattern"
        assert t.minutes == "/5"


class TestPersistentNotificationTrigger:
    def test_valid(self) -> None:
        from src.schema.ha.triggers import PersistentNotificationTrigger

        t = PersistentNotificationTrigger.model_validate(
            {"platform": "persistent_notification", "notification_id": "test"}
        )
        assert t.platform == "persistent_notification"
        assert t.notification_id == "test"


# =============================================================================
# ACTION TYPES
# =============================================================================


class TestConditionAction:
    def test_valid(self) -> None:
        from src.schema.ha.actions import ConditionAction

        a = ConditionAction.model_validate(
            {"condition": "state", "entity_id": "light.room", "state": "on"}
        )
        assert a.condition == "state"
        assert a.entity_id == "light.room"
        assert a.state == "on"


class TestRepeatAction:
    def test_valid(self) -> None:
        from src.schema.ha.actions import RepeatAction

        a = RepeatAction.model_validate(
            {"repeat": {"count": 3, "sequence": [{"service": "light.turn_on"}]}}
        )
        assert a.repeat["count"] == 3
        assert len(a.repeat["sequence"]) == 1


class TestChooseAction:
    def test_valid(self) -> None:
        from src.schema.ha.actions import ChooseAction

        a = ChooseAction.model_validate(
            {
                "choose": [
                    {
                        "conditions": [{"condition": "state"}],
                        "sequence": [{"service": "light.turn_on"}],
                    }
                ]
            }
        )
        assert len(a.choose) == 1


class TestIfAction:
    def test_valid(self) -> None:
        from src.schema.ha.actions import IfAction

        a = IfAction.model_validate(
            {
                "if": [{"condition": "state"}],
                "then": [{"service": "light.turn_on"}],
            }
        )
        assert a.if_ == [{"condition": "state"}]
        assert a.then == [{"service": "light.turn_on"}]


class TestStopAction:
    def test_valid(self) -> None:
        from src.schema.ha.actions import StopAction

        a = StopAction.model_validate({"stop": "All done"})
        assert a.stop == "All done"


class TestParallelAction:
    def test_valid(self) -> None:
        from src.schema.ha.actions import ParallelAction

        a = ParallelAction.model_validate(
            {"parallel": [{"service": "light.turn_on"}, {"service": "switch.turn_off"}]}
        )
        assert len(a.parallel) == 2


class TestVariablesAction:
    def test_valid(self) -> None:
        from src.schema.ha.actions import VariablesAction

        a = VariablesAction.model_validate({"variables": {"my_var": "hello"}})
        assert a.variables == {"my_var": "hello"}


# =============================================================================
# CONDITION TYPES
# =============================================================================


class TestSunCondition:
    def test_valid(self) -> None:
        from src.schema.ha.conditions import SunCondition

        c = SunCondition.model_validate(
            {"condition": "sun", "after": "sunrise", "before": "sunset"}
        )
        assert c.condition == "sun"
        assert c.after == "sunrise"
        assert c.before == "sunset"


class TestZoneCondition:
    def test_valid(self) -> None:
        from src.schema.ha.conditions import ZoneCondition

        c = ZoneCondition.model_validate(
            {"condition": "zone", "entity_id": "person.me", "zone": "zone.home"}
        )
        assert c.condition == "zone"
        assert c.entity_id == "person.me"
        assert c.zone == "zone.home"


class TestTriggerCondition:
    def test_valid(self) -> None:
        from src.schema.ha.conditions import TriggerCondition

        c = TriggerCondition.model_validate({"condition": "trigger", "id": "my_trigger"})
        assert c.condition == "trigger"
        assert c.id == "my_trigger"


class TestDeviceCondition:
    def test_valid(self) -> None:
        from src.schema.ha.conditions import DeviceCondition

        c = DeviceCondition.model_validate(
            {
                "condition": "device",
                "device_id": "abc123",
                "domain": "light",
                "type": "is_on",
            }
        )
        assert c.condition == "device"
        assert c.device_id == "abc123"
        assert c.domain == "light"
        assert c.type == "is_on"
