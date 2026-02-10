# Implementation Plan: Smart Config Review

**Feature**: [spec.md](./spec.md)
**Date**: 2026-02-09

## Summary

Add a reactive config review workflow where the Architect + DS team analyze existing HA configs and produce improvement suggestions as YAML diffs in the proposal UI.

## Technical Approach

### Data Model (extend existing)

Extend `AutomationProposal` in `src/storage/entities/automation_proposal.py`:
- `original_yaml: Text (nullable)` -- before state
- `review_notes: JSONB (nullable)` -- structured change list
- `review_session_id: UUID (nullable, indexed)` -- batch grouping
- `parent_proposal_id: UUID (nullable, FK self-ref)` -- split tracking

### Review Workflow (`build_review_graph`)

New LangGraph workflow in `src/graph/workflows.py` with state model `ReviewState` in `src/graph/state.py`:

```
START -> resolve_targets -> fetch_configs -> gather_context -> consult_ds_team -> architect_synthesize -> create_review_proposals -> END
```

Nodes implemented in `src/graph/nodes/review.py`.

### Architect Tool

New `review_config` tool in `src/tools/review_tools.py`, added to Architect's tool list.

### API Extensions

Extend `src/api/routes/proposals.py`:
- `GET /proposals/{id}` returns `original_yaml` + `review_notes` when present
- `GET /proposals?review_session_id=X` for batch filtering
- `POST /proposals/{id}/split` for splitting combined reviews

### Frontend

- `ui/src/components/ui/yaml-diff-viewer.tsx` -- diff component
- Enhanced `ProposalDetail` with diff view when `original_yaml` present
- Review badge on `ProposalCard`

## Constitution Check

- **Safety**: Review suggestions go through existing HITL approval
- **Isolation**: DS team scripts run in gVisor sandbox
- **Observability**: Review workflow traced via MLflow
- **State**: LangGraph + PostgreSQL checkpointing
- **Reliability**: TDD for all components; mock DS findings in tests
- **Security**: No new auth surface; reuses proposal permissions
