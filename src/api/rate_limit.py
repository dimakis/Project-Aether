"""Rate limiting configuration for API endpoints (T188).

Provides a shared Limiter instance that route modules can import
to apply per-endpoint rate limits on expensive operations.

Rate limit tiers:
- Global default: 60/minute per IP (covers ALL endpoints automatically)
- Standard: 30/minute (read-heavy endpoints with expensive queries)
- Expensive: 10/minute (LLM calls, discovery, analysis)
- Critical: 5/minute (deployment, rollback, seed operations)

The global default ensures all endpoints have rate limiting even if a
developer forgets to add per-endpoint limits. Per-endpoint decorators
override the global default with tighter limits where needed.

Usage in route modules:
    from src.api.rate_limit import limiter

    @router.post("/sync")
    @limiter.limit("10/minute")
    async def sync_entities(request: Request, ...):
        ...
"""

from slowapi import Limiter
from starlette.requests import Request


def _get_real_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For from trusted proxies.

    When running behind a reverse proxy (nginx, K8s ingress), the direct
    client IP is the proxy. X-Forwarded-For contains the real client IP
    as the first entry in the comma-separated list.

    Args:
        request: Starlette/FastAPI request object.

    Returns:
        Client IP address string.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2 — take the leftmost (client)
        return forwarded_for.split(",")[0].strip()
    # Direct connection (no proxy)
    if request.client:
        return request.client.host
    return "127.0.0.1"


# Shared rate limiter instance
# key_func: Uses real client IP (supports X-Forwarded-For behind proxy)
# default_limits: Applied to all endpoints unless overridden by @limiter.limit()
limiter = Limiter(
    key_func=_get_real_client_ip,
    default_limits=["60/minute"],
)

# Maximum request body size (bytes) for non-streaming endpoints.
# Applied via middleware in main.py to prevent DoS via large payloads.
MAX_REQUEST_BODY_BYTES = 1_048_576  # 1 MB
