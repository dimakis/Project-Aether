---
name: feature-branch
description: Start a new feature branch, run CI locally, squash, and open a PR. Use when starting new features, preparing to push, or when the user asks to create a PR.
---

# Feature Branch Workflow

Procedural skill for the feature branch lifecycle. Based on `.specify/memory/constitution.md` (Branching & PR Workflow).

## Instructions

### Starting a New Feature

1. Create branch from develop:
   ```bash
   git checkout -b feat/<name> develop
   ```
2. Confirm branch created:
   ```bash
   git branch --show-current
   ```
3. Proceed with TDD cycle (invoke `tdd-cycle` skill for each task).
4. Commit incrementally on the branch — these are working checkpoints.

### Before Pushing

1. Run CI locally and verify all checks pass:
   ```bash
   make ci-local
   ```
2. If any check fails, fix the issue and re-run until green.
3. Squash all branch commits into a single conventional commit:
   ```bash
   git rebase -i develop
   ```
   - Mark all commits except the first as `squash` (or `s`).
   - Write a single Conventional Commits message for the squashed result.
4. Push the squashed branch:
   ```bash
   git push -u origin HEAD
   ```

### Opening a PR

1. Create PR with `gh`:
   ```bash
   gh pr create --title "<type>(scope): description" --body "$(cat <<'EOF'
   ## Summary
   - <1-3 bullet points>

   ## Test plan
   - [ ] Unit tests added/updated
   - [ ] `make ci-local` passes

   EOF
   )"
   ```
2. The title MUST follow Conventional Commits format.
3. The body MUST follow `.github/PULL_REQUEST_TEMPLATE.md`.
4. Verify PR was created: check URL in output.

### Merging (After Review)

1. Rebase-merge the PR:
   ```bash
   gh pr merge --rebase --delete-branch
   ```
2. The single commit from the branch lands cleanly on the target branch with linear history.

## Anti-patterns

- Pushing a branch without running `make ci-local` first.
- Pushing unsquashed commits (multiple commits in the PR).
- Using squash-merge or merge-commit on the PR instead of rebase-merge.
- Committing directly to main/develop for functional changes.
