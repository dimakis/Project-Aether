"""Home Assistant configuration validator.

Provides structured config checking and local YAML validation
for automations before deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfigCheckResult:
    """Structured result from a HA configuration check."""

    result: str  # "valid", "invalid", "error", "unknown"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def run_config_check(mcp: Any) -> ConfigCheckResult:
    """Run a HA configuration check via the API.

    Wraps MCPClient.check_config() with structured parsing.

    Args:
        mcp: MCPClient instance

    Returns:
        ConfigCheckResult with parsed errors and warnings
    """
    raw = await mcp.check_config()
    return parse_config_errors(raw)


def parse_config_errors(raw_result: dict[str, Any]) -> ConfigCheckResult:
    """Parse raw config check result into a structured ConfigCheckResult.

    Extracts individual error messages from the errors string,
    splitting on newlines.

    Args:
        raw_result: Raw dict from HA config check API

    Returns:
        ConfigCheckResult with parsed errors
    """
    result_str = raw_result.get("result", "unknown")
    errors_raw = raw_result.get("errors", "")

    errors: list[str] = []
    if isinstance(errors_raw, str) and errors_raw.strip():
        errors = [line.strip() for line in errors_raw.splitlines() if line.strip()]
    elif isinstance(errors_raw, list):
        errors = [str(e) for e in errors_raw]

    warnings_raw = raw_result.get("warnings", "")
    warnings: list[str] = []
    if isinstance(warnings_raw, str) and warnings_raw.strip():
        warnings = [line.strip() for line in warnings_raw.splitlines() if line.strip()]
    elif isinstance(warnings_raw, list):
        warnings = [str(w) for w in warnings_raw]

    return ConfigCheckResult(
        result=result_str,
        errors=errors,
        warnings=warnings,
    )


_REQUIRED_AUTOMATION_KEYS = {"alias", "trigger", "action"}


def validate_automation_yaml(yaml_str: str) -> list[str]:
    """Validate automation YAML locally before deploying.

    Checks for required keys (alias, trigger, action) and valid
    YAML syntax. Does NOT validate trigger/action schemas -- that's
    HA's job at deploy time.

    Args:
        yaml_str: YAML string representing an automation config

    Returns:
        List of error strings. Empty list means valid.
    """
    import yaml as yaml_lib

    errors: list[str] = []

    # Parse YAML
    try:
        data = yaml_lib.safe_load(yaml_str)
    except yaml_lib.YAMLError as e:
        return [f"Invalid YAML syntax: {e}"]

    # Must be a dict
    if not isinstance(data, dict):
        return ["Automation config must be a YAML mapping (dict), not a list or scalar"]

    # Check required keys
    for key in _REQUIRED_AUTOMATION_KEYS:
        if key not in data:
            errors.append(f"Missing required key: '{key}'")

    return errors
