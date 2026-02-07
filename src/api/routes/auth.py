"""Authentication routes.

Provides login/logout/session endpoints for JWT-based authentication.
Includes HA-verified first-time setup and multiple login methods:
- Password (DB hash first, then env var fallback)
- HA token
- Passkey (handled in passkey.py)
"""

import secrets

import bcrypt
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from src.api.auth import (
    JWT_COOKIE_NAME,
    create_jwt_token,
    decode_jwt_token,
    _extract_bearer_token,
    _get_jwt_secret,
)
from src.api.ha_verify import verify_ha_connection
from src.dal.system_config import SystemConfigRepository, encrypt_token, decrypt_token
from src.storage import get_session
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


class SetupRequest(BaseModel):
    """First-time setup request body."""

    ha_url: str
    ha_token: str
    password: str | None = None


class SetupResponse(BaseModel):
    """Setup response with JWT."""

    token: str
    message: str = "Setup complete"


class SetupStatusResponse(BaseModel):
    """Setup status check response."""

    setup_complete: bool


class HATokenLoginRequest(BaseModel):
    """HA token login request body."""

    ha_token: str


# =============================================================================
# Helper
# =============================================================================


def _set_jwt_cookie(response: Response, token: str, settings) -> None:
    """Set the httpOnly JWT cookie on the response."""
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


# =============================================================================
# Setup Endpoints
# =============================================================================


@router.get("/setup-status", response_model=SetupStatusResponse)
async def setup_status() -> SetupStatusResponse:
    """Check whether initial setup has been completed.

    This endpoint is exempt from authentication so the frontend can
    determine whether to show the setup wizard or login page.
    """
    async with get_session() as session:
        repo = SystemConfigRepository(session)
        complete = await repo.is_setup_complete()
    return SetupStatusResponse(setup_complete=complete)


@router.post("/setup", response_model=SetupResponse)
async def setup(body: SetupRequest, response: Response) -> SetupResponse:
    """First-time system setup.

    Validates HA connection, stores config in DB (encrypted), and returns JWT.
    Returns 409 if setup has already been completed.
    """
    settings = _settings_mod.get_settings()

    async with get_session() as session:
        repo = SystemConfigRepository(session)

        # Guard: already set up
        if await repo.is_setup_complete():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="System is already configured. Setup can only be run once.",
            )

        # Validate HA connection (raises HTTPException on failure)
        await verify_ha_connection(body.ha_url, body.ha_token)

        # Encrypt HA token
        jwt_secret = _get_jwt_secret(settings)
        ha_token_encrypted = encrypt_token(body.ha_token, jwt_secret)

        # Hash password if provided
        password_hash = None
        if body.password:
            password_hash = bcrypt.hashpw(
                body.password.encode(), bcrypt.gensalt()
            ).decode()

        # Store config
        await repo.create_config(
            ha_url=body.ha_url,
            ha_token_encrypted=ha_token_encrypted,
            password_hash=password_hash,
        )
        await session.commit()

    # Issue JWT for the admin user
    username = settings.auth_username
    token = create_jwt_token(username, settings)
    _set_jwt_cookie(response, token, settings)

    # Reset MCP client so it picks up DB config
    try:
        from src.mcp.client import reset_mcp_client
        reset_mcp_client()
    except ImportError:
        pass

    return SetupResponse(token=token)


# =============================================================================
# HA Token Login
# =============================================================================


@router.post("/login/ha-token", response_model=LoginResponse)
async def login_with_ha_token(
    body: HATokenLoginRequest, response: Response
) -> LoginResponse:
    """Authenticate using an HA long-lived access token.

    Validates the provided token against the stored HA URL (from DB or env).
    """
    settings = _settings_mod.get_settings()

    # Determine HA URL to validate against
    ha_url: str | None = None

    # Try DB config first
    async with get_session() as session:
        repo = SystemConfigRepository(session)
        jwt_secret = _get_jwt_secret(settings)
        conn = await repo.get_ha_connection(jwt_secret)
        if conn:
            ha_url = conn[0]

    # Fall back to env var
    if not ha_url:
        ha_url = settings.ha_url

    if not ha_url:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="HA connection not configured.",
        )

    # Validate the token against HA
    await verify_ha_connection(ha_url, body.ha_token)

    # Issue JWT
    username = settings.auth_username
    token = create_jwt_token(username, settings)
    _set_jwt_cookie(response, token, settings)

    return LoginResponse(token=token, username=username, message="Login successful")


# =============================================================================
# Password Login
# =============================================================================


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response) -> LoginResponse:
    """Authenticate with username and password, receive JWT.

    Checks DB password hash first, then falls back to env var AUTH_PASSWORD.
    The JWT is returned both in the response body and as an httpOnly cookie.
    """
    settings = _settings_mod.get_settings()

    # 1. Try DB password hash first
    async with get_session() as session:
        repo = SystemConfigRepository(session)
        config = await repo.get_config()
        if config and config.password_hash:
            if bcrypt.checkpw(body.password.encode(), config.password_hash.encode()):
                # DB password match - username doesn't need to match env var
                token = create_jwt_token(body.username, settings)
                _set_jwt_cookie(response, token, settings)
                return LoginResponse(token=token, username=body.username)

    # 2. Fall back to env var AUTH_PASSWORD
    configured_password = settings.auth_password.get_secret_value()
    if not configured_password:
        # No password configured at all
        # Check if DB config exists (setup was done without password)
        if config is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Password authentication is not configured.",
        )

    # Verify env-var credentials
    configured_username = settings.auth_username
    username_ok = secrets.compare_digest(body.username, configured_username)
    password_ok = secrets.compare_digest(body.password, configured_password)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    # Create JWT token
    token = create_jwt_token(body.username, settings)
    _set_jwt_cookie(response, token, settings)

    return LoginResponse(token=token, username=body.username)


# =============================================================================
# Session Endpoints
# =============================================================================


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
