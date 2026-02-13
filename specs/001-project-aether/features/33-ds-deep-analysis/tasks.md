# Tasks: DS Deep Analysis & Agent Collaboration

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1: Sandbox Artifact Capture

### Security Gates (test-first)

- [ ] T3301 Add `sandbox_artifacts_enabled` setting to src/settings.py (default: false)
- [ ] T3302 Add `artifacts_enabled` field to `SandboxPolicy` in src/sandbox/policies.py (default: false)
- [ ] T3303 Implement gate logic: effective = global AND per-policy

### Egress Validator (test-first)

- [ ] T3304 Create `ArtifactEgressPolicy` model in src/sandbox/artifact_validator.py
- [ ] T3305 Implement extension allowlist validation
- [ ] T3306 Implement magic-byte verification (.png, .jpg, .svg, .csv, .json signatures)
- [ ] T3307 Implement size limits (per-file, total, count)
- [ ] T3308 Implement symlink rejection
- [ ] T3309 Implement filename sanitization (traversal, null bytes, dotfiles, pattern)
- [ ] T3310 Implement `validate_artifacts()` orchestrator function

### Sandbox Output Mount (test-first)

- [ ] T3311 Add `ArtifactMeta` model to src/sandbox/runner.py
- [ ] T3312 Extend `SandboxResult` with `artifacts` and `artifacts_rejected` fields
- [ ] T3313 Create temp output dir and mount as `/workspace/output/:rw` in `_build_command()` (gated)
- [ ] T3314 Collect and validate artifacts after execution in `run()`
- [ ] T3315 Handle unsandboxed mode artifact collection in `_run_unsandboxed()`

### Artifact Storage (test-first)

- [ ] T3316 Create `ArtifactStore` in src/storage/artifact_store.py (persist, retrieve, delete)
- [ ] T3317 Implement content-type cross-check and path sanitization

### Artifact Serving API (test-first)

- [ ] T3318 Create `GET /reports/{report_id}/artifacts/{filename}` route
- [ ] T3319 Add security headers (nosniff, CSP sandbox, Content-Disposition)

---

## Phase 2: Analysis Profiles & Execution Strategy

### Enums and Settings (test-first)

- [ ] T3320 Add `AnalysisDepth` and `ExecutionStrategy` enums to src/graph/state.py
- [ ] T3321 Add `depth` and `strategy` fields to `AnalysisState`
- [ ] T3322 Add `sandbox_timeout_*` and `sandbox_memory_*` settings to src/settings.py
- [ ] T3323 Implement `get_policy_for_depth()` in src/sandbox/policies.py

### Execution Strategy (test-first)

- [ ] T3324 Implement teamwork sequential execution path in src/tools/specialist_tools.py
- [ ] T3325 Implement discussion round (post-specialist cross-reference pass)
- [ ] T3326 Wire LLMSynthesizer for teamwork mode (vs ProgrammaticSynthesizer for parallel)
- [ ] T3327 Add `depth`, `strategy`, `timeout_seconds` parameters to `consult_data_science_team`

### Prompts

- [ ] T3328 Create `eda_depth_quick.md` prompt fragment
- [ ] T3329 Create `eda_depth_standard.md` prompt fragment
- [ ] T3330 Create `eda_depth_deep.md` prompt fragment
- [ ] T3331 Create `strategy_teamwork.md` prompt fragment
- [ ] T3332 Update `data_scientist_system.md` with conditional artifact output instructions
- [ ] T3333 Wire depth/strategy prompt selection in `BaseAnalyst._build_analysis_prompt()`

### API/Schedule Wiring (test-first)

- [ ] T3334 Add `depth`, `strategy`, `timeout_seconds` to `POST /insights/analyze`
- [ ] T3335 Add `depth`, `strategy`, `timeout_seconds` columns to `insight_schedules` (migration)
- [ ] T3336 Wire depth/strategy through scheduler to analysis workflow

---

## Phase 3: Agent Communication Log

- [ ] T3337 Create `ReportCommunication` DB entity in src/storage/entities/report_communication.py
- [ ] T3338 Create Alembic migration for report_communications table
- [ ] T3339 Add `communication_log` to `ExecutionContext` and `emit_communication()` helper
- [ ] T3340 Instrument BaseAnalyst: log start/complete, cross-consultation reads, finding submissions
- [ ] T3341 Instrument synthesis step: log synthesizer reasoning

---

## Phase 4: Analysis Reports

- [ ] T3342 Create `AnalysisReport` DB entity in src/storage/entities/analysis_report.py
- [ ] T3343 Create Alembic migration for analysis_reports table
- [ ] T3344 Create `ReportRepository` with CRUD + list with filters in src/dal/report_repository.py
- [ ] T3345 Create report API routes (list, get, create, delete) in src/api/routes/reports.py
- [ ] T3346 Wire workflow: create report at start, link insights/artifacts, persist comms, finalize

---

## Phase 5: Enhanced UI

- [ ] T3347 Create Reports list page in ui/src/pages/reports/index.tsx
- [ ] T3348 Create Report detail page with chart gallery in ui/src/pages/reports/ReportDetail.tsx
- [ ] T3349 Create Agent conversation timeline in ui/src/pages/reports/AgentTimeline.tsx
- [ ] T3350 Replace CSS-based charts with Recharts in ui/src/pages/insights/EvidencePanel.tsx
- [ ] T3351 Add report API hooks and client (ui/src/api/hooks/reports.ts, ui/src/api/client/reports.ts)
- [ ] T3352 Add /reports route and sidebar navigation
