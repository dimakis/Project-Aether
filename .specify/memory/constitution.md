<!--
Sync Impact Report:
Version: 1.12.0 → 1.13.0 (MINOR: Added OpenAPI spec update requirement to Delivery Checklist and PR Workflow)
Modified Principles: None
Added Sections: None
Modified Sections: "Feature Delivery Standards" — added OpenAPI spec update to Delivery Checklist item 5; "Branching & PR Workflow" — added OpenAPI spec regeneration to Required Workflow step 3; "Quality Gates" — added OpenAPI spec freshness check; AI Directives updated
Removed Sections: None
Templates Requiring Updates:
  ⬜ .github/PULL_REQUEST_TEMPLATE.md — add OpenAPI spec checklist item
  ⬜ .cursor/rules/feature-branch-workflow.mdc — mention OpenAPI spec in CI step
Follow-up TODOs:
  - Update PR template with OpenAPI spec checkbox
  - Consider adding `make generate-openapi` to `make ci-local`
-->

# Aether Home Architect Constitution

---

## AI Directives

> **For coding agents.** Terse, actionable constraints extracted from the full governance below.
> When in doubt, consult the detailed section for rationale and examples.

### Principles

1. **Safety** — Every HA automation MUST include human-in-the-loop approval before execution. No exceptions.
2. **Isolation** — All generated scripts MUST run inside a gVisor (runsc) sandbox. Never execute untrusted code on the host.
3. **Observability** — All agent actions, LLM calls, and tool invocations MUST be traced via MLflow with session correlation.
4. **State** — Use LangGraph for workflow state; Postgres for durable checkpointing. No in-memory-only state for anything that must survive restarts.
5. **Reliability** — Minimum 80% code coverage (95%+ for critical paths). Testing pyramid: unit → integration → E2E. Flaky tests are bugs.
6. **Security** — Defence in depth at every layer. Security wins over development speed — always. See full 8-point posture below.

### Security MUST / MUST NOT

- MUST encrypt credentials at rest (Fernet/AES-256) or hash irreversibly (bcrypt, work factor >= 12).
- MUST validate all external input via Pydantic schemas before use.
- MUST use parameterised queries only — no raw SQL interpolation.
- MUST serve production traffic over TLS with security headers on every response.
- MUST pin dependencies to exact versions; patch known CVEs within 72 hours.
- MUST require authentication by default; exempt routes are explicit exceptions.
- MUST log auth events with timestamps; MUST NOT log secrets or PII.
- MUST NOT store plaintext passwords/tokens, use eval()/exec() outside sandbox, disable auth for convenience, return stack traces in API errors, use MD5/SHA-1 for security hashing, or hard-code secrets.

### Development MUST / MUST NOT

- MUST follow TDD: write test first (red), implement (green), refactor, commit atomically. Never batch tests after implementation.
- MUST commit incrementally: one logical change per commit, max ~400 lines, commit proactively after each TDD cycle.
- MUST use Conventional Commits: `<type>[scope]: <description>` with required types (feat, fix, docs, style, refactor, perf, test, build, ci, chore).
- MUST create feature directory (`specs/<project>/features/NN-name/`) with spec.md, plan.md, tasks.md before implementation begins.
- MUST update documentation (architecture.md, tasks.md, plan.md) alongside code — never batch docs as an afterthought.
- MUST regenerate the OpenAPI spec (`specs/<project>/contracts/api.yaml`) when any API route, schema, or endpoint changes. Stale specs are bugs.
- MUST NOT choose a simpler implementation that weakens security or creates tech debt degrading security posture later.
- MUST develop new features on a dedicated branch, run CI locally (`make ci-local`), squash commits into one, then push and open a PR. PRs are rebase-merged for linear history.
- MUST run the quality contract (format, lint, mypy, bandit, completeness check) on every changed file BEFORE committing. New modules, routes, and entities MUST be exported/registered in the same commit. See `.cursor/skills/quality-contract/SKILL.md`.

### Reference

Full governance, rationale, examples, and amendment procedure: see sections below.
Procedural skills: `security-review`, `tdd-cycle`, `feature-checklist`, `quality-contract` (in `.cursor/skills/`).

---

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

