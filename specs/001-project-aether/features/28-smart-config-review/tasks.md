# Tasks: Smart Config Review

## Backend

- [ ] T2800: Extend AutomationProposal model with review fields + Alembic migration
- [ ] T2801: Add ReviewState model to src/graph/state.py
- [ ] T2802: Implement review workflow nodes (resolve_targets, fetch_configs, gather_context, consult_ds_team, architect_synthesize, create_review_proposals)
- [ ] T2803: Add build_review_graph() to src/graph/workflows.py
- [ ] T2804: Create review_config tool + wire into Architect
- [ ] T2805: Extend proposal API schemas with review fields
- [ ] T2806: Add review_session_id filter to GET /proposals
- [ ] T2807: Add POST /proposals/{id}/split endpoint

## Frontend

- [ ] T2808: Add react-diff-viewer-continued dependency
- [ ] T2809: Create YamlDiffViewer component
- [ ] T2810: Enhance ProposalDetail with diff view + review notes
- [ ] T2811: Add review badge to ProposalCard
- [ ] T2812: Extend TypeScript types for review fields
