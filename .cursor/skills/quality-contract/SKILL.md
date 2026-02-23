---
name: quality-contract
description: Pre-commit quality checklist that catches issues before they become tech debt. Use on every TDD cycle, after refactoring, or before any commit that changes source code.
---

# Quality Contract

Mandatory checks to run BEFORE every commit that touches source code. This eliminates the post-phase audit cycle.

## Instructions

After tests pass (green) and before `git add`, run these checks on every new or modified file:

### Step 1: Format

```bash
uv run ruff format <files>
```

### Step 2: Lint

```bash
uv run ruff check <files>
```

- Fix all issues. If adding `# noqa`, include a justification comment.

### Step 3: Type Check

```bash
uv run mypy <file> --ignore-missing-imports
```

- Fix all type errors. Use `Literal` types for string enums. Avoid `Any` unless justified.

### Step 4: Security Scan

```bash
uv run bandit <file> -c pyproject.toml
```

- No `assert` statements in production code (use proper error handling).
- No hardcoded secrets, eval/exec, or unsafe deserialization.

### Step 5: Completeness Check

Before staging files, verify:

- [ ] New modules are exported from their parent `__init__.py`
- [ ] New routes are registered in `src/api/routes/__init__.py` or `src/api/main.py`
- [ ] New entities are exported from `src/storage/entities/__init__.py`
- [ ] New Alembic migrations have correct `revision` and `down_revision` matching the chain
- [ ] Error handling uses specific exceptions (not bare `except Exception`)
- [ ] URL/path inputs are validated
- [ ] Dynamic imports are restricted to whitelisted paths

### Step 6: Full CI

After committing, before starting the next task:

```bash
make ci-local
```

This runs format-check, lint, typecheck, security-scan, and all unit tests.

## Anti-patterns

- Committing with `# type: ignore` without a comment explaining why.
- Adding `# noqa` to silence a legitimate warning instead of fixing it.
- Skipping mypy/bandit because "it worked in tests."
- Leaving new modules unexported and fixing later in a "cleanup" commit.
- Using `Any` for return types when a concrete type is available.
- Bare `except Exception` in business logic (acceptable only in infrastructure wrappers that must never crash, e.g., A2A executors).

## Integration with TDD Cycle

This contract is Step 5.5 in the TDD cycle — after refactor (Step 5) and before commit (Step 6):

```
Step 1: Write test (red)
Step 2: See it fail
Step 3: Implement
Step 4: See it pass (green)
Step 5: Refactor
Step 5.5: Quality contract ← THIS
Step 6: Commit
Step 7: make ci-local
```
