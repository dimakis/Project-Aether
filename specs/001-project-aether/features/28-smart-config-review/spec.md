# Feature: Smart Config Review

**Status**: Active
**Priority**: P2
**Depends on**: Feature 26 (YAML Schema Validator), Feature 27 (Semantic Validation), Feature 03 (Intelligent Optimization)

## Goal

Enable the Architect to review existing HA automations, scripts, scenes, and dashboards, collaborate with the DS team to analyze them against entity state, energy patterns, and behavioral data, and produce suggested improvements as YAML diffs presented through the existing proposal flow.

## Description

Users can ask the Architect to review their existing HA configurations. The Architect fetches the current YAML, delegates to the DS team for analysis (energy, behavioral, diagnostic), synthesizes the findings into concrete YAML changes, and creates review proposals. Each review proposal contains both the original and suggested YAML, enabling a diff view in the proposals UI.

Supports both individual review ("review my kitchen automation") and batch review ("review all my automations"). By default, changes are presented as a single combined diff per config. Users can split a review into individual proposals for granular approval.

## Independent Test

User asks the Architect to review an existing automation. The Architect fetches the config, consults the DS team, produces a suggested YAML with improvements, and creates a review proposal visible on the proposals page with a before/after diff view.

## MCP Tools Used

- `get_automation_config` -- fetch automation YAML from discovery DB
- `get_script_config` -- fetch script YAML from discovery DB
- `list_automations` -- list all automations
- `list_entities` -- entity context for DS team
- `get_history` -- historical data for behavioral/energy analysis

## Design Decisions

1. **Extend existing proposal model** rather than creating a new entity. The presence of `original_yaml` distinguishes a review from a new creation. This reuses the full HITL approval lifecycle.

2. **Review session grouping** via `review_session_id` UUID. Batch reviews share a session ID for grouped display in the UI.

3. **Splittable proposals** via `parent_proposal_id` self-referential FK. A combined review can be split into individual proposals for granular approval/deployment.

4. **Tool-delegation pattern** for DS team consultation, consistent with Feature 03/08-C architecture. No new agent communication patterns.

5. **Frontend diff viewer** using `react-diff-viewer-continued` for side-by-side YAML comparison with inline annotations from review notes.
