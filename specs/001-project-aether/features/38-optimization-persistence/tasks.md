# Tasks: Optimization Persistence

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Phase 1 -- Entities & Migration

- [ ] T3801 Create `OptimizationJob` entity in `src/storage/entities/optimization_job.py` -- UUID PK, status, analysis_types (JSONB), hours_analyzed, insight_count, suggestion_count, recommendations (JSONB), error, started_at, completed_at, timestamps
- [ ] T3802 [P] Create `AutomationSuggestion` entity in `src/storage/entities/automation_suggestion.py` -- UUID PK, job_id (FK), pattern, entities (JSONB), proposed_trigger, proposed_action, confidence, source_insight_type, status, timestamps
- [ ] T3803 Export both entities from `src/storage/entities/__init__.py`
- [ ] T3804 Create migration `033_optimization_tables.py` -- both tables with FK constraint

**Checkpoint**: Schema ready

---

## Phase 2 -- Repository

- [ ] T3805 Create `OptimizationJobRepository` in `src/dal/optimization.py` -- CRUD, `list_all(status_filter)`, `reconcile_stale_jobs()`
- [ ] T3806 [P] Create `AutomationSuggestionRepository` in `src/dal/optimization.py` -- CRUD, `list_by_job(job_id)`, `list_all(status_filter)`, `update_status()`
- [ ] T3807 [P] Unit tests in `tests/unit/dal/test_optimization_repository.py` -- CRUD, filtering, reconciliation
- [ ] T3808 Export repositories from `src/dal/__init__.py`

**Checkpoint**: Data layer complete and tested

---

## Phase 3 -- Route Migration

- [ ] T3809 Refactor `src/api/routes/optimization.py` -- replace `_optimization_jobs` dict with `OptimizationJobRepository`, replace `_suggestions` dict with `AutomationSuggestionRepository`
- [ ] T3810 Update `_run_optimization_background()` to persist job status and suggestions to DB
- [ ] T3811 Add startup reconciliation in `src/api/main.py` -- call `repo.reconcile_stale_jobs()` in lifespan
- [ ] T3812 Add `GET /optimize/jobs` endpoint for job history list with optional status filter
- [ ] T3813 Update `GET /optimize/suggestions/list` to support optional `?job_id=` filter

**Checkpoint**: Backend fully persistent, API contract preserved

---

## Phase 4 -- Frontend Polish (US3)

- [ ] T3814 Add `jobHistory()` client function in `ui/src/api/client/optimization.ts`
- [ ] T3815 Add `useJobHistory()` React Query hook in `ui/src/api/hooks/optimization.ts`
- [ ] T3816 Add job history section to `ui/src/pages/optimization/index.tsx` -- collapsible list, status badges, date, counts
- [ ] T3817 Add status filter dropdown for job history

**Checkpoint**: UI shows persistent job history

---

## Phase 5 -- Polish

- [ ] T3818 Verify existing optimization tests pass (no API contract breaks)
- [ ] T3819 Integration test: create job -> complete -> restart mock -> verify persisted

---

`[P]` = Can run in parallel (different files, no dependencies)
