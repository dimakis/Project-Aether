# Implementation Plan: Optimization Persistence

**Feature**: [spec.md](./spec.md)
**Status**: Planned
**Date**: 2026-02-27

## Summary

Persist optimization jobs and automation suggestions to PostgreSQL, replacing the current in-memory dicts. Add job reconciliation on startup, job history in the UI, and suggestion filtering by job.

## Technical Context

**Language/Version**: Python 3.11 + TypeScript (React)
**Primary Dependencies**: FastAPI, SQLAlchemy (async), Alembic, React, React Query
**Storage**: PostgreSQL (2 new tables)
**Testing**: pytest (backend), vitest (frontend)
**Target Platform**: Linux server (Docker/K8s)

## Constitution Check

- **Safety First**: No HA mutations. Optimization suggestions still go through HITL approval via existing proposal system.
- **Isolation**: No script execution changes.
- **Observability**: Job lifecycle logged. No new MLflow traces needed.
- **State**: DB-backed (Postgres). Existing in-memory dicts replaced.

## Architecture

```
POST /optimize
    |-- Create OptimizationJob (status: pending) in DB
    |-- Start background task
    v
_run_optimization_background()
    |-- Update job status: running
    |-- Run optimization workflow
    |-- Create AutomationSuggestion rows in DB
    |-- Update job status: completed/failed
    v
GET /optimize/{job_id}
    |-- Query OptimizationJobRepository
    v
GET /optimize/suggestions/list
    |-- Query AutomationSuggestionRepository
    |-- Optional filter: ?job_id=...
```

## Key Design Decisions

- **Mirror existing schemas**: DB entities match current in-memory `OptimizationResult` and `AutomationSuggestionResponse` shapes. API contract unchanged.
- **Startup reconciliation**: On app start, find jobs with status "running" and mark as "failed" with error "Server restarted during execution."
- **Background task pattern**: Same `asyncio.create_task` pattern, but writes to DB instead of dicts.
- **UI-only job history**: Minimal frontend change -- add a collapsible history section below the active job card.

## Files to Create

- `src/storage/entities/optimization_job.py` -- OptimizationJob entity
- `src/storage/entities/automation_suggestion.py` -- AutomationSuggestion entity
- `src/dal/optimization.py` -- OptimizationJobRepository, AutomationSuggestionRepository
- `alembic/versions/033_optimization_tables.py` -- Create tables
- `tests/unit/dal/test_optimization_repository.py` -- Repository tests

## Files to Modify

- `src/api/routes/optimization.py` -- Replace in-memory dicts with DB repositories
- `src/storage/entities/__init__.py` -- Export new entities
- `src/dal/__init__.py` -- Export new repositories
- `src/api/main.py` -- Add startup reconciliation for stale "running" jobs
- `ui/src/pages/optimization/index.tsx` -- Add job history section
- `ui/src/api/hooks/optimization.ts` -- Add `useJobHistory()` hook
- `ui/src/api/client/optimization.ts` -- Add `jobHistory()` client function
