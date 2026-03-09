"""Home Assistant diagnostics module.

Provides structured analysis of HA error logs, entity health,
integration status, and configuration validation.

Feature 06: HA Diagnostics & Troubleshooting.

Uses lazy imports to defer loading diagnostic implementations.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    # config_validator
    "ConfigCheckResult": "src.diagnostics.config_validator",
    "parse_config_errors": "src.diagnostics.config_validator",
    "run_config_check": "src.diagnostics.config_validator",
    "validate_automation_yaml": "src.diagnostics.config_validator",
    # entity_health
    "EntityDiagnostic": "src.diagnostics.entity_health",
    "correlate_unavailability": "src.diagnostics.entity_health",
    "find_stale_entities": "src.diagnostics.entity_health",
    "find_unavailable_entities": "src.diagnostics.entity_health",
    # error_patterns
    "analyze_errors": "src.diagnostics.error_patterns",
    "match_known_errors": "src.diagnostics.error_patterns",
    # integration_health
    "IntegrationHealth": "src.diagnostics.integration_health",
    "diagnose_integration": "src.diagnostics.integration_health",
    "find_unhealthy_integrations": "src.diagnostics.integration_health",
    "get_integration_statuses": "src.diagnostics.integration_health",
    # log_parser
    "ErrorLogEntry": "src.diagnostics.log_parser",
    "categorize_by_integration": "src.diagnostics.log_parser",
    "find_patterns": "src.diagnostics.log_parser",
    "get_error_summary": "src.diagnostics.log_parser",
    "parse_error_log": "src.diagnostics.log_parser",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]

    if name in _EXPORTS:
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr

    raise AttributeError(f"module 'src.diagnostics' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
    from src.diagnostics.config_validator import (
        ConfigCheckResult,
        parse_config_errors,
        run_config_check,
        validate_automation_yaml,
    )
    from src.diagnostics.entity_health import (
        EntityDiagnostic,
        correlate_unavailability,
        find_stale_entities,
        find_unavailable_entities,
    )
    from src.diagnostics.error_patterns import (
        analyze_errors,
        match_known_errors,
    )
    from src.diagnostics.integration_health import (
        IntegrationHealth,
        diagnose_integration,
        find_unhealthy_integrations,
        get_integration_statuses,
    )
    from src.diagnostics.log_parser import (
        ErrorLogEntry,
        categorize_by_integration,
        find_patterns,
        get_error_summary,
        parse_error_log,
    )

__all__ = [
    "ConfigCheckResult",
    "EntityDiagnostic",
    "ErrorLogEntry",
    "IntegrationHealth",
    "analyze_errors",
    "categorize_by_integration",
    "correlate_unavailability",
    "diagnose_integration",
    "find_patterns",
    "find_stale_entities",
    "find_unavailable_entities",
    "find_unhealthy_integrations",
    "get_error_summary",
    "get_integration_statuses",
    "match_known_errors",
    "parse_config_errors",
    "parse_error_log",
    "run_config_check",
    "validate_automation_yaml",
]
