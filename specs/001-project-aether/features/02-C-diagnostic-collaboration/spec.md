**Completed**: 2026-02-07

# Feature: Diagnostic Collaboration (Architect + Data Scientist)

**Status**: Complete  
**Priority**: P2  
**Depends on**: US2 (Architect), US3 (Data Scientist)

## Goal

Enable the Architect agent to diagnose Home Assistant system issues by pulling logs, rich historical data, and configuration status, then delegating to the Data Scientist with diagnostic context and instructions for collaborative troubleshooting.

## Problem Statement

A user lost energy data on their HA dashboards from both a car charger (hub measures all energy in) and a Panasonic heat system. The Architect correctly identified the entities to investigate but reported it had no access to HA logs or means to pull detailed sensor data for analysis. The Data Scientist could only perform predefined energy analysis types and had no way to receive diagnostic context from the Architect.

## User Experience

1. User describes an issue: "My car charger energy data disappeared from dashboards"
2. Architect pulls HA error logs, checks config validity, and retrieves detailed entity history
3. Architect identifies potential issues (data gaps, integration errors, sensor failures)
4. Architect delegates to Data Scientist with collected evidence and specific investigation instructions
5. Data Scientist analyzes the data and returns diagnostic findings
6. Architect can loop: pull more data based on DS findings and re-delegate if needed
7. Architect presents a unified diagnosis to the user

## New Capabilities

### Architect gains:
- `get_ha_logs` tool — fetch HA error/warning logs
- `check_ha_config` tool — validate HA configuration
- Enhanced `get_entity_history` — detailed mode with gap detection and statistics
- `diagnose_issue` tool — delegate diagnostic analysis to Data Scientist with context

### Data Scientist gains:
- `DIAGNOSTIC` analysis type — troubleshooting mode that works with Architect-provided context
- Diagnostic prompt path — analyzes data gaps, integration failures, sensor connectivity issues

## MCP Tools Used

- `get_error_log` (existing MCPClient method, newly exposed as tool)
- `check_config` (existing MCPClient method, newly exposed as tool)
- `get_history` (existing, enhanced presentation)

## Constitution Check

- **Safety First**: N/A — diagnostic tools are read-only
- **Isolation**: DS analysis scripts still run in gVisor sandbox
- **Observability**: All diagnostic operations traced via MLflow
- **State**: No new state persistence required