**Test Isolation Requirements (Non-Negotiable)**:
- Unit tests MUST NOT attempt real database connections, network calls, or filesystem I/O
- All external dependencies MUST be mocked/stubbed at the dependency injection boundary
- `pytest-timeout` MUST be configured globally with `timeout_method = "thread"` for async compatibility
- Tests that use `create_app()` MUST override all DB dependencies (`get_db`, `get_session`) with mocks
- Module-level imports in test files MUST NOT trigger side effects (no eager DB/network connections)
- The `tests/unit/conftest.py` autouse DB guard MUST NOT be disabled or bypassed
- Flaky tests caused by timing (`asyncio.sleep` for coordination) MUST use `asyncio.Event` instead

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
  
  6. COMMIT IMMEDIATELY (Mandatory Checkpoint)
     - git add test + implementation files
     - Single atomic commit with conventional commit message
     - Verify commit succeeded before proceeding
     - Update tasks.md with commit hash
     - NEVER start the next task without committing this one
```

**TDD Benefits**:
- Tests define the API contract BEFORE implementation
- Method signatures, parameter names, and return types are validated immediately
- No "bolted-on" tests with wrong assumptions
- Each commit is self-contained and independently verifiable
- Faster feedback loops catch issues immediately

**TDD Applies to Planning Too**:

When creating implementation plans or build plans, each deliverable/step MUST include its tests as part of the same step — never as a separate phase. A plan that lists "Part 2: Build modules" and "Part 4: Write tests" violates TDD just as much as coding all features before writing any tests. The correct structure is: "Step N: Build X (test-first)" where the test file is the first artifact created in that step.

**Anti-patterns (Prohibited)**:
- Writing all implementation first, then batching tests
- Modifying test assertions to match incorrect implementation
- Committing tests separately from their implementation
- Skipping the "red" phase (test must fail first)
- Structuring plans with "Implementation" and "Tests" as separate phases or sections (tests are part of each deliverable, not a separate workstream)

**Quality Gates**:
- Pre-commit hooks: `ruff` (lint), `ruff format` (format), `mypy` (type check)
- CI pipeline: unit tests → integration tests → E2E tests → coverage report
- OpenAPI spec freshness: PRs that modify API routes or schemas MUST include a regenerated OpenAPI spec. CI SHOULD verify the spec is not stale.
- Coverage regression blocks merge
- Type hints required for all public APIs

Rationale: Home automation systems control physical environments where reliability is critical. Enterprise-grade testing ensures system stability, enables confident refactoring, and catches regressions before they reach production. The testing pyramid provides fast feedback loops while ensuring comprehensive coverage.

### VI. Security by Default

This application is internet-accessible and controls a physical home. All code — whether written by a human or generated by an AI coding agent — MUST treat security as a first-class, non-negotiable concern at every layer.

**Mandatory Security Posture**:

1. **Defence in Depth**: Never rely on a single security control. Authentication, authorization, input validation, output encoding, encryption, and network controls MUST each be implemented independently so that failure of one layer does not compromise the system.

2. **Secrets & Credentials**:
   - Secrets (tokens, passwords, API keys) MUST NEVER appear in source code, logs, error messages, or client-side responses.
   - Credentials stored at rest MUST be encrypted (Fernet/AES-256) or irreversibly hashed (bcrypt with work factor ≥ 12).
   - JWT signing keys MUST be ≥ 256 bits. Tokens MUST have bounded expiry.
   - All cookies carrying auth tokens MUST be `httpOnly`, `Secure` (in production), and `SameSite=Lax` or stricter.

3. **Input Validation & Injection Prevention**:
   - All external input (HTTP bodies, query params, headers, WebSocket messages) MUST be validated via Pydantic schemas or equivalent strict typing before use.
   - Database access MUST use parameterised queries (SQLAlchemy ORM/Core) — raw string interpolation into SQL is strictly prohibited.
   - Rendered output MUST be contextually escaped to prevent XSS.

4. **Transport & Headers**:
   - All production traffic MUST be served over TLS (HTTPS).
   - Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Strict-Transport-Security`) MUST be present on every response.
   - CORS origins MUST be explicitly allowlisted — wildcard (`*`) origins are prohibited in production.

5. **Dependency Hygiene**:
   - Dependencies MUST be pinned to exact versions in the lock file.
   - Known-vulnerable dependencies MUST be updated within 72 hours of advisory publication.
   - New dependencies MUST be evaluated for maintenance status, known CVEs, and supply-chain risk before adoption.

6. **No Security Shortcuts**:
   - Coding agents MUST NOT choose a simpler implementation if it weakens security or creates technical debt that degrades the security posture later.
   - When there is a trade-off between development speed and security, security wins — always.
   - `# nosec`, `# type: ignore[security]`, disabling linter security rules, or suppressing security warnings is prohibited unless accompanied by a written justification in the code AND approval in code review.

