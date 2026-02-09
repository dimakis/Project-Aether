---
name: test-isolation
description: Enforce unit test isolation to prevent hangs and side effects. Use when writing or reviewing unit tests, especially API route tests, DB mocks, dependency overrides, or async coordination.
---

# Test Isolation

## Quick Start

Use this checklist for unit tests:

1. Do not touch real DBs, network calls, or filesystem I/O.
2. If using `create_app()`, override all DB dependencies (`get_db`, `get_session`).
3. Avoid module-level side effects; move setup into fixtures.
4. Use `asyncio.Event` for coordination, not `asyncio.sleep()`.
5. Keep `pytest-timeout` configured with `timeout_method = "thread"`.
6. Preserve the unit DB guard in `tests/unit/conftest.py`.

## Patterns

### API route tests with dependency overrides

```python
app = create_app()
app.dependency_overrides[get_db] = lambda: fake_db
app.dependency_overrides[get_session] = fake_session
client = TestClient(app)
```

### Async coordination without sleeps

```python
ready = asyncio.Event()

async def worker():
    # ... setup ...
    ready.set()

await ready.wait()
```

## Anti-patterns

- Calling `create_app()` without overrides
- Import-time calls to `get_session()` / `get_engine()`
- `asyncio.sleep()` for test coordination
- Disabling the unit DB guard fixture
