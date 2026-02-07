**Completed**: 2026-02-07

# Feature: Home Assistant Diagnostics & Troubleshooting

**Status**: Complete  
**Priority**: P4  
**User Story**: US8  
**Depends on**: US1 (Entity Discovery)

## Goal

Enable agents to diagnose Home Assistant issues, validate configurations, access logs, and troubleshoot problems - acting as an intelligent support assistant.

## Description

Home Assistant can be complex to troubleshoot. This feature gives agents access to diagnostic information and the ability to help users identify and resolve issues:

- **Error Log Access**: Read HA error logs, parse for patterns
- **Config Validation**: Check configuration before restart
- **Integration Status**: Monitor integration health
- **Entity Diagnostics**: Identify unavailable/problematic entities
- **System Health**: Check overall HA system status
- **Guided Troubleshooting**: Walk users through common fixes

## Example Use Cases

### 1. Error Log Analysis
**User**: "My HA has been acting weird, can you check the logs?"
**Agent**:
- Fetches recent error log entries
- Parses and categorizes errors by integration
- Identifies recurring patterns
- Suggests fixes for common errors
- "I found 23 errors related to your Zigbee integration. The most common is 'device not responding' for sensor.bathroom_motion. This usually means the device needs a new battery or has moved out of range."

### 2. Pre-Restart Validation
**User**: "I made some changes, is it safe to restart?"
**Agent**:
- Runs configuration check via API
- Reports any errors or warnings
- Identifies which files have issues
- "Your configuration has 1 error in automations.yaml line 45: invalid trigger type 'stat' - did you mean 'state'?"

### 3. Unavailable Entity Diagnosis
**User**: "Why are some of my devices showing unavailable?"
**Agent**:
- Lists all entities with state "unavailable"
- Groups by integration/device type
- Checks history for when they became unavailable
- Correlates with any recent changes
- "5 Zigbee devices became unavailable 2 hours ago, right after your ZHA coordinator restarted. Try repairing the devices."

### 4. Integration Health Check
**User**: "Is everything working properly?"
**Agent**:
- Checks all integration statuses
- Identifies integrations with errors
- Monitors connection states
- Reports latency issues
- "All 12 integrations are healthy. Your MQTT broker is responding in 3ms. One issue: your Nest integration shows 'reauthentication required'."

### 5. Automation Debugging
**User**: "My automation isn't working, can you help?"
**Agent**:
- Checks if automation is enabled
- Reviews trigger conditions
- Checks if entities exist and are available
- Reviews recent trigger history
- Traces through conditions to find failure point
- "Your automation 'Motion Lights' hasn't triggered because binary_sensor.hallway_motion has been 'unavailable' for 3 days."

### 6. Performance Analysis
**User**: "HA seems slow lately"
**Agent**:
- Checks recorder database size
- Reviews entity count and history retention
- Identifies integrations with high polling rates
- Suggests optimizations
- "Your recorder database is 4.2GB. You have 847 entities recording every 5 seconds. Consider excluding high-frequency sensors from history."

## Independent Test

Agent can fetch error logs, run config check, identify unavailable entities, and provide actionable troubleshooting guidance.

## REST API Endpoints Required

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/error_log` | GET | Get error log contents |
| `/api/config/core/check_config` | POST | Validate configuration |
| `/api/config/config_entries` | GET | List integrations |
| `/api/config/config_entries/{id}/diagnostics` | GET | Integration diagnostics |
| `/api/services` | GET | List available services |
| `/api/events` | GET | List event types |
| `/api/template` | POST | Render templates for debugging |
| `/api/states` | GET | Check for unavailable entities |

## Data Structures

### ErrorLogEntry
```python
ErrorLogEntry:
  timestamp: datetime
  level: str           # ERROR, WARNING, INFO
  logger: str          # Integration/component name
  message: str
  exception: str | None
```

### ConfigCheckResult
```python
ConfigCheckResult:
  result: str          # valid, invalid
  errors: list[str]
  warnings: list[str]
```

### IntegrationHealth
```python
IntegrationHealth:
  entry_id: str
  domain: str
  title: str
  state: str           # loaded, setup_error, not_loaded
  reason: str | None
  disabled_by: str | None
```

### EntityDiagnostic
```python
EntityDiagnostic:
  entity_id: str
  state: str
  available: bool
  last_changed: datetime
  last_updated: datetime
  integration: str
  issues: list[str]
```

## Acceptance Criteria

1. **Given** errors in HA log, **When** agent analyzes logs, **Then** it categorizes by integration and suggests fixes
2. **Given** invalid configuration, **When** agent checks config, **Then** it identifies exact error location
3. **Given** unavailable entities, **When** agent diagnoses, **Then** it identifies root cause
4. **Given** any troubleshooting request, **When** agent responds, **Then** guidance is actionable and accurate
5. **Given** diagnostic operations, **When** executed, **Then** they don't modify system state (read-only)

## HITL Requirements

- Diagnostics are read-only, no approval needed
- Suggested fixes require approval before execution
- Restart/reload operations require explicit confirmation

## Agent Capabilities

The agent should be able to:
- Parse and understand HA error messages
- Correlate errors with entity states
- Suggest common fixes for known error patterns
- Guide users through debugging steps
- Know when to recommend manual intervention
- Escalate to HA community/docs for unknown issues

## Related Features

- **US1 Entity Discovery**: Uses entity data for diagnostics
- **US5 Intelligent Optimization**: Can detect performance issues
- **Registry Management**: Can identify orphaned entities