7. **Least Privilege & Minimised Attack Surface**:
   - API endpoints MUST require authentication by default; public endpoints are the exception and MUST be explicitly listed in `EXEMPT_ROUTES`.
   - Database connections MUST use a role with minimal required permissions.
   - Container images MUST run as non-root with a read-only filesystem where possible.
   - Unused routes, debug endpoints, and development scaffolding MUST be removed or disabled before production deployment.

8. **Audit & Accountability**:
   - Authentication events (login, logout, failed attempts, passkey registration) MUST be logged with timestamps and client metadata.
   - Changes to system configuration (HA token, password hash) MUST be logged.
   - Logs MUST NOT contain secrets, tokens, or PII beyond what is strictly necessary.

**Anti-patterns (Prohibited)**:
- Storing plaintext passwords or tokens in the database
- Using `eval()`, `exec()`, or equivalent dynamic code execution outside the sandbox
- Disabling authentication "for convenience" in any deployed environment
- Returning stack traces, internal paths, or dependency versions in API error responses
- Using MD5 or SHA-1 for any security-critical hashing
- Hard-coding secrets, even "temporarily"
- Choosing a faster/simpler implementation that creates a known security weakness, even if "we'll fix it later"

Rationale: Aether is designed for remote access over the internet and controls a physical home. A security breach could expose private home data, enable unauthorized control of physical devices, or serve as a pivot point into the home network. Security is not a feature to be bolted on — it is a foundational property that must be maintained in every line of code, every dependency choice, and every architecture decision.

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
   - Multiple unrelated features
   - Feature code + unrelated refactoring
   - Changes to multiple independent modules
   - Implementation + documentation for different features

3. **Commit Immediately**: After completing each functional piece:
   - Run tests to verify the piece works
   - Commit immediately before starting the next piece
   - Do NOT batch multiple pieces into a single commit
   - This applies equally to AI agents during coding sessions. The agent MUST NOT proceed to the next task until the current task is committed.

4. **Commit Size Guidelines**:
   - Ideal: 50-200 lines changed
   - Maximum: 400 lines (except for generated code or large test fixtures)
   - If a commit exceeds limits, split into smaller logical pieces

**Examples**:

Good commit sequence:
```
feat(dal): add InsightRepository with CRUD operations
feat(dal): add InsightRepository unit tests
feat(sandbox): add Containerfile.sandbox for data science
feat(sandbox): update SandboxRunner to use custom image
test(sandbox): add sandbox runner unit tests
```

Bad commit (too large, multiple pieces):
```
feat(us3): implement Data Scientist foundation
- InsightRepository
- Containerfile.sandbox  
- Energy history module
- API schemas
- All tests
```

**Commit Checkpoints (Agentic Workflows)**:

When an AI agent is implementing tasks in a coding session, the following commit checkpoints are mandatory:

1. **After each TDD cycle**: Once a test passes (green), the agent MUST commit the test + implementation before starting the next TDD cycle. No exceptions.
2. **After each logical unit of work**: Spec files, documentation updates, refactoring passes, and configuration changes each get their own commit immediately upon completion.
3. **Uncommitted change limit**: The agent MUST NOT accumulate more than ~400 lines of uncommitted changes. If approaching this limit, stop and commit what's complete.
4. **Proactive commits**: The agent MUST commit proactively at each checkpoint. Do NOT wait for the user to request commits — committing is part of the task, not a separate action.
5. **Session end**: Before ending a session or switching context, ALL uncommitted work must be committed (or stashed with explanation).

**Anti-patterns (Prohibited)**:
- Implementing multiple tasks in a session without committing between them
- Waiting for the user to request commits instead of committing proactively
- Accumulating a large batch of uncommitted changes across many files
- Deferring commits to "do them all at the end"

**Rationale**: Incremental commits enable:
- Easier code review (smaller diffs)
- Precise git bisect for debugging
- Clean reverts without collateral damage
- Better understanding of project history
- Reduced merge conflicts

### Feature Delivery Standards

Every feature implementation MUST be tracked, documented, and delivered as a complete unit. Features are never "done" until all artifacts are in place.

**Feature Directory Structure**:

Every feature MUST have a directory under `specs/<project>/features/` with a numbered prefix indicating the order it was added to the project:

