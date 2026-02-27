"""Jinja2 template syntax validation for HA YAML configs.

Validates that template strings in HA automations (value_template,
wait_template, event_data_template, and inline {{ }} expressions)
are syntactically correct Jinja2 without rendering them.

HA uses a custom Jinja2 environment with extensions (e.g., is_state,
states.*), so we only check syntax -- not filter/function availability.
"""

from __future__ import annotations

import re
from typing import Any

import jinja2

from src.schema.core import ValidationError

_TEMPLATE_RE = re.compile(r"\{\{|\{%")

_TEMPLATE_FIELDS = frozenset(
    {
        "value_template",
        "wait_template",
        "event_data_template",
    }
)

_env = jinja2.Environment(undefined=jinja2.Undefined)  # nosec B701 — parse-only, never renders


def _is_template_string(value: Any) -> bool:
    """Check if a value looks like a Jinja2 template."""
    return isinstance(value, str) and bool(_TEMPLATE_RE.search(value))


def _check_template_syntax(template: str, path: str) -> ValidationError | None:
    """Parse a Jinja2 template string and return an error if invalid."""
    try:
        _env.parse(template)
        return None
    except jinja2.TemplateSyntaxError as exc:
        line_info = f" (line {exc.lineno})" if exc.lineno else ""
        return ValidationError(
            path=path,
            message=f"Jinja2 syntax error{line_info}: {exc.message}",
        )


def validate_templates(data: dict[str, Any]) -> list[ValidationError]:
    """Find and validate all Jinja2 templates in an HA automation dict.

    Walks triggers, actions, and conditions looking for:
    - Explicit template fields (value_template, wait_template, etc.)
    - Any string value containing ``{{`` or ``{%``

    Args:
        data: Normalized automation dict.

    Returns:
        List of template syntax errors (empty if all valid).
    """
    errors: list[ValidationError] = []

    triggers = data.get("trigger", [])
    if isinstance(triggers, dict):
        triggers = [triggers]
    if isinstance(triggers, list):
        for i, trigger in enumerate(triggers):
            if isinstance(trigger, dict):
                _check_dict_templates(trigger, f"trigger[{i}]", errors)

    actions = data.get("action", [])
    if isinstance(actions, dict):
        actions = [actions]
    if isinstance(actions, list):
        for i, action in enumerate(actions):
            if isinstance(action, dict):
                _check_dict_templates(action, f"action[{i}]", errors)

    conditions = data.get("condition", [])
    if isinstance(conditions, dict):
        conditions = [conditions]
    if isinstance(conditions, list):
        for i, condition in enumerate(conditions):
            if isinstance(condition, dict):
                _check_dict_templates(condition, f"condition[{i}]", errors)

    if isinstance(data.get("variables"), dict):
        _check_dict_templates(data["variables"], "variables", errors)

    return errors


def _check_dict_templates(
    d: dict[str, Any],
    prefix: str,
    errors: list[ValidationError],
    *,
    depth: int = 0,
) -> None:
    """Recursively check all template strings in a dict."""
    if depth > 10:
        return

    for key, value in d.items():
        path = f"{prefix}.{key}"

        if (key in _TEMPLATE_FIELDS and isinstance(value, str)) or _is_template_string(value):
            err = _check_template_syntax(value, path)
            if err:
                errors.append(err)
        elif isinstance(value, dict):
            _check_dict_templates(value, path, errors, depth=depth + 1)
        elif isinstance(value, list):
            for j, item in enumerate(value):
                if isinstance(item, dict):
                    _check_dict_templates(item, f"{path}[{j}]", errors, depth=depth + 1)
                elif _is_template_string(item):
                    err = _check_template_syntax(item, f"{path}[{j}]")
                    if err:
                        errors.append(err)
