"""Home Assistant diagnostics module.

Provides structured analysis of HA error logs, entity health,
integration status, and configuration validation.

Feature 06: HA Diagnostics & Troubleshooting.
"""

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