```
specs/<project>/features/NN-feature-name/
├── spec.md    # What the feature does and why
├── plan.md    # Build plan used during implementation (saved for historical tracing)
└── tasks.md   # Implementation tasks with status tracking
```

**Feature Naming Convention**:

1. **Active Features**: `NN-feature-name/` where NN is a zero-padded sequence number
   - Example: `04-ha-registry-management/`
   - Numbers indicate the order features were added to the project
   
2. **Completed Features**: `NN-C-feature-name/` where C indicates complete
   - Example: `04-C-ha-registry-management/`
   - Rename directory when all tasks are done and feature is deployed

3. **Completion Header**: When a feature is completed, add to the TOP of each doc (spec.md, plan.md, tasks.md):
   ```
   **Completed**: YYYY-MM-DD
   ```

**Feature Lifecycle**:
```
01-feature-name/        # Active development
    ↓ (all tasks complete)
01-C-feature-name/      # Completed, add date header to all docs
```

**Delivery Checklist (Required for Every Feature)**:

1. **Feature Directory**: `features/<name>/` created with spec, plan, and tasks before implementation begins
2. **Build Plan Saved**: The build plan used during implementation MUST be saved as the feature's `plan.md` for historical tracing of architecture evolution
3. **Tests Updated**: All tests added/updated alongside implementation (per TDD workflow above) — never batched as an afterthought
4. **Documentation Updated**: Every feature commit MUST update relevant documentation:
   - `docs/architecture.md` — if the feature changes system architecture, data flows, or agent capabilities
   - Project-level `plan.md` — if the feature changes project structure or capabilities
   - Feature `tasks.md` — mark tasks complete with commit hashes
5. **OpenAPI Spec Updated**: If the PR modifies any API route, request/response schema, or endpoint, the OpenAPI spec (`specs/<project>/contracts/api.yaml`) MUST be regenerated and included in the PR. A stale spec is a bug.
6. **Functional Commits**: Each commit self-contained and independently verifiable (per Incremental Commits above)

**Anti-patterns (Prohibited)**:
- Writing all code first, then batching documentation updates
- Committing a feature without updating architecture docs
- Skipping the feature directory ("it's too small")
- Leaving the build plan unsaved after implementation

**Rationale**: Feature directories create a historical record of how the architecture evolved over time. Each feature's spec, plan, and tasks document the "why" and "how" decisions were made, enabling future developers (and AI agents) to understand context without re-deriving it. This is especially important for agentic systems where capabilities compound over time.

### Branching & PR Workflow

All new features and functional changes MUST be developed on a dedicated branch and merged via pull request. Direct commits to `main` or `develop` are prohibited for functional changes.

**Required Workflow**:

1. **Create feature branch**: Branch from `develop` using the naming convention `feat/short-description`, `fix/short-description`, `docs/short-description`, `refactor/short-description`, or `ci/short-description`.
2. **Develop incrementally**: Follow TDD and incremental commit discipline (see above). Commits on the feature branch are working checkpoints that aid local review, bisect, and rollback.
3. **Run CI locally**: Run `make ci-local` to execute the same checks that run in GitHub Actions (lint, typecheck, unit tests). If API routes or schemas changed, regenerate the OpenAPI spec (`python scripts/generate_openapi.py`) and include it in the commit. The branch MUST pass locally before proceeding.
4. **Squash commits locally**: Once CI passes, squash all branch commits into a single conventional commit: `git rebase -i develop`. The squash commit message MUST follow the Conventional Commits format.
5. **Push and open PR**: Push the squashed branch (`git push -u origin HEAD`) and create a pull request via `gh pr create`. The PR description MUST follow the PR template.
6. **Rebase-merge**: PRs are rebase-merged onto the target branch. Since the branch is already a single commit, this lands one clean commit with linear history.

**Exceptions**: Typo fixes, single-commit doc changes, and CI config tweaks MAY be committed directly to `develop` if they are trivially correct.

**Anti-patterns (Prohibited)**:
- Pushing directly to `main` or `develop` for functional changes
- Pushing a branch with unsquashed commits (multiple commits in the PR)
- Merging without running `make ci-local` first
- Using squash-merge or merge-commit strategies on the PR (rebase-merge only)

**Rationale**: Feature branches isolate in-progress work and enable code review before integration. Local CI catches issues before they reach the remote pipeline. Squashing locally produces one clean commit per feature, and rebase-merging preserves linear history — making `git log`, `git bisect`, and rollbacks straightforward.

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

**Version**: 1.13.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-13
