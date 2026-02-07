# Feature 25: DS Team Architecture & Dual Synthesis

**Status**: Complete
**Completed**: 2026-02-07

## Summary

Restructure the monolithic DataScientistAgent into a team of three specialist analysts with cross-consultation and dual synthesis (programmatic + LLM).

## Changes

### HA Client Rename
- Renamed `src/mcp/` to `src/ha/` across 97 files
- `MCPClient` -> `HAClient`, `MCPError` -> `HAClientError`
- The layer was never an MCP implementation; it's a direct HA REST client

### State Models (`src/graph/state.py`)
- Added `SpecialistFinding`: individual findings with confidence, evidence, cross-references
- Added `TeamAnalysis`: shared analysis state for multi-specialist workflows
- New `AgentRole` values: `ENERGY_ANALYST`, `BEHAVIORAL_ANALYST`, `DIAGNOSTIC_ANALYST`, `DASHBOARD_DESIGNER`
- `AnalysisState` gains `team_analysis` field

### Base Analyst (`src/agents/base_analyst.py`)
Abstract base providing shared infrastructure for all specialists:
- HA client access (lazy singleton)
- LLM access with model context resolution
- Sandbox script execution with data injection
- Cross-consultation: `get_prior_findings()` reads other specialists' findings
- Finding management: `add_finding()` to TeamAnalysis
- Insight persistence to DB

### Energy Analyst (`src/agents/energy_analyst.py`)
- Energy sensor discovery and historical data collection
- LLM-based script generation for energy analysis
- JSON finding extraction from sandbox output
- Cross-consults behavioral/diagnostic findings

### Behavioral Analyst (`src/agents/behavioral_analyst.py`)
Enhanced data sources:
- Script and scene usage frequency tracking
- Trigger source analysis (automation vs human input)
- Automation effectiveness with manual override rates
- Button usage patterns, correlation discovery, gap detection

### Diagnostic Analyst (`src/agents/diagnostic_analyst.py`)
Absorbs `src/diagnostics/` module:
- Entity health (unavailable/stale entities)
- Integration health monitoring
- Config validation
- Error log analysis and pattern matching

### Dual Synthesizer (`src/agents/synthesis.py`)
- **ProgrammaticSynthesizer** (default): deterministic entity grouping, conflict detection, cross-specialist scoring
- **LLMSynthesizer** (on-demand): async LLM-backed with JSON parsing and graceful fallback
- `synthesize()` dispatcher defaults to programmatic
- Both return immutable `TeamAnalysis` copies

### Specialist Tools (`src/tools/specialist_tools.py`)
Architect delegation tools:
- `consult_energy_analyst`, `consult_behavioral_analyst`, `consult_diagnostic_analyst`
- `request_synthesis_review` for LLM second opinion
- All accumulate findings in shared `TeamAnalysis`

### Team Analysis Workflow (`src/graph/workflows.py`)
- `build_team_analysis_graph()`: Energy -> Behavioral -> Diagnostic -> Synthesize
- `TeamAnalysisWorkflow` convenience class for programmatic use
- Registered as "team_analysis" in `WORKFLOW_REGISTRY`

## Test Coverage

- 16 tests: State models (SpecialistFinding, TeamAnalysis, AgentRole)
- 12 tests: Dual synthesizer (programmatic + LLM)
- 11 tests: Base analyst (init, HA, sandbox, cross-consult, persistence)
- 10 tests: Energy analyst
- 9 tests: Behavioral analyst
- 8 tests: Diagnostic analyst
- 6 tests: Specialist tools
- 3 tests: Team analysis workflow
- **Total: 75 new tests**
