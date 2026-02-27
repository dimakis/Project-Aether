# Performance & Architecture Review Skill

Systematic checklist for reviewing performance, health checks, and architectural quality. Invoke during feature implementation, large refactors, or when the Boy Scout Rule (Principle VII) triggers deeper review.

## When to Invoke

- Adding or modifying API endpoints
- Adding or modifying database queries / DAL methods
- Adding or modifying background tasks or agent workflows
- Touching health check or observability code
- Any change spanning 5+ files (signals architectural impact)
- User requests a performance or architecture audit

## Checklist

Work through each section. For each item, either confirm it passes or fix it in the same changeset.

### 1. Database & Query Efficiency

- [ ] No N+1 query patterns (use `joinedload`, `selectinload`, or aggregate queries)
- [ ] Counting/grouping done in SQL (`func.count()`, `GROUP BY`), not in Python
- [ ] Connection pool configured: `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`, `pool_pre_ping`
- [ ] No raw SQL string interpolation (parameterized queries only)
- [ ] Indexes exist for columns used in `WHERE`, `ORDER BY`, `JOIN` clauses on hot paths

### 2. Async & Concurrency

- [ ] Independent I/O calls use `asyncio.gather()`
- [ ] Synchronous SDK/library calls wrapped in `asyncio.to_thread()`
- [ ] External calls have explicit timeouts (`asyncio.wait_for()` or client-level timeout)
- [ ] No `asyncio.sleep()` for coordination — use `asyncio.Event` or similar primitives
- [ ] No blocking calls (file I/O, subprocess) in async handlers without executor

### 3. Caching & Memory

- [ ] Frequently-polled endpoints have TTL caches (health, metrics, status)
- [ ] All in-memory caches are bounded (LRU with `maxsize` or TTL eviction)
- [ ] Cache invalidation path exists for testing (`invalidate_*_cache()` function)
- [ ] Dataclasses use `slots=True` where frequently instantiated
- [ ] No unbounded lists/dicts growing with request volume

### 4. Error Handling & Resilience

- [ ] Business logic catches specific exceptions (`SQLAlchemyError`, `httpx.HTTPError`, `TimeoutError`)
- [ ] Bare `except Exception` only at top-level error boundaries (middleware, background task runners)
- [ ] External service calls have retry/circuit-breaker logic or degrade gracefully
- [ ] Error messages don't leak internal details in non-debug mode
- [ ] Timeouts configured for all external dependency calls

### 5. Logging & Observability

- [ ] Hot-path log calls use lazy `%s`-style formatting, not f-strings
- [ ] Log levels appropriate: `debug` for internals, `info` for operations, `warning` for degraded, `error` for failures
- [ ] No secrets, tokens, or PII in log output
- [ ] Traces/spans cover agent actions, LLM calls, tool invocations (Principle III)

### 6. Health Checks & Monitoring

- [ ] Liveness probe (`/health`): responds 200 with no dependency checks
- [ ] Readiness probe (`/ready`): checks critical deps with timeouts
- [ ] Status endpoint (`/status`): runs checks concurrently, TTL-cached, includes component latency
- [ ] Container orchestration health check paths match actual API routes
- [ ] Application version read from package metadata, not hardcoded

### 7. Code Quality (Boy Scout Rule)

- [ ] No duplicated dependency functions (shared `get_db`, auth, etc. centralized)
- [ ] Pydantic models use `model_config = ConfigDict(...)`, not inner `class Config`
- [ ] No hardcoded values that should be in settings
- [ ] Dead code and stale TODO comments removed
- [ ] Type hints present on all public functions and method signatures
- [ ] String building in loops uses `list.append()` + `"".join()`, not `+=`

### 8. Architecture & Dependencies

- [ ] New modules exported from parent `__init__.py`
- [ ] New routes registered in router
- [ ] No circular imports
- [ ] Dependencies pinned to exact versions
- [ ] No unused imports or dependencies

## Output

After completing the checklist, summarize:
1. Items that passed (brief)
2. Items that were fixed in this changeset (with file:line references)
3. Items that need follow-up (out of scope for current change, tracked as TODOs with issue references)

## Reference

- Constitution: `.specify/memory/constitution.md` § VII. Performance & Continuous Improvement
- Always-applied rule: `.cursor/rules/boy-scout-rule.mdc`
- Quality contract: `.cursor/skills/quality-contract/SKILL.md`
