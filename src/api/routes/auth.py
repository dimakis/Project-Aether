"""Authentication routes.

Provides login/logout/session endpoints for JWT-based authentication.
Password credentials are configured via environment variables (single-user).
"""

import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from src.api.auth import (
    JWT_COOKIE_NAME,
    create_jwt_token,
    decode_jwt_token,
    _extract_bearer_token,
)
import src.settings as _settings_mod

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Request / Response Schemas
# =============================================================================


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with token and user info."""

    token: str
    username: str
    message: str = "Login successful"


class MeResponse(BaseModel):
    """Session status response."""

    authenticated: bool
    username: str | None = None
    auth_method: str | None = None
    has_passkeys: bool = False


class LogoutResponse(BaseModel):
    """Logout response."""

    message: str = "Logged out"


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response) -> LoginResponse:
    """Authenticate with username and password, receive JWT.

    The JWT is returned both in the response body and as an httpOnly cookie.
    """
    settings = _settings_mod.get_settings()

    # Check if password auth is configured
    if not settings.auth_password.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Password authentication is not configured. Set AUTH_PASSWORD.",
        )

    # Verify credentials
    configured_username = settings.auth_username
    configured_password = settings.auth_password.get_secret_value()

    # Constant-time comparison for both username and password
    username_ok = secrets.compare_digest(body.username, configured_username)
    password_ok = secrets.compare_digest(body.password, configured_password)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    # Create JWT token
    token = create_jwt_token(body.username, settings)

    # Set httpOnly cookie
    is_production = settings.environment == "production"
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=settings.jwt_expiry_hours * 3600,
        path="/",
    )

    return LoginResponse(token=token, username=body.username)


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response) -> LogoutResponse:
    """Clear the session cookie."""
    response.delete_cookie(
        key=JWT_COOKIE_NAME,
        path="/",
        httponly=True,
    )
    return LogoutResponse()


@router.get("/me", response_model=MeResponse)
async def me(request: Request) -> MeResponse:
    """Check current authentication status.

    Returns user info if authenticated, 401 if not.
    """
    settings = _settings_mod.get_settings()

    # Try JWT Bearer token
    bearer_token = _extract_bearer_token(request)
    if bearer_token:
        payload = decode_jwt_token(bearer_token, settings)
        if payload and "sub" in payload:
            return MeResponse(
                authenticated=True,
                username=payload["sub"],
                auth_method="bearer",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    # Try JWT session cookie
    cookie_token = request.cookies.get(JWT_COOKIE_NAME)
    if cookie_token:
        payload = decode_jwt_token(cookie_token, settings)
        if payload and "sub" in payload:
            return MeResponse(
                authenticated=True,
                username=payload["sub"],
                auth_method="cookie",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    # No valid credentials
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
    )
