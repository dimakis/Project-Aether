# Feature: DS Deep Analysis & Agent Collaboration

**Status**: In Progress  
**Priority**: P1  
**Depends on**: 25-ds-team-architecture, 10-scheduled-event-insights

## Goal

Enable the DS agent team to perform configurable deep exploratory data analysis with pandas, capture sandbox-generated artifacts (charts, CSVs), support parallel vs teamwork execution strategies for inter-agent collaboration, and surface rich analysis reports in the UI.

## Problem Statement

The DS agents run pandas/numpy/matplotlib scripts in gVisor-sandboxed containers, but:

1. Charts saved to `/workspace/output/` are never captured (directory not mounted).
2. All analyses use the same prompts and sandbox limits -- no way to request "quick scan" vs "deep EDA".
3. Specialists always run in parallel -- they cannot see each other's findings or collaborate.
4. Inter-agent communication is transient (progress queue only) -- not persisted.
5. Insights are individual records with no grouping into coherent reports with charts.
6. The Insights UI uses CSS-based bars instead of proper charting.

## User Experience

1. User asks: "Run a deep energy analysis for the last 7 days with teamwork"
2. Architect delegates to DS team with `depth=deep`, `strategy=teamwork`
3. Energy Analyst runs first, produces pandas EDA with charts saved to sandbox output
4. Behavioral Analyst runs next, reads Energy findings, cross-references with usage patterns
5. Diagnostic Analyst runs last, checks for data quality issues flagged by prior analysts
6. Discussion round: each specialist reviews full findings, adds cross-references
7. LLM Synthesizer produces a narrative report
8. Report is created: insights + chart artifacts + agent conversation log
9. User views the report on `/reports/{id}` with chart gallery, data tables, agent timeline
10. User can schedule this as a weekly deep analysis

## Core Capabilities

### Sandbox Artifact Capture (with Security Gates)
- Global `sandbox_artifacts_enabled` setting (default: false, defense-in-depth)
- Per-request `artifacts_enabled` flag on `SandboxPolicy`
- Writable `/workspace/output/` mount (only when both gates are true)
- Artifact egress validator: extension allowlist, magic-byte verification, size/count limits, symlink rejection, filename sanitization
- Artifact persistence to `data/artifacts/{report_id}/`
- Secure serving API with nosniff headers

### Configurable Analysis Depth
- `AnalysisDepth` enum: quick, standard, deep
- Per-depth settings: `sandbox_timeout_*`, `sandbox_memory_*` (configurable via env)
- Per-request timeout override (clamped to depth ceiling)
- Depth-specific prompt fragments for EDA scope

### Execution Strategy
- `ExecutionStrategy` enum: parallel, teamwork
- Parallel: current behavior (asyncio.gather), fast
- Teamwork: sequential execution, cross-consultation, discussion round, LLM synthesis
- Teamwork prompt fragment encouraging cross-referencing and collaboration

### Analysis Reports
- `AnalysisReport` DB entity grouping insights + artifacts + communication log
- Full CRUD API with filters
- Linked to schedules and conversations

### Agent Communication Log
- `ReportCommunication` DB entity capturing inter-agent messages
- Types: finding, question, cross_reference, synthesis, agreement, disagreement
- Persisted per report for UI rendering

### Enhanced UI
- New `/reports` page with report list and detail view
- Report detail: executive summary, chart gallery, Recharts data viz, agent conversation timeline
- Enhanced `/insights` with Recharts replacing CSS-based charts

## Constitution Check

- **Safety First**: Artifact output is default-deny. Two independent gates required.
- **Isolation**: Scripts still run in gVisor sandbox. Output dir is the only writable mount. Artifact egress is validated before leaving sandbox boundary.
- **Observability**: Reports link to MLflow traces. Communication log provides full audit trail.
- **State**: Reports, communications, artifact metadata in PostgreSQL.
- **Security**: Magic-byte validation prevents polyglot attacks. Filename sanitization prevents path traversal. Artifact serving sets CSP sandbox headers.
