# Feature: Custom Dashboard Generation

**Status**: Not Started  
**Priority**: P4  
**User Story**: US4  
**Migrated from**: `specs/001-project-aether/tasks.md` Phase 6

## Goal

Generate and deploy custom Home Assistant dashboards based on user preferences and usage patterns.

## Description

Users should be able to request themed dashboards through the Architect agent. The system generates Lovelace YAML configurations using entity context from the DAL, validates the configuration, and either deploys it directly to HA or exports it for manual import.

## Independent Test

Request a themed dashboard, receive a valid Lovelace configuration, deploy to HA (or export).

## MCP Tools Used

- `list_entities` — find entities for cards
- `domain_summary_tool` — layout planning

## MCP Gap Report (Expected)

- Direct dashboard deployment requires `lovelace/config` WebSocket API
- Dashboard preview requires HA frontend access
- Export mode works without additional MCP features
