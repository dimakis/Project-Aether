"""Rate limiting configuration for API endpoints (T188).

Provides a shared Limiter instance that route modules can import
to apply per-endpoint rate limits on expensive operations.

Rate limit tiers:
- Default: 60/minute (applied via app-level default)
- Standard: 30/minute (read-heavy endpoints)
- Expensive: 10/minute (LLM calls, discovery, analysis)
- Critical: 5/minute (deployment, rollback)

Usage in route modules:
    from src.api.rate_limit import limiter

    @router.post("/sync")
    @limiter.limit("10/minute")
    async def sync_entities(request: Request, ...):
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate limiter instance
# key_func: Uses client IP address for per-client rate limiting
# default_limits: Applied to all endpoints unless overridden
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
)
