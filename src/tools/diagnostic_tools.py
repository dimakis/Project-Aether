"""Diagnostic tools for Home Assistant troubleshooting.

LangChain-compatible tools that give agents the ability to
analyze error logs, find unhealthy entities/integrations,
diagnose individual entities, and validate configuration.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from src.diagnostics.config_validator import run_config_check
from src.diagnostics.entity_health import (
    correlate_unavailability,
    find_unavailable_entities as _find_unavailable,
)
from src.diagnostics.error_patterns import analyze_errors
from src.diagnostics.integration_health import (
    find_unhealthy_integrations,
)
from src.diagnostics.log_parser import parse_error_log, get_error_summary
from src.mcp import get_mcp_client


@tool("analyze_error_log")
async def analyze_error_log() -> str:
    """Fetch and analyze the Home Assistant error log.

    Parses errors, groups by integration, and matches against known
    error patterns to provide actionable recommendations.
    """
    try:
        mcp = get_mcp_client()
        raw_log = await mcp.get_error_log()

        if not raw_log or not raw_log.strip():
            return "Error log is clean -- no errors found."

        entries = parse_error_log(raw_log)
        if not entries:
            return "Error log is clean -- no errors found."

        summary = get_error_summary(entries)
        analysis = analyze_errors(entries)

        counts_by_level = summary.get("counts_by_level", {})
        error_count = counts_by_level.get("ERROR", 0)
        warning_count = counts_by_level.get("WARNING", 0)

        lines = [
            f"Error Log Analysis: {summary['total']} entries, "
            f"{error_count} errors, {warning_count} warnings",
            "",
        ]

        # Top integrations
        top_integrations = summary.get("top_integrations", [])
        if top_integrations:
            lines.append("Top integrations with issues:")
            for integration, count in top_integrations[:5]:
                lines.append(f"  - {integration}: {count} entries")
            lines.append("")

        # Known issues matched
        if analysis:
            lines.append("Known issues detected:")
            for issue in analysis[:5]:
                lines.append(
                    f"  - [{issue.get('category', 'unknown')}] "
                    f"{issue.get('integration', '?')}: "
                    f"{issue['message'][:100]} ({issue['count']}x)"
                )
                if issue.get("suggestion"):
                    lines.append(f"    Recommendation: {issue['suggestion'][:200]}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"Failed to analyze error log: {e}"


@tool("find_unavailable_entities")
async def find_unavailable_entities_tool() -> str:
    """Find all entities that are unavailable or unknown, grouped by integration."""
    try:
        mcp = get_mcp_client()
        diagnostics = await _find_unavailable(mcp)

        if not diagnostics:
            return "All entities are healthy -- no unavailable entities found."

        correlations = correlate_unavailability(diagnostics)

        lines = [f"Found {len(diagnostics)} unavailable entities:"]

        for corr in correlations:
            label = corr["integration"]
            count = corr["count"]
            common = " (likely common cause)" if corr["likely_common_cause"] else ""
            lines.append(f"\n  {label}: {count} entities{common}")
            for eid in corr["entity_ids"][:5]:
                lines.append(f"    - {eid}")
            if count > 5:
                lines.append(f"    ... and {count - 5} more")

        return "\n".join(lines)

    except Exception as e:
        return f"Failed to find unavailable entities: {e}"


@tool("diagnose_entity")
async def diagnose_entity(entity_id: str) -> str:
    """Deep-dive diagnosis of a single entity, including history and related errors."""
    try:
        mcp = get_mcp_client()
        entity = await mcp.get_entity(entity_id)

        if not entity:
            return f"Entity '{entity_id}' not found."

        state = entity.get("state", "unknown")
        attrs = entity.get("attributes") or {}
        friendly_name = attrs.get("friendly_name", entity_id)
        last_changed = entity.get("last_changed", "unknown")

        lines = [
            f"Diagnosis for {entity_id} ({friendly_name})",
            f"  State: {state}",
            f"  Last changed: {last_changed}",
        ]

        # Key attributes
        for key in ("device_class", "unit_of_measurement", "integration"):
            if key in attrs:
                lines.append(f"  {key}: {attrs[key]}")

        # History
        try:
            history = await mcp.get_history(entity_id, hours=24)
            states = history.get("states", []) if isinstance(history, dict) else []
            if states:
                lines.append(f"\n  History (last 24h): {len(states)} state changes")
                # Find transitions
                prev = None
                for s in states[-5:]:
                    s_state = s.get("state", "?")
                    s_time = s.get("last_changed", "?")
                    if s_state != prev:
                        lines.append(f"    {s_time}: {s_state}")
                        prev = s_state
        except Exception:
            lines.append("\n  History: unavailable")

        # Related errors
        try:
            raw_log = await mcp.get_error_log()
            if raw_log:
                domain = entity_id.split(".")[0]
                related = [line for line in raw_log.splitlines()
                           if entity_id in line or domain in line.lower()]
                if related:
                    lines.append(f"\n  Related log entries: {len(related)}")
                    for entry in related[:3]:
                        lines.append(f"    {entry[:120]}")
        except Exception:
            pass

        # Assessment
        if state in ("unavailable", "unknown"):
            lines.append(f"\n  Assessment: Entity is {state} -- likely device/integration issue")
        else:
            lines.append(f"\n  Assessment: Entity appears functional (state={state})")

        return "\n".join(lines)

    except Exception as e:
        return f"Failed to diagnose entity: {e}"


@tool("check_integration_health")
async def check_integration_health() -> str:
    """Check the health of all Home Assistant integrations."""
    try:
        mcp = get_mcp_client()
        unhealthy = await find_unhealthy_integrations(mcp)

        if not unhealthy:
            return "All integrations are healthy -- no issues found."

        lines = [f"Found {len(unhealthy)} unhealthy integrations:"]

        for ih in unhealthy:
            reason = f" (reason: {ih.reason})" if ih.reason else ""
            disabled = f" [disabled by {ih.disabled_by}]" if ih.disabled_by else ""
            lines.append(f"  - {ih.domain} ({ih.title}): {ih.state}{reason}{disabled}")

        return "\n".join(lines)

    except Exception as e:
        return f"Failed to check integration health: {e}"


@tool("validate_config")
async def validate_config() -> str:
    """Run a Home Assistant configuration validation check."""
    try:
        mcp = get_mcp_client()
        result = await run_config_check(mcp)

        if result.result == "valid":
            msg = "Configuration is valid."
            if result.warnings:
                msg += f"\n\nWarnings ({len(result.warnings)}):"
                for w in result.warnings:
                    msg += f"\n  - {w}"
            return msg

        lines = [f"Configuration check result: {result.result}"]
        if result.errors:
            lines.append(f"\nErrors ({len(result.errors)}):")
            for e in result.errors:
                lines.append(f"  - {e}")
        if result.warnings:
            lines.append(f"\nWarnings ({len(result.warnings)}):")
            for w in result.warnings:
                lines.append(f"  - {w}")

        return "\n".join(lines)

    except Exception as e:
        return f"Failed to validate config: {e}"


def get_diagnostic_tools() -> list:
    """Return all diagnostic tools for agent registration."""
    return [
        analyze_error_log,
        find_unavailable_entities_tool,
        diagnose_entity,
        check_integration_health,
        validate_config,
    ]
