# Feature: Diagnostics API & CLI

**Status**: Not Started  
**Priority**: P4  
**User Story**: US8 (continued)  
**Depends on**: Feature 06 (HA Diagnostics & Troubleshooting - Core)

## Goal

Expose the diagnostics intelligence layer (built in Feature 06) via REST API endpoints and CLI commands, enabling programmatic access to error analysis, entity health, integration status, and troubleshooting workflows.

## Description

Feature 06 builds the diagnostic brain (log parser, error patterns, entity/integration health, config validator) and agent tools. This feature adds the HTTP and CLI surface area so users and external systems can consume diagnostics without going through the conversational agent.

### API Endpoints

- `GET /diagnostics/errors` -- Recent errors with structured analysis
- `GET /diagnostics/errors/{integration}` -- Errors filtered by integration
- `POST /diagnostics/config-check` -- Validate HA configuration
- `GET /diagnostics/entities/unavailable` -- List unavailable entities with diagnostics
- `GET /diagnostics/entities/{id}` -- Single entity health check
- `GET /diagnostics/integrations` -- All integration health statuses
- `GET /diagnostics/integrations/{domain}` -- Single integration health
- `POST /diagnostics/troubleshoot` -- Run guided troubleshooting

### CLI Commands

- `aether diagnose errors [--integration NAME]` -- Show/filter recent errors
- `aether diagnose config` -- Validate configuration
- `aether diagnose entity <entity_id>` -- Entity health check
- `aether diagnose integration <domain>` -- Integration health
- `aether diagnose --full` -- Complete health report
- `aether health` -- Quick system health summary
- `aether health integrations` -- Integration status table
- `aether health entities` -- Entity availability summary

## Acceptance Criteria

1. **Given** the diagnostics module is available, **When** calling the API, **Then** it returns structured JSON responses
2. **Given** the CLI is installed, **When** running `aether diagnose`, **Then** it displays formatted diagnostic output
3. **Given** any diagnostic endpoint, **When** called, **Then** it is read-only and does not modify HA state

## HITL Requirements

- All endpoints are read-only, no approval needed
- Any fix-execution endpoints (future) would require HITL approval

## Related Features

- **Feature 06**: Provides the diagnostics module this feature exposes
- **US1 Entity Discovery**: Entity data used by diagnostics
