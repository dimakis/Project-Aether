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
    # Log parser
    "ErrorLogEntry",
    "parse_error_log",
    "categorize_by_integration",
    "find_patterns",
    "get_error_summary",
    # Error patterns
    "match_known_errors",
    "analyze_errors",
    # Entity health
    "EntityDiagnostic",
    "find_unavailable_entities",
    "find_stale_entities",
    "correlate_unavailability",
    # Integration health
    "IntegrationHealth",
    "get_integration_statuses",
    "find_unhealthy_integrations",
    "diagnose_integration",
    # Config validator
    "ConfigCheckResult",
    "run_config_check",
    "parse_config_errors",
    "validate_automation_yaml",
]
