<!--
Sync Impact Report:
Version: 1.2.0 → 1.3.0 (MINOR: Added TDD workflow requirement with atomic test+implementation commits)
Modified Principles: V. Reliability & Quality (expanded with TDD workflow)
Added Sections: TDD Workflow subsection
Removed Sections: None
Templates Requiring Updates:
  ✅ plan-template.md - Should verify test strategy section exists
  ✅ tasks-template.md - Should include test tasks for each phase
  ✅ spec-template.md - No updates needed
  ✅ .cursor/commands/speckit.constitution.md - No updates needed
Follow-up TODOs: 
  - Ensure all future tasks follow TDD workflow
-->

# Aether Home Architect Constitution

## Core Principles

### I. Safety First

All home automation (HA) automations MUST include a human-in-the-loop (HITL) approval step before execution. This ensures that critical home system changes receive explicit human confirmation, preventing unintended or potentially harmful automated actions. Rationale: Home automation systems control physical environments where errors can have safety, security, or property damage consequences. Human oversight is non-negotiable for any automation that modifies home state.

### II. Isolation

All generated analysis scripts MUST run in a gVisor (runsc) sandbox. This provides strong isolation boundaries for dynamically generated code, preventing script execution from affecting the host system or other processes. Rationale: Generated scripts from AI agents or data science workflows may contain untrusted code. gVisor's user-space kernel provides defense-in-depth security without requiring full VM overhead.

### III. Observability

Every agent negotiation and data science insight MUST be traced via MLflow. All agent interactions, decision points, and analytical outputs must be logged to MLflow for experiment tracking, reproducibility, and auditability. Rationale: Understanding agent behavior and data science workflows requires comprehensive observability. MLflow provides standardized tracking that enables debugging, performance analysis, and compliance verification.

### IV. State

Use LangGraph for state management and Postgres for long-term checkpointing. LangGraph handles in-memory state transitions and workflow orchestration, while Postgres provides durable persistence for state snapshots and recovery. Rationale: Complex agent workflows require robust state management. LangGraph provides structured state transitions, while Postgres ensures durability and enables system recovery from failures.

### V. Reliability & Quality

All code MUST be enterprise-grade with comprehensive test coverage following the testing pyramid:

**Unit Tests (Foundation)**:
- Every module, function, and class MUST have unit tests
- Minimum 80% code coverage required; critical paths require 95%+
- Tests MUST be fast, isolated, and deterministic
- Use mocking/stubbing for external dependencies (HA, databases, LLMs)
- Framework: `pytest` with `pytest-cov` for coverage

**Integration Tests (Middle Layer)**:
- All component boundaries MUST have integration tests
- Database operations tested against real PostgreSQL (via testcontainers)
- MCP client tested against mock HA responses
- Agent workflows tested with LangGraph test utilities
- API routes tested with FastAPI TestClient

**End-to-End Tests (Top Layer)**:
- Critical user journeys MUST have E2E tests
- Full system tests with containerized dependencies
- Includes: discovery flow, conversation flow, automation deployment, insight generation
- Framework: `pytest` with docker-compose test environment

**Test Requirements**:
- All PRs MUST include tests for new functionality
- All bug fixes MUST include regression tests
- Tests MUST run in CI before merge
- Flaky tests are bugs and must be fixed immediately
- Test code follows same quality standards as production code

**TDD Workflow (Required)**:

Tests MUST be written FIRST and committed ATOMICALLY with their implementation. Batching tests at the end leads to incorrect assumptions, multiple fix cycles, and wasted effort. The required workflow for each task:

```
For each task T0XX:
  1. WRITE TEST FIRST
     - Create test file with expected behavior
     - Test should define the API contract (method names, parameters, return types)
  
  2. RUN TEST → SEE IT FAIL (Red)
     - Confirms test is valid and not passing accidentally
     - Example: "ModuleNotFoundError" or "AssertionError"
  
  3. IMPLEMENT THE FEATURE
     - Write minimum code to make the test pass
     - Follow the contract defined by the test
  
  4. RUN TEST → SEE IT PASS (Green)
     - All assertions should pass
     - No modifications to test assertions allowed at this stage
  
  5. REFACTOR (if needed)
     - Clean up implementation
     - Tests must still pass after refactoring
  
  6. COMMIT TEST + IMPLEMENTATION TOGETHER
     - Single atomic commit with both test and implementation
     - Commit message: "feat(scope): T0XX description"
     - Update tasks.md with commit hash
```

**TDD Benefits**:
- Tests define the API contract BEFORE implementation
- Method signatures, parameter names, and return types are validated immediately
- No "bolted-on" tests with wrong assumptions
- Each commit is self-contained and independently verifiable
- Faster feedback loops catch issues immediately

**Anti-patterns (Prohibited)**:
- ❌ Writing all implementation first, then batching tests
- ❌ Modifying test assertions to match incorrect implementation
- ❌ Committing tests separately from their implementation
- ❌ Skipping the "red" phase (test must fail first)

**Quality Gates**:
- Pre-commit hooks: `ruff` (lint), `ruff format` (format), `mypy` (type check)
- CI pipeline: unit tests → integration tests → E2E tests → coverage report
- Coverage regression blocks merge
- Type hints required for all public APIs

Rationale: Home automation systems control physical environments where reliability is critical. Enterprise-grade testing ensures system stability, enables confident refactoring, and catches regressions before they reach production. The testing pyramid provides fast feedback loops while ensuring comprehensive coverage.

## Development Standards

### Conventional Commits

All commits MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. Commit messages MUST use the format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Required Types**:
- `feat`: New feature (correlates with MINOR in SemVer)
- `fix`: Bug fix (correlates with PATCH in SemVer)
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, whitespace)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `build`: Build system or external dependency changes
- `ci`: CI configuration changes
- `chore`: Other changes that don't modify src or test files

**Breaking Changes**: Append `!` after type/scope or include `BREAKING CHANGE:` in footer. Breaking changes correlate with MAJOR in SemVer.

Rationale: Conventional commits enable automated changelog generation, semantic versioning, and clear communication of change intent across the team.

## Governance

This constitution supersedes all other development practices and design decisions. All code, architecture decisions, and implementation plans must comply with these principles.

**Amendment Procedure**: Changes to this constitution require:
1. Documentation of the proposed change and rationale
2. Review and approval process
3. Version increment according to semantic versioning:
   - MAJOR: Backward incompatible governance/principle removals or redefinitions
   - MINOR: New principle/section added or materially expanded guidance
   - PATCH: Clarifications, wording, typo fixes, non-semantic refinements
4. Update of all dependent templates and documentation
5. Migration plan if existing code violates new principles

**Compliance Review**: All pull requests and code reviews must verify compliance with constitution principles. Violations must be justified in the Complexity Tracking section of implementation plans, or the code must be refactored to comply.

**Version**: 1.3.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-03
