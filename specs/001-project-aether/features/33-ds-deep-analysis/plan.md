# Implementation Plan: DS Deep Analysis & Agent Collaboration

**Feature**: [spec.md](./spec.md)  
**Date**: 2026-02-13

## Summary

Enable configurable deep EDA in the DS agent sandbox, capture chart/data artifacts securely, add parallel vs teamwork execution strategies, persist inter-agent communication, introduce analysis reports, and enhance the UI with Recharts visualizations.

## Architecture

See the full architecture diagram in the [cursor plan](../../../.cursor/plans/ds_deep_analysis_enhancement_bee8adc8.plan.md).

## Phase 1: Sandbox Artifact Capture

### Security Gates
- `sandbox_artifacts_enabled` global setting in `src/settings.py` (default: false)
- `artifacts_enabled` per-policy flag in `src/sandbox/policies.py` (default: false)
- Effective = global AND per-policy

### Output Mount
- In `SandboxRunner.run()`: create temp dir, mount as `/workspace/output/:rw` only when effective=true
- After execution: scan, validate, collect artifacts

### Egress Validator (`src/sandbox/artifact_validator.py`)
- Extension allowlist: .png, .jpg, .jpeg, .svg, .csv, .json
- Magic-byte verification (file header must match claimed type)
- Per-file size limit (10MB), total limit (50MB), max count (20)
- Symlink rejection, filename sanitization, dotfile rejection

### Artifact Storage
- `src/storage/artifact_store.py`: persist to `data/artifacts/{report_id}/`
- `ArtifactMeta` on `SandboxResult` for downstream processing

### Serving API
- `GET /reports/{report_id}/artifacts/{filename}` with security headers

## Phase 2: Analysis Profiles & Execution Strategy

### Enums
- `AnalysisDepth`: quick, standard, deep in `src/graph/state.py`
- `ExecutionStrategy`: parallel, teamwork in `src/graph/state.py`

### Configurable Timeouts
- `sandbox_timeout_quick/standard/deep` settings (env-configurable)
- `sandbox_memory_quick/standard/deep` settings
- Per-request `timeout_seconds` override (clamped)

### Execution Strategy
- In `consult_data_science_team`: branch on `strategy` parameter
- Parallel: existing `asyncio.gather` path
- Teamwork: sequential execution, cross-consult reads prior findings, discussion round, LLM synthesis

### Prompts
- `eda_depth_quick.md`, `eda_depth_standard.md`, `eda_depth_deep.md`
- `strategy_teamwork.md` (cross-consultation instructions)
- Update `data_scientist_system.md` with conditional artifact instructions

### API/Schedule Wiring
- `depth`, `strategy`, `timeout_seconds` on API endpoints and schedule model
- `get_policy_for_depth()` resolver in policies.py

## Phase 3: Agent Communication Log

- `ReportCommunication` DB entity + migration
- `communication_log` on `ExecutionContext`
- `emit_communication()` helper
- Instrument BaseAnalyst lifecycle and cross-consultation

## Phase 4: Analysis Reports

- `AnalysisReport` DB entity + migration
- `ReportRepository` CRUD
- API routes: list, get (with insights + artifacts + comms), create, delete
- Workflow integration: create report at start, finalize at end

## Phase 5: Enhanced UI

- `/reports` page: list + detail with chart gallery, agent timeline, Recharts
- Enhanced `/insights`: replace CSS bars with Recharts
- API hooks and routing

## Files to Create

| File | Purpose |
|------|---------|
| `src/sandbox/artifact_validator.py` | Egress security |
| `src/storage/entities/analysis_report.py` | Report model |
| `src/storage/entities/report_communication.py` | Communication model |
| `src/storage/artifact_store.py` | Artifact persistence |
| `src/dal/report_repository.py` | Report data access |
| `src/api/routes/reports.py` | Report API |
| `src/agents/prompts/eda_depth_quick.md` | Quick depth prompt |
| `src/agents/prompts/eda_depth_standard.md` | Standard depth prompt |
| `src/agents/prompts/eda_depth_deep.md` | Deep depth prompt |
| `src/agents/prompts/strategy_teamwork.md` | Teamwork strategy prompt |
| `migrations/versions/0xx_analysis_reports.py` | DB migration |
| `ui/src/pages/reports/index.tsx` | Reports list page |
| `ui/src/pages/reports/ReportDetail.tsx` | Report detail page |
| `ui/src/pages/reports/AgentTimeline.tsx` | Communication timeline |
| `ui/src/api/hooks/reports.ts` | Report API hooks |
| `ui/src/api/client/reports.ts` | Report API client |

## Files to Modify

| File | Change |
|------|--------|
| `src/settings.py` | `sandbox_artifacts_enabled`, depth timeout/memory settings |
| `src/sandbox/runner.py` | Gated output mount, artifact collection |
| `src/sandbox/policies.py` | `artifacts_enabled`, `get_policy_for_depth()` |
| `src/graph/state.py` | `AnalysisDepth`, `ExecutionStrategy` enums |
| `src/tools/specialist_tools.py` | Parallel vs teamwork paths, strategy/depth params |
| `src/agents/base_analyst.py` | Communication logging, depth-aware prompts |
| `src/agents/execution_context.py` | Communication log |
| `src/agents/prompts/data_scientist_system.md` | Conditional artifact instructions |
| `src/graph/workflows/team_analysis.py` | Report creation/finalization |
| `src/api/main.py` | Register report routes |
| `ui/src/pages/insights/EvidencePanel.tsx` | Recharts integration |
| `ui/src/App.tsx` | Add /reports route |
