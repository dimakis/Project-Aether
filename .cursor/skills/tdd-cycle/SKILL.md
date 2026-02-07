---
name: tdd-cycle
description: Enforce the 6-step TDD red/green/refactor/commit workflow from the Aether constitution. Use when implementing features, writing tests, doing TDD, or when the user asks to build something test-first.
---

# TDD Cycle

Enforce the mandatory test-driven development workflow from `.specify/memory/constitution.md` (Principle V).

## Instructions

For every implementation task, follow these 6 steps in strict order. Do NOT skip steps or reorder them.

### Step 1: Write Test First

- Create or update the test file with expected behavior.
- The test defines the API contract: method names, parameters, return types.
- The test file is the **first** artifact created for this task.

```
Action: Create/edit test file
Tool: Write to tests/unit/test_<module>.py or tests/integration/test_<module>.py
```

### Step 2: Run Test — See It Fail (Red)

- Execute the test to confirm it fails.
- Expected failures: `ModuleNotFoundError`, `ImportError`, `AssertionError`, `AttributeError`.
- If the test passes without implementation, the test is wrong — fix it.

```
Action: Run pytest on the specific test file
Tool: Shell — pytest tests/unit/test_<module>.py -v
Verify: At least one FAILED result in output
```

### Step 3: Implement the Feature

- Write the **minimum** code to make the test pass.
- Follow the contract defined by the test (names, params, returns).
- Do not add functionality beyond what the test requires.

```
Action: Create/edit source file(s)
Tool: Write to src/<module>.py
```

### Step 4: Run Test — See It Pass (Green)

- Execute the test again.
- All assertions must pass. No modifications to test assertions allowed at this stage.
- If the test fails, fix the **implementation**, not the test.

```
Action: Run pytest on the specific test file
Tool: Shell — pytest tests/unit/test_<module>.py -v
Verify: All PASSED in output
```

### Step 5: Refactor (If Needed)

- Clean up the implementation: rename, extract, simplify.
- Tests must still pass after refactoring.
- Run tests again to confirm.

### Step 6: Commit Immediately (Mandatory Checkpoint)

- Stage both test and implementation files.
- Create a single atomic commit with a conventional commit message.
- Verify the commit succeeded before proceeding to the next task.
- Update `tasks.md` with the commit hash if applicable.

```
Action: Commit test + implementation together
Tool: Shell — git add <files> && git commit -m "<type>(scope): description"
Verify: Commit hash appears in output
```

**NEVER start the next task without completing this step.**

## Anti-patterns to Prevent

- Writing all implementation first, then batching tests afterward.
- Modifying test assertions to match incorrect implementation (fix the code, not the test).
- Committing tests separately from their implementation.
- Skipping the red phase (test must fail first to prove it tests something real).
- Structuring plans with "Implementation" and "Tests" as separate phases.

## Planning Integration

When creating build plans, each step must be structured as:

```
Step N: Build <component> (test-first)
  - Test file is the first artifact
  - Implementation follows
  - Both committed together
```

Never structure plans with "Part A: Build modules" and "Part B: Write tests" — this violates TDD.
