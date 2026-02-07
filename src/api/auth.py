"""Authentication middleware for FastAPI.

Supports multiple authentication methods (checked in order):
1. JWT Bearer token (Authorization: Bearer <token>)
2. JWT session cookie (aether_session)
3. API key header (X-API-Key)
4. API key query parameter (api_key)

If no auth credentials are configured (both AUTH_PASSWORD and API_KEY empty),
authentication is disabled (development convenience).
"""

import secrets
import time
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import SecretStr

# Import module (not function) so monkeypatching in tests works correctly.
# Using `from src.settings import get_settings` would create a local reference
# that monkeypatch cannot intercept.
import src.settings as _settings_mod
from src.settings import Settings

# Header-based API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Query parameter-based API key
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# JWT configuration
JWT_ALGORITHM = "HS256"
JWT_COOKIE_NAME = "aether_session"

# Routes that are exempt from authentication
EXEMPT_ROUTES = {
    "/api/v1/health",
    "/api/v1/status",
    "/api/v1/metrics",
    "/api/v1/auth/login",
    "/api/v1/auth/passkey/authenticate/options",
    "/api/v1/auth/passkey/authenticate/verify",
}


def _get_jwt_secret(settings: Settings) -> str:
    """Get or generate the JWT signing secret.

    If jwt_secret is not configured, generates a deterministic secret
    from auth_password to survive restarts (but not password changes).
    """
    configured = settings.jwt_secret.get_secret_value()
    if configured:
        return configured
    # Fallback: derive from auth_password (stable across restarts)
    password = settings.auth_password.get_secret_value()
    if password:
        return f"aether-jwt-{password}-auto"
    return "aether-dev-jwt-secret"


def create_jwt_token(username: str, settings: Settings | None = None) -> str:
    """Create a JWT token for the given username.

    Args:
        username: The authenticated username
        settings: Optional settings override

    Returns:
        Encoded JWT token string
    """
    settings = settings or _settings_mod.get_settings()
    secret = _get_jwt_secret(settings)
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + settings.jwt_expiry_hours * 3600,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str, settings: Settings | None = None) -> dict | None:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string
        settings: Optional settings override

    Returns:
        Decoded payload dict, or None if invalid/expired
    """
    settings = settings or _settings_mod.get_settings()
    secret = _get_jwt_secret(settings)
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        return None


def _is_auth_configured(settings: Settings) -> bool:
    """Check if any authentication method is configured."""
    has_password = bool(settings.auth_password.get_secret_value())
    has_api_key = bool(settings.api_key.get_secret_value())
    return has_password or has_api_key


def _extract_bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def verify_api_key(
    request: Request,
    header_key: str | None = Security(api_key_header),
    query_key: str | None = Security(api_key_query),
) -> str:
    """Verify authentication from JWT or API key.

    Checks for credentials in order:
    1. JWT Bearer token (Authorization header)
    2. JWT session cookie (aether_session)
    3. API key header (X-API-Key)
    4. API key query parameter (api_key)

    If no auth is configured (both AUTH_PASSWORD and API_KEY empty),
    authentication is disabled (development convenience).

    Args:
        request: FastAPI request object
        header_key: API key from X-API-Key header
        query_key: API key from api_key query parameter

    Returns:
        The authenticated identity (username or "api_key")

    Raises:
        HTTPException: 401 Unauthorized if authentication fails
    """
    # Check if this route is exempt from authentication
    route_path = request.url.path
    if route_path in EXEMPT_ROUTES:
        return ""

    settings = _settings_mod.get_settings()

    # If no auth is configured at all, disable authentication
    if not _is_auth_configured(settings):
        return ""

    # 1. Check JWT Bearer token
    bearer_token = _extract_bearer_token(request)
    if bearer_token:
        payload = decode_jwt_token(bearer_token, settings)
        if payload and "sub" in payload:
            return payload["sub"]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    # 2. Check JWT session cookie
    cookie_token = request.cookies.get(JWT_COOKIE_NAME)
    if cookie_token:
        payload = decode_jwt_token(cookie_token, settings)
        if payload and "sub" in payload:
            return payload["sub"]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    # 3. Check API key (header or query)
    configured_key = settings.api_key.get_secret_value()
    if configured_key:
        provided_key = header_key or query_key
        if provided_key:
            if secrets.compare_digest(provided_key, configured_key):
                return "api_key"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key.",
            )

    # No valid credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a JWT token or API key.",
    )


# Dependency for endpoints that require authentication
RequireAPIKey = Annotated[str, Depends(verify_api_key)]
