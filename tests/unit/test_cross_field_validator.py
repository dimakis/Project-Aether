"""Unit tests for HA cross-field consistency validation.

Tests for src/schema/ha/cross_field.py.
"""

from __future__ import annotations

from src.schema.ha.cross_field import validate_cross_field


class TestNumericStateTrigger:
    """Cross-field rules for numeric_state triggers."""

    def test_missing_both_above_and_below(self) -> None:
        data = {
            "trigger": [{"platform": "numeric_state", "entity_id": "sensor.temp"}],
        }
        errors = validate_cross_field(data)
        assert len(errors) == 1
        assert "at least one of 'above' or 'below'" in errors[0].message

    def test_with_above_set_is_valid(self) -> None:
        data = {
            "trigger": [{"platform": "numeric_state", "entity_id": "sensor.temp", "above": 25}],
        }
        errors = validate_cross_field(data)
        assert errors == []


class TestStateTrigger:
    """Cross-field rules for state triggers."""

    def test_identical_to_and_from_warning(self) -> None:
        data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "light.room",
                    "to": "on",
                    "from": "on",
                }
            ],
        }
        errors = validate_cross_field(data)
        assert len(errors) == 1
        assert "identical" in errors[0].message
        assert errors[0].severity == "warning"

    def test_different_to_from_is_valid(self) -> None:
        data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "light.room",
                    "to": "on",
                    "from": "off",
                }
            ],
        }
        errors = validate_cross_field(data)
        assert errors == []


class TestTimeTrigger:
    """Cross-field rules for time triggers."""

    def test_invalid_at_format_warning(self) -> None:
        data = {
            "trigger": [{"platform": "time", "at": "not_a_time"}],
        }
        errors = validate_cross_field(data)
        assert len(errors) == 1
        assert "not HH:MM(:SS)" in errors[0].message
        assert errors[0].severity == "warning"

    def test_valid_hh_mm_ss(self) -> None:
        data = {
            "trigger": [{"platform": "time", "at": "08:30:00"}],
        }
        errors = validate_cross_field(data)
        assert errors == []

    def test_input_datetime_entity_is_valid(self) -> None:
        data = {
            "trigger": [{"platform": "time", "at": "input_datetime.alarm_time"}],
        }
        errors = validate_cross_field(data)
        assert errors == []


class TestSunTrigger:
    """Cross-field rules for sun triggers."""

    def test_invalid_event(self) -> None:
        data = {
            "trigger": [{"platform": "sun", "event": "noon"}],
        }
        errors = validate_cross_field(data)
        assert len(errors) == 1
        assert "'sunrise' or 'sunset'" in errors[0].message

    def test_sunrise_is_valid(self) -> None:
        data = {
            "trigger": [{"platform": "sun", "event": "sunrise"}],
        }
        errors = validate_cross_field(data)
        assert errors == []

    def test_sunset_is_valid(self) -> None:
        data = {
            "trigger": [{"platform": "sun", "event": "sunset"}],
        }
        errors = validate_cross_field(data)
        assert errors == []


class TestModeTopLevel:
    """Cross-field rules for top-level mode/max/max_exceeded."""

    def test_mode_queued_without_max_warning(self) -> None:
        data = {
            "mode": "queued",
            "trigger": [],
        }
        errors = validate_cross_field(data)
        assert len(errors) == 1
        assert "max" in errors[0].message
        assert errors[0].severity == "warning"

    def test_mode_single_without_max_is_valid(self) -> None:
        data = {
            "mode": "single",
            "trigger": [],
        }
        errors = validate_cross_field(data)
        assert errors == []

    def test_max_exceeded_without_max_warning(self) -> None:
        data = {
            "max_exceeded": "silent",
            "trigger": [],
        }
        errors = validate_cross_field(data)
        assert len(errors) == 1
        assert "'max_exceeded' has no effect without 'max'" in errors[0].message
        assert errors[0].severity == "warning"


class TestDelayAction:
    """Cross-field rules for delay actions."""

    def test_invalid_string_format_warning(self) -> None:
        data = {
            "trigger": [],
            "action": [{"delay": "not_a_duration"}],
        }
        errors = validate_cross_field(data)
        assert len(errors) == 1
        assert "not HH:MM(:SS)" in errors[0].message
        assert errors[0].severity == "warning"

    def test_valid_dict_keys(self) -> None:
        data = {
            "trigger": [],
            "action": [{"delay": {"hours": 1, "minutes": 30}}],
        }
        errors = validate_cross_field(data)
        assert errors == []

    def test_unknown_dict_keys_warning(self) -> None:
        data = {
            "trigger": [],
            "action": [{"delay": {"hours": 1, "bogus": 99}}],
        }
        errors = validate_cross_field(data)
        assert len(errors) == 1
        assert "unknown keys" in errors[0].message
        assert errors[0].severity == "warning"

    def test_template_delay_is_valid(self) -> None:
        data = {
            "trigger": [],
            "action": [{"delay": "{{ states('input_number.wait') }}"}],
        }
        errors = validate_cross_field(data)
        assert errors == []


class TestChooseAction:
    """Cross-field rules for choose actions."""

    def test_branch_missing_conditions(self) -> None:
        data = {
            "trigger": [],
            "action": [{"choose": [{"sequence": [{"service": "light.turn_on"}]}]}],
        }
        errors = validate_cross_field(data)
        assert any("missing 'conditions'" in e.message for e in errors)

    def test_branch_missing_sequence(self) -> None:
        data = {
            "trigger": [],
            "action": [{"choose": [{"conditions": [{"condition": "state"}]}]}],
        }
        errors = validate_cross_field(data)
        assert any("missing 'sequence'" in e.message for e in errors)

    def test_valid_branch(self) -> None:
        data = {
            "trigger": [],
            "action": [
                {
                    "choose": [
                        {
                            "conditions": [{"condition": "state"}],
                            "sequence": [{"service": "light.turn_on"}],
                        }
                    ]
                }
            ],
        }
        errors = validate_cross_field(data)
        assert errors == []


class TestRepeatAction:
    """Cross-field rules for repeat actions."""

    def test_missing_loop_type(self) -> None:
        data = {
            "trigger": [],
            "action": [{"repeat": {"sequence": [{"service": "light.turn_on"}]}}],
        }
        errors = validate_cross_field(data)
        assert any("requires one of" in e.message for e in errors)

    def test_missing_sequence(self) -> None:
        data = {
            "trigger": [],
            "action": [{"repeat": {"count": 3}}],
        }
        errors = validate_cross_field(data)
        assert any("missing 'sequence'" in e.message for e in errors)

    def test_count_plus_sequence_is_valid(self) -> None:
        data = {
            "trigger": [],
            "action": [
                {
                    "repeat": {
                        "count": 3,
                        "sequence": [{"service": "light.turn_on"}],
                    }
                }
            ],
        }
        errors = validate_cross_field(data)
        assert errors == []
