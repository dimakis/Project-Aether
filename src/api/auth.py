"""API key authentication middleware for FastAPI.

Provides API key authentication using FastAPI's dependency injection.
Supports API key in both header (X-API-Key) and query parameter (api_key).
"""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

from src.settings import Settings, get_settings

# Header-based API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Query parameter-based API key
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# Routes that are exempt from authentication
EXEMPT_ROUTES = {
    "/api/v1/system/health",
    "/api/v1/system/status",
    "/api/v1/system/metrics",
}


async def verify_api_key(
    request: Request,
    header_key: str | None = Security(api_key_header),
    query_key: str | None = Security(api_key_query),
) -> str:
    """Verify API key from header or query parameter.

    Checks for API key in:
    1. X-API-Key header
    2. api_key query parameter

    If no API key is configured in settings (empty string), authentication
    is disabled (development convenience).

    Health check endpoints are exempt from authentication.

    Args:
        request: FastAPI request object (to check route path)
        header_key: API key from X-API-Key header
        query_key: API key from api_key query parameter

    Returns:
        The API key that was verified (for logging/tracking purposes)

    Raises:
        HTTPException: 401 Unauthorized if key is invalid or missing when auth is enabled
    """
    # Check if this route is exempt from authentication
    route_path = request.url.path
    if route_path in EXEMPT_ROUTES:
        return ""

    settings = get_settings()
    configured_key = settings.api_key.get_secret_value()

    # If no API key is configured, disable authentication (development mode)
    if not configured_key:
        return ""

    # Get API key from header or query parameter
    provided_key = header_key or query_key

    # If no key provided, raise 401
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide it via X-API-Key header or api_key query parameter.",
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return provided_key


# Dependency for endpoints that require authentication
RequireAPIKey = Annotated[str, Depends(verify_api_key)]
