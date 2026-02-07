---
name: feature-checklist
description: Verify all required feature artifacts exist before marking a feature complete. Use when completing a feature, marking tasks as done, finishing implementation, or when the user says a feature is ready or asks to verify completeness.
---

# Feature Checklist

Actively verify that all required artifacts for a feature are in place before it can be marked complete. Based on Feature Delivery Standards in `.specify/memory/constitution.md`.

## Instructions

When triggered, perform these verification steps using file system tools. Report each as **PASS** or **MISSING** with actionable fix instructions.

### Verification Steps

1. **Feature Directory Exists**
   - Check: `specs/001-project-aether/features/NN-<feature-name>/` exists.
   - Contains: `spec.md`, `plan.md`, `tasks.md`.
   - Tool: Use Glob to search for the directory.

2. **Spec File Complete**
   - Check: `spec.md` describes what the feature does and why.
   - Must not be empty or a placeholder.
   - Tool: Read `spec.md` and verify it has substantive content.

3. **Build Plan Saved**
   - Check: `plan.md` contains the build plan used during implementation.
   - This is a historical record — it must reflect what was actually built, not a template.
   - Tool: Read `plan.md` and verify content.

4. **Tasks Tracked**
   - Check: `tasks.md` has implementation tasks with status markers.
   - Completed tasks should reference commit hashes.
   - Tool: Read `tasks.md` and check for completion markers.

5. **Tests Co-committed**
   - Check: Every implementation commit includes its corresponding tests.
   - No commits that are "implementation only" followed by "tests only".
   - Tool: Use `git log --oneline` for the feature branch/commits and spot-check.

6. **Documentation Updated**
   - Check: If the feature changes architecture, data flows, or agent capabilities:
     - `docs/architecture.md` is updated.
   - If project structure or capabilities changed:
     - `specs/001-project-aether/plan.md` is updated.
   - Tool: Read relevant docs and check for references to the new feature.

7. **Commits Are Incremental**
   - Check: No single commit exceeds ~400 lines (except generated code/test fixtures).
   - Each commit is one logical change.
   - Tool: Use `git log --stat` to check commit sizes.

### Output Format

```
## Feature Checklist: <feature-name>

| # | Artifact                  | Status  | Notes                          |
|---|---------------------------|---------|--------------------------------|
| 1 | Feature directory         | PASS    | specs/.../07-feature-name/     |
| 2 | spec.md                   | PASS    | 45 lines, substantive          |
| 3 | plan.md                   | MISSING | File exists but is empty       |
| 4 | tasks.md                  | PASS    | 8/8 tasks complete with hashes |
| 5 | Tests co-committed        | PASS    | Spot-checked 3 commits         |
| 6 | Docs updated              | MISSING | architecture.md not updated    |
| 7 | Incremental commits       | PASS    | Largest commit: 187 lines      |

**Result**: X/7 passed. Feature is [READY / NOT READY] for completion.
**Action items**: [list of missing artifacts to create]
```

### Completion Actions

If all checks pass:
1. Rename feature directory: `NN-feature-name/` to `NN-C-feature-name/`
2. Add `**Completed**: YYYY-MM-DD` header to top of spec.md, plan.md, tasks.md
3. Commit the rename and headers as a single `docs(feature): mark <name> complete` commit
