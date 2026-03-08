# Tasks: DS Deep Analysis & Agent Collaboration

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1: Sandbox Artifact Capture

### Security Gates (test-first)

- [x] T3301 Add `sandbox_artifacts_enabled` setting to src/settings.py (default: false)
- [x] T3302 Add `artifacts_enabled` field to `SandboxPolicy` in src/sandbox/policies.py (default: false)
- [x] T3303 Implement gate logic: effective = global AND per-policy

### Egress Validator (test-first)

- [x] T3304 Create `ArtifactEgressPolicy` model in src/sandbox/artifact_validator.py
- [x] T3305 Implement extension allowlist validation
- [x] T3306 Implement magic-byte verification (.png, .jpg, .svg, .csv, .json signatures)
- [x] T3307 Implement size limits (per-file, total, count)
- [x] T3308 Implement symlink rejection
- [x] T3309 Implement filename sanitization (traversal, null bytes, dotfiles, pattern)
- [x] T3310 Implement `validate_artifacts()` orchestrator function

### Sandbox Output Mount (test-first)

- [x] T3311 Add `ArtifactMeta` model to src/sandbox/artifact_validator.py
- [x] T3312 Extend `SandboxResult` with `artifacts` and `artifacts_rejected` fields
- [x] T3313 Create temp output dir and mount as `/workspace/output/:rw` in `_build_command()` (gated)
- [x] T3314 Collect and validate artifacts after execution in `run()`
- [x] T3315 Handle unsandboxed mode artifact collection in `_run_unsandboxed()`

### Artifact Storage (test-first)

- [x] T3316 Create `ArtifactStore` in src/storage/artifact_store.py (persist, retrieve, delete)
- [x] T3317 Implement content-type cross-check and path sanitization

### Artifact Serving API (test-first)

- [x] T3318 Create `GET /reports/{report_id}/artifacts/{filename}` route
- [x] T3319 Add security headers (nosniff, CSP sandbox, Content-Disposition)

---

## Phase 2: Analysis Profiles & Execution Strategy

### Enums and Settings (test-first)

- [x] T3320 Add `AnalysisDepth` and `ExecutionStrategy` enums to src/graph/state/enums.py
- [x] T3321 Add `depth` and `strategy` fields to `AnalysisState`
- [x] T3322 Add `sandbox_timeout_*` and `sandbox_memory_*` settings to src/settings.py
- [x] T3323 Implement `get_policy_for_depth()` in src/sandbox/policies.py

### Execution Strategy (test-first)

- [x] T3324 Implement teamwork sequential execution path in src/tools/specialist_tools.py
- [x] T3325 Implement discussion round (post-specialist cross-reference pass)
- [x] T3326 Wire LLMSynthesizer for teamwork mode (vs ProgrammaticSynthesizer for parallel)
- [x] T3327 Add `depth`, `strategy`, `timeout_seconds` parameters to `consult_data_science_team`

### Prompts

- [x] T3328 Create `eda_depth_quick.md` prompt fragment
- [x] T3329 Create `eda_depth_standard.md` prompt fragment
- [x] T3330 Create `eda_depth_deep.md` prompt fragment
- [x] T3331 Create `strategy_teamwork.md` prompt fragment
- [x] T3332 Update `data_scientist_system.md` with conditional artifact output instructions
- [x] T3333 Wire depth/strategy prompt selection in `BaseAnalyst._build_analysis_prompt()`

### API/Schedule Wiring (test-first)

- [x] T3334 Add `depth`, `strategy`, `timeout_seconds` to `POST /insights/analyze`
- [x] T3335 Add `depth`, `strategy`, `timeout_seconds` columns to `insight_schedules` (migration 024)
- [x] T3336 Wire depth/strategy through scheduler to analysis workflow

---

## Phase 3: Agent Communication Log

- [x] T3337 Communication log stored as JSONB on `AnalysisReport` (embedded, not separate entity)
- [x] T3338 Alembic migration 023_analysis_reports includes communication_log column
- [x] T3339 Add `communication_log` tracking in execution context
- [x] T3340 Instrument BaseAnalyst: log start/complete, cross-consultation reads, finding submissions
- [x] T3341 Instrument synthesis step: log synthesizer reasoning

---

## Phase 4: Analysis Reports

- [x] T3342 Create `AnalysisReport` DB entity in src/storage/entities/analysis_report.py
- [x] T3343 Create Alembic migration 023_analysis_reports
- [x] T3344 Create `AnalysisReportRepository` with CRUD + list with filters in src/dal/analysis_reports.py
- [x] T3345 Create report API routes (list, get, create, delete) in src/api/routes/reports.py
- [x] T3346 Wire workflow: create report at start, link insights/artifacts, persist comms, finalize

---

## Phase 5: Enhanced UI

- [x] T3347 Create Reports list page in ui/src/pages/reports/index.tsx
- [x] T3348 Create Report detail page with chart gallery in ui/src/pages/reports/ReportDetail.tsx
- [x] T3349 Create Agent conversation timeline in ui/src/pages/reports/AgentTimeline.tsx
- [x] T3350 Replace CSS-based charts with Recharts in ui/src/pages/insights/EvidencePanel.tsx
- [x] T3351 Add report API hooks and client (ui/src/api/hooks/reports.ts, ui/src/api/client/reports.ts)
- [x] T3352 Add /reports route and sidebar navigation
