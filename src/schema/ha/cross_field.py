"""Cross-field consistency validation for HA YAML configs.

Rules that span multiple fields within a single trigger, action,
condition, or the top-level automation dict.  These supplement
the per-model Pydantic validation which only checks individual
field types and required-ness.

Called after structural validation in ``_validate_ha_automation_contents()``.
"""

from __future__ import annotations

import re
from typing import Any

from src.schema.core import ValidationError

_DURATION_RE = re.compile(
    r"^\d{1,3}:\d{2}(:\d{2})?$"  # HH:MM or HH:MM:SS
)


def validate_cross_field(data: dict[str, Any]) -> list[ValidationError]:
    """Run all cross-field rules on a normalized automation dict.

    Returns:
        List of cross-field errors/warnings (empty if all valid).
    """
    errors: list[ValidationError] = []

    _check_top_level(data, errors)
    _check_triggers(data.get("trigger", []), errors)
    _check_actions(data.get("action", []), errors)

    return errors


def _check_top_level(data: dict[str, Any], errors: list[ValidationError]) -> None:
    """Check top-level automation fields."""
    mode = data.get("mode", "single")
    max_val = data.get("max")
    max_exceeded = data.get("max_exceeded")

    if mode in ("queued", "parallel") and max_val is None:
        errors.append(
            ValidationError(
                path="mode",
                message=f"mode '{mode}' should have 'max' set to limit concurrent/queued runs",
                severity="warning",
            )
        )

    if max_exceeded is not None and max_val is None:
        errors.append(
            ValidationError(
                path="max_exceeded",
                message="'max_exceeded' has no effect without 'max'",
                severity="warning",
            )
        )


def _check_triggers(
    triggers: list[dict[str, Any]] | dict[str, Any],
    errors: list[ValidationError],
) -> None:
    """Check trigger-specific cross-field rules."""
    if isinstance(triggers, dict):
        triggers = [triggers]
    if not isinstance(triggers, list):
        return

    for i, trigger in enumerate(triggers):
        if not isinstance(trigger, dict):
            continue

        platform = trigger.get("platform", "")

        if (
            platform == "numeric_state"
            and trigger.get("above") is None
            and trigger.get("below") is None
        ):
            errors.append(
                ValidationError(
                    path=f"trigger[{i}]",
                    message="numeric_state trigger requires at least one of 'above' or 'below'",
                )
            )

        if platform == "state":
            to_val = trigger.get("to")
            from_val = trigger.get("from")
            if to_val is not None and from_val is not None and to_val == from_val:
                errors.append(
                    ValidationError(
                        path=f"trigger[{i}]",
                        message=f"state trigger has identical 'to' and 'from' values ('{to_val}') — will never fire",
                        severity="warning",
                    )
                )

        if platform == "time":
            at_val = trigger.get("at")
            if (
                isinstance(at_val, str)
                and not at_val.startswith("input_datetime.")
                and not _DURATION_RE.match(at_val)
            ):
                errors.append(
                    ValidationError(
                        path=f"trigger[{i}].at",
                        message=f"time trigger 'at' value '{at_val}' is not HH:MM(:SS) or an input_datetime entity",
                        severity="warning",
                    )
                )

        if platform == "sun":
            event = trigger.get("event", "")
            if event not in ("sunrise", "sunset"):
                errors.append(
                    ValidationError(
                        path=f"trigger[{i}].event",
                        message=f"sun trigger 'event' must be 'sunrise' or 'sunset', got '{event}'",
                    )
                )


def _check_actions(
    actions: list[dict[str, Any]] | dict[str, Any],
    errors: list[ValidationError],
) -> None:
    """Check action-specific cross-field rules."""
    if isinstance(actions, dict):
        actions = [actions]
    if not isinstance(actions, list):
        return

    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            continue

        if "delay" in action:
            _check_delay(action["delay"], f"action[{i}].delay", errors)

        if "choose" in action:
            _check_choose(action["choose"], i, errors)

        if "repeat" in action:
            _check_repeat(action["repeat"], i, errors)


def _check_delay(delay: Any, path: str, errors: list[ValidationError]) -> None:
    """Validate delay duration format."""
    if isinstance(delay, str):
        if not _DURATION_RE.match(delay) and not delay.startswith("{{"):
            errors.append(
                ValidationError(
                    path=path,
                    message=f"delay '{delay}' is not HH:MM(:SS) format or a template",
                    severity="warning",
                )
            )
    elif isinstance(delay, dict):
        valid_keys = {"hours", "minutes", "seconds", "milliseconds", "days"}
        unknown = set(delay.keys()) - valid_keys
        if unknown:
            errors.append(
                ValidationError(
                    path=path,
                    message=f"delay has unknown keys: {unknown}. Expected: {valid_keys}",
                    severity="warning",
                )
            )


def _check_choose(
    branches: list[dict[str, Any]],
    action_idx: int,
    errors: list[ValidationError],
) -> None:
    """Validate choose action branches."""
    if not isinstance(branches, list):
        return

    for j, branch in enumerate(branches):
        if not isinstance(branch, dict):
            continue
        if "conditions" not in branch and "condition" not in branch:
            errors.append(
                ValidationError(
                    path=f"action[{action_idx}].choose[{j}]",
                    message="choose branch missing 'conditions'",
                )
            )
        if "sequence" not in branch:
            errors.append(
                ValidationError(
                    path=f"action[{action_idx}].choose[{j}]",
                    message="choose branch missing 'sequence'",
                )
            )


def _check_repeat(
    repeat: dict[str, Any],
    action_idx: int,
    errors: list[ValidationError],
) -> None:
    """Validate repeat action structure."""
    if not isinstance(repeat, dict):
        return

    has_count = "count" in repeat
    has_while = "while" in repeat
    has_until = "until" in repeat
    has_for_each = "for_each" in repeat

    loop_types = sum([has_count, has_while, has_until, has_for_each])
    if loop_types == 0:
        errors.append(
            ValidationError(
                path=f"action[{action_idx}].repeat",
                message="repeat action requires one of 'count', 'while', 'until', or 'for_each'",
            )
        )
    elif loop_types > 1:
        errors.append(
            ValidationError(
                path=f"action[{action_idx}].repeat",
                message="repeat action should have only one of 'count', 'while', 'until', or 'for_each'",
                severity="warning",
            )
        )

    if "sequence" not in repeat:
        errors.append(
            ValidationError(
                path=f"action[{action_idx}].repeat",
                message="repeat action missing 'sequence'",
            )
        )
