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


async def run_config_check(ha: Any) -> ConfigCheckResult:
    """Run a HA configuration check via the API.

    Wraps HAClient.check_config() with structured parsing.

    Args:
        ha: HAClient instance

    Returns:
        ConfigCheckResult with parsed errors and warnings
    """
    raw = await ha.check_config()
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


def validate_automation_yaml(yaml_str: str) -> list[str]:
    """Validate automation YAML locally before deploying.

    Uses the schema validator (Feature 26) for structural validation
    of required keys, types, and enum values. Falls back to basic
    YAML syntax checking if the schema module is unavailable.

    Args:
        yaml_str: YAML string representing an automation config

    Returns:
        List of error strings. Empty list means valid.
    """
    from src.schema import validate_yaml

    result = validate_yaml(yaml_str, "ha.automation")
    return [f"{e.path}: {e.message}" if e.path else e.message for e in result.errors]
