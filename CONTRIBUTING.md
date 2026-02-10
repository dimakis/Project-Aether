# Contributing to Aether

Thank you for your interest in contributing to Aether! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [Podman](https://podman.io/) (container runtime)
- Node.js 18+ (for UI development)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/dsaridak/home_agent.git
cd home_agent

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Install dependencies and start infrastructure
make dev

# Run the application
make run

# Run with UI
make run-ui
```

### Running Tests

```bash
make test          # All tests
make test-unit     # Unit tests only
make test-int      # Integration tests (requires services)
make test-cov      # Tests with coverage report
```

### Code Quality

```bash
make lint          # Run ruff linter
make format        # Format code
make check         # Run all quality checks (lint + typecheck)
```

## Development Workflow

### Test-Driven Development (TDD)

Aether follows **Test-Driven Development (TDD)**:

1. **Red**: Write a failing test first.
2. **Green**: Write the minimum code to make it pass.
3. **Refactor**: Clean up while keeping tests green.
4. **Commit**: Commit the test and implementation together.

### Feature Branch Workflow

All new features and functional changes follow this process:

1. **Create a branch**: `git checkout -b feat/my-feature develop`
2. **Develop with TDD**: Write tests first, commit incrementally (see above).
3. **Run CI locally**: `make ci-local` — runs lint, typecheck, and unit tests. Must pass.
4. **Squash commits**: `git rebase -i develop` — squash all commits into one with a conventional commit message.
5. **Push and open PR**: `git push -u origin HEAD && gh pr create`
6. **Rebase-merge**: After review and remote CI passes, rebase-merge the PR.

> **Why squash before push?** Each feature lands as a single clean commit on `develop`/`main`, keeping `git log` readable and `git bisect` effective. Incremental commits on your branch are working checkpoints — they help you during development but don't need to persist in the main history.

### Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`

**Examples**:
```
feat(api): add entity search endpoint
fix(scheduler): prevent duplicate job execution
docs: update deployment guide
test(dal): add repository edge case tests
```

### Branch Naming

- `feat/short-description` for features
- `fix/short-description` for bug fixes
- `docs/short-description` for documentation
- `refactor/short-description` for refactoring

## Project Structure

```
src/
  agents/       # LangGraph agent definitions
  api/          # FastAPI routes, middleware, schemas
  dal/          # Data access layer (repositories)
  graph/        # LangGraph workflows and state
  mcp/          # Home Assistant MCP client
  sandbox/      # gVisor script execution sandbox
  scheduler/    # APScheduler cron job service
  storage/      # SQLAlchemy ORM models
  tools/        # LangChain tool definitions
  tracing/      # MLflow observability
tests/
  unit/         # Fast, isolated unit tests
  integration/  # Tests requiring services (DB, etc.)
  e2e/          # End-to-end tests
ui/             # React frontend (Vite + TypeScript)
infrastructure/ # Container and deployment configs
```

## Security

- **Never** commit secrets, API keys, or credentials.
- **Never** use `eval()` or `exec()` outside the sandbox.
- **Always** validate input via Pydantic schemas.
- **Always** use parameterized queries (no raw SQL with user input).
- See [SECURITY.md](SECURITY.md) for the full security policy.

## Pull Request Process

1. Create a feature branch from `develop` and develop with TDD.
2. Run `make ci-local` — all checks must pass before proceeding.
3. Squash all branch commits into a single conventional commit (`git rebase -i develop`).
4. Push the branch and open a pull request with a clear description.
5. Ensure remote CI passes and request review.
6. PRs are rebase-merged to maintain linear history.

## Code of Conduct

Be respectful and constructive. We are committed to providing a welcoming and inclusive experience for everyone.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
