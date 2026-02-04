<!--
Sync Impact Report:
Version: 1.4.0 → 1.5.0 (MINOR: Added Incremental Commits development standard)
Modified Principles: None
Added Sections: Incremental Commits subsection under Development Standards
Removed Sections: None
Templates Requiring Updates:
  ✅ No template updates required
Follow-up TODOs: 
  - Enforce incremental commits in all future development
  - Review existing commit practices
-->

# Aether Home Architect Constitution

## Core Principles

### I. Safety First

All home automation (HA) automations MUST include a human-in-the-loop (HITL) approval step before execution. This ensures that critical home system changes receive explicit human confirmation, preventing unintended or potentially harmful automated actions. Rationale: Home automation systems control physical environments where errors can have safety, security, or property damage consequences. Human oversight is non-negotiable for any automation that modifies home state.

### II. Isolation

All generated analysis scripts MUST run in a gVisor (runsc) sandbox. This provides strong isolation boundaries for dynamically generated code, preventing script execution from affecting the host system or other processes. Rationale: Generated scripts from AI agents or data science workflows may contain untrusted code. gVisor's user-space kernel provides defense-in-depth security without requiring full VM overhead.

### III. Observability

Every agent negotiation and data science insight MUST be traced via MLflow. All agent interactions, decision points, and analytical outputs must be logged to MLflow for experiment tracking, reproducibility, and auditability. Rationale: Understanding agent behavior and data science workflows requires comprehensive observability. MLflow provides standardized tracking that enables debugging, performance analysis, and compliance verification.

**Tracing Architecture Requirements**:

1. **Session Correlation**: Multi-turn conversations MUST share the same `mlflow.trace.session` metadata, enabling grouping of related traces in the MLflow UI. Use `session_context()` at workflow entry points and propagate `conversation_id` as the session identifier.

2. **Agent Trace Spans**: All agents extending `BaseAgent` MUST use the `trace_span()` context manager for operations. This ensures:
   - Hierarchical trace visualization (parent/child spans)
   - Input/output capture for debugging (`span.set_inputs()`, `span.set_outputs()`)
   - Automatic session correlation via state's `conversation_id`

3. **LLM Autologging**: Enable `mlflow.langchain.autolog(log_inputs=True, log_outputs=True)` to automatically capture all LangChain and OpenAI API calls with full message content.

4. **Experiment Runs**: Long-running workflows (discovery, conversations) MUST use `start_experiment_run()` to create named MLflow runs with:
   - `session.id` tag for correlation
   - Relevant parameters (triggered_by, filters, etc.)
   - Metrics (duration, counts, success/failure)

5. **Tool Call Tracing**: MCP tool invocations MUST create child spans capturing:
   - Tool name and arguments (inputs)
   - Tool response (outputs)
   - Error states if applicable

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

### Incremental Commits

All work MUST be committed in small, focused, incremental commits. Each commit should represent ONE logical change that can be understood, reviewed, and reverted independently.

**Required Commit Granularity**:

1. **One Functional Piece Per Commit**: Each commit should contain exactly one of:
   - A single new module/class with its tests
   - A single bug fix with its regression test
   - A single refactoring change
   - Documentation updates for a specific feature

2. **Maximum Commit Scope**: A commit should NOT combine:
   - ❌ Multiple unrelated features
   - ❌ Feature code + unrelated refactoring
   - ❌ Changes to multiple independent modules
   - ❌ Implementation + documentation for different features

3. **Commit Immediately**: After completing each functional piece:
   - Run tests to verify the piece works
   - Commit immediately before starting the next piece
   - Do NOT batch multiple pieces into a single commit

4. **Commit Size Guidelines**:
   - Ideal: 50-200 lines changed
   - Maximum: 400 lines (except for generated code or large test fixtures)
   - If a commit exceeds limits, split into smaller logical pieces

**Examples**:

✅ Good commit sequence:
```
feat(dal): add InsightRepository with CRUD operations
feat(dal): add InsightRepository unit tests
feat(sandbox): add Containerfile.sandbox for data science
feat(sandbox): update SandboxRunner to use custom image
test(sandbox): add sandbox runner unit tests
```

❌ Bad commit (too large, multiple pieces):
```
feat(us3): implement Data Scientist foundation
- InsightRepository
- Containerfile.sandbox  
- Energy history module
- API schemas
- All tests
```

**Rationale**: Incremental commits enable:
- Easier code review (smaller diffs)
- Precise git bisect for debugging
- Clean reverts without collateral damage
- Better understanding of project history
- Reduced merge conflicts

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

**Version**: 1.5.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-04
