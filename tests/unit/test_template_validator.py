"""Unit tests for HA Jinja2 template syntax validation.

Tests for src/schema/ha/template_validator.py.
"""

from __future__ import annotations

from src.schema.ha.template_validator import (
    _check_template_syntax,
    _is_template_string,
    validate_templates,
)


class TestIsTemplateString:
    """Tests for _is_template_string helper."""

    def test_detects_double_brace(self) -> None:
        assert _is_template_string("{{ states('sensor.temp') }}") is True

    def test_detects_block_tag(self) -> None:
        assert _is_template_string("{% if true %}yes{% endif %}") is True

    def test_rejects_plain_string(self) -> None:
        assert _is_template_string("just a plain string") is False

    def test_rejects_non_string(self) -> None:
        assert _is_template_string(42) is False
        assert _is_template_string(None) is False
        assert _is_template_string(["{{ x }}"]) is False


class TestCheckTemplateSyntax:
    """Tests for _check_template_syntax helper."""

    def test_returns_none_for_valid_template(self) -> None:
        result = _check_template_syntax(
            "{{ states('sensor.temp') | float > 25 }}",
            "trigger[0].value_template",
        )
        assert result is None

    def test_returns_error_with_line_number(self) -> None:
        result = _check_template_syntax(
            "{{ states('sensor.temp') | }}",
            "trigger[0].value_template",
        )
        assert result is not None
        assert "Jinja2 syntax error" in result.message
        assert "line" in result.message
        assert result.path == "trigger[0].value_template"


class TestValidateTemplates:
    """Tests for the top-level validate_templates function."""

    def test_valid_template_no_errors(self) -> None:
        data = {
            "trigger": [
                {
                    "platform": "template",
                    "value_template": "{{ states('sensor.temp') | float > 25 }}",
                }
            ],
            "action": [{"service": "light.turn_on"}],
        }
        errors = validate_templates(data)
        assert errors == []

    def test_catches_unclosed_brace_in_value_template(self) -> None:
        data = {
            "trigger": [
                {
                    "platform": "template",
                    "value_template": "{{ states('sensor.temp') | float > 25 ",
                }
            ],
            "action": [],
        }
        errors = validate_templates(data)
        assert len(errors) == 1
        assert "Jinja2 syntax error" in errors[0].message
        assert errors[0].path == "trigger[0].value_template"

    def test_catches_bad_filter_in_trigger_template(self) -> None:
        data = {
            "trigger": [
                {
                    "platform": "template",
                    "value_template": "{{ states('sensor.temp') | }}",
                }
            ],
            "action": [],
        }
        errors = validate_templates(data)
        assert len(errors) == 1
        assert "Jinja2 syntax error" in errors[0].message

    def test_finds_templates_in_nested_action_data(self) -> None:
        data = {
            "trigger": [],
            "action": [
                {
                    "service": "notify.mobile",
                    "data": {
                        "message": "{{ states('sensor.temp') | }}",
                    },
                }
            ],
        }
        errors = validate_templates(data)
        assert len(errors) == 1
        assert errors[0].path == "action[0].data.message"

    def test_skips_non_template_strings(self) -> None:
        data = {
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.motion",
                    "to": "on",
                }
            ],
            "action": [{"service": "light.turn_on"}],
        }
        errors = validate_templates(data)
        assert errors == []

    def test_checks_wait_template_field(self) -> None:
        data = {
            "trigger": [],
            "action": [
                {
                    "wait_template": "{{ is_state('light.bedroom', 'off') | }}",
                }
            ],
        }
        errors = validate_templates(data)
        assert len(errors) == 1
        assert errors[0].path == "action[0].wait_template"

    def test_handles_empty_data_gracefully(self) -> None:
        errors = validate_templates({})
        assert errors == []

    def test_handles_empty_trigger_and_action_lists(self) -> None:
        data: dict[str, list[str]] = {"trigger": [], "action": [], "condition": []}
        errors = validate_templates(data)
        assert errors == []

    def test_validates_condition_templates(self) -> None:
        data = {
            "trigger": [],
            "action": [],
            "condition": [
                {
                    "condition": "template",
                    "value_template": "{{ states('sensor.x') | }}",
                }
            ],
        }
        errors = validate_templates(data)
        assert len(errors) == 1
        assert errors[0].path == "condition[0].value_template"

    def test_validates_variables_templates(self) -> None:
        data = {
            "trigger": [],
            "action": [],
            "variables": {
                "greeting": "{{ 'hello' | }}",
            },
        }
        errors = validate_templates(data)
        assert len(errors) == 1
        assert errors[0].path == "variables.greeting"
