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

Aether follows **Test-Driven Development (TDD)**:

1. **Red**: Write a failing test first.
2. **Green**: Write the minimum code to make it pass.
3. **Refactor**: Clean up while keeping tests green.
4. **Commit**: Commit the test and implementation together.

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

1. Fork the repository and create a feature branch.
2. Write tests first (TDD), then implement.
3. Ensure all checks pass: `make check && make test`.
4. Update documentation if needed.
5. Submit a pull request with a clear description.
6. PRs require at least one review before merging.

## Code of Conduct

Be respectful and constructive. We are committed to providing a welcoming and inclusive experience for everyone.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
