# Tasks: Smart Config Review

## Backend

- [x] T2800: Extend AutomationProposal model with review fields + Alembic migration
- [x] T2801: Add ReviewState model to src/graph/state.py
- [x] T2802: Implement review workflow nodes (resolve_targets, fetch_configs, gather_context, consult_ds_team, architect_synthesize, create_review_proposals)
- [x] T2803: Add build_review_graph() to src/graph/workflows.py
- [x] T2804: Create review_config tool + wire into Architect
- [x] T2805: Extend proposal API schemas with review fields
- [x] T2806: Add review_session_id filter to GET /proposals
- [x] T2807: Add POST /proposals/{id}/split endpoint

## Frontend

- [x] T2808: Add react-diff-viewer-continued dependency
- [x] T2809: Create YamlDiffViewer component
- [x] T2810: Enhance ProposalDetail with diff view + review notes
- [x] T2811: Add review badge to ProposalCard
- [x] T2812: Extend TypeScript types for review fields
