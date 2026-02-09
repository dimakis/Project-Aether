"""WebAuthn passkey routes.

Provides registration and authentication endpoints for passkey (Face ID / Touch ID)
login. Uses py_webauthn for server-side WebAuthn operations.

Registration flow (requires active JWT session):
1. POST /passkey/register/options -> returns challenge
2. POST /passkey/register/verify  -> stores credential

Authentication flow (public):
1. POST /passkey/authenticate/options -> returns challenge
2. POST /passkey/authenticate/verify  -> returns JWT

Management (requires active JWT session):
- GET  /passkeys          -> list registered passkeys
- DELETE /passkeys/{id}   -> remove a passkey
"""

import base64
import logging
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

import src.settings as _settings_mod
from src.api.auth import (
    JWT_COOKIE_NAME,
    _extract_bearer_token,
    create_jwt_token,
    decode_jwt_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory challenge store (short-lived, keyed by username)
# Challenges are ephemeral (60s TTL) so in-memory is acceptable even
# with multiple workers -- worst case, user retries the challenge step.
_challenge_store: dict[str, bytes] = {}


# =============================================================================
# Credential storage helpers (DB-backed via PasskeyCredential model)
# =============================================================================


async def get_credentials_for_user(username: str) -> list[dict]:
    """Get all stored credentials for a user from the database.

    Returns list of dicts with keys: id, credential_id, public_key,
    sign_count, transports, device_name, last_used_at, username.
    """
    from sqlalchemy import select

    from src.storage import get_session
    from src.storage.entities.passkey_credential import PasskeyCredential

    async with get_session() as session:
        result = await session.execute(
            select(PasskeyCredential).where(PasskeyCredential.username == username)
        )
        credentials = result.scalars().all()
        return [
            {
                "id": str(c.id),
                "credential_id": c.credential_id,
                "public_key": c.public_key,
                "sign_count": c.sign_count,
                "transports": c.transports,
                "device_name": c.device_name,
                "username": c.username,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
            }
            for c in credentials
        ]


async def store_credential(credential: dict) -> None:
    """Store a new credential in the database."""
    from src.storage import get_session
    from src.storage.entities.passkey_credential import PasskeyCredential

    async with get_session() as session:
        db_credential = PasskeyCredential(
            credential_id=credential["credential_id"],
            public_key=credential["public_key"],
            sign_count=credential["sign_count"],
            transports=credential.get("transports"),
            device_name=credential.get("device_name"),
            username=credential["username"],
        )
        session.add(db_credential)
        await session.commit()


async def get_credential_by_id(credential_id: bytes) -> dict | None:
    """Look up a credential by its WebAuthn credential ID from the database."""
    from sqlalchemy import select

    from src.storage import get_session
    from src.storage.entities.passkey_credential import PasskeyCredential

    async with get_session() as session:
        result = await session.execute(
            select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id)
        )
        c = result.scalar_one_or_none()
        if not c:
            return None
        return {
            "id": str(c.id),
            "credential_id": c.credential_id,
            "public_key": c.public_key,
            "sign_count": c.sign_count,
            "transports": c.transports,
            "device_name": c.device_name,
            "username": c.username,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
        }


async def update_credential_sign_count(credential_id: bytes, new_count: int) -> None:
    """Update the sign count for replay protection in the database."""
    from sqlalchemy import select

    from src.storage import get_session
    from src.storage.entities.passkey_credential import PasskeyCredential

    async with get_session() as session:
        result = await session.execute(
            select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id)
        )
        credential = result.scalar_one_or_none()
        if credential:
            credential.sign_count = new_count
            credential.last_used_at = datetime.now(UTC)
            await session.commit()


async def delete_credential_by_uuid(uuid_str: str) -> bool:
    """Delete a credential by its UUID. Returns True if found and deleted."""
    from sqlalchemy import select

    from src.storage import get_session
    from src.storage.entities.passkey_credential import PasskeyCredential

    async with get_session() as session:
        result = await session.execute(
            select(PasskeyCredential).where(PasskeyCredential.id == uuid_str)
        )
        credential = result.scalar_one_or_none()
        if not credential:
            return False
        await session.delete(credential)
        await session.commit()
        return True


# =============================================================================
# Request / Response Schemas
# =============================================================================


class RegisterVerifyRequest(BaseModel):
    """WebAuthn registration response from the browser."""

    credential: dict
    device_name: str | None = Field(default=None, max_length=100)


class AuthenticateVerifyRequest(BaseModel):
    """WebAuthn authentication response from the browser."""

    credential: dict


class PasskeyInfo(BaseModel):
    """Public info about a registered passkey."""

    id: str
    device_name: str | None
    created_at: str | None
    last_used_at: str | None


class PasskeyListResponse(BaseModel):
    """List of registered passkeys."""

    passkeys: list[PasskeyInfo]


# =============================================================================
# Helper to extract current username from JWT
# =============================================================================


def _get_current_username(request: Request) -> str | None:
    """Extract username from JWT in request (Bearer or cookie)."""
    settings = _settings_mod.get_settings()

    token = _extract_bearer_token(request)
    if not token:
        token = request.cookies.get(JWT_COOKIE_NAME)
    if not token:
        return None

    payload = decode_jwt_token(token, settings)
    if payload and "sub" in payload:
        return cast("str", payload["sub"])
    return None


# =============================================================================
# Registration Endpoints
# =============================================================================


@router.post("/passkey/register/options")
async def passkey_register_options(request: Request) -> dict[str, Any]:
    """Generate WebAuthn registration options (challenge).

    Requires active JWT session. Returns options for the browser's
    navigator.credentials.create() call.
    """
    username = _get_current_username(request)
    if not username:
        raise HTTPException(
            status_code=401, detail="Authentication required to register a passkey."
        )

    settings = _settings_mod.get_settings()

    # Get existing credentials to exclude (prevent re-registration)
    existing = await get_credentials_for_user(username)
    exclude_credentials = [
        PublicKeyCredentialDescriptor(
            id=c["credential_id"],
            type=PublicKeyCredentialType.PUBLIC_KEY,
            transports=c.get("transports"),
        )
        for c in existing
    ]

    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_id=username.encode(),
        user_name=username,
        user_display_name=username,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        supported_pub_key_algs=[
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ],
    )

    # Store challenge for verification
    _challenge_store[username] = options.challenge

    # Serialize to JSON-friendly dict
    return _options_to_dict(options)


@router.post("/passkey/register/verify")
async def passkey_register_verify(body: RegisterVerifyRequest, request: Request) -> dict:
    """Verify WebAuthn registration response and store credential.

    Requires active JWT session.
    """
    username = _get_current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required.")

    settings = _settings_mod.get_settings()
    challenge = _challenge_store.pop(username, None)
    if not challenge:
        raise HTTPException(status_code=400, detail="No registration challenge found. Start over.")

    try:
        verification = verify_registration_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
            require_user_verification=False,
        )
    except Exception as e:
        logger.warning("Passkey registration verification failed: %s", e)
        raise HTTPException(
            status_code=400, detail="Registration failed. Please try again."
        ) from None

    # Store credential
    import uuid

    await store_credential(
        {
            "id": str(uuid.uuid4()),
            "username": username,
            "credential_id": verification.credential_id,
            "public_key": verification.credential_public_key,
            "sign_count": verification.sign_count,
            "transports": body.credential.get("response", {}).get("transports"),
            "device_name": body.device_name,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
        }
    )

    return {"status": "ok", "message": "Passkey registered successfully"}


# =============================================================================
# Authentication Endpoints
# =============================================================================


@router.post("/passkey/authenticate/options")
async def passkey_authenticate_options() -> dict:
    """Generate WebAuthn authentication options (challenge).

    This is a public endpoint (no auth required) - it's the entry point
    for passkey login.
    """
    settings = _settings_mod.get_settings()
    username = settings.auth_username

    # Get credentials for the configured user
    existing = await get_credentials_for_user(username)
    allow_credentials = [
        PublicKeyCredentialDescriptor(
            id=c["credential_id"],
            type=PublicKeyCredentialType.PUBLIC_KEY,
            transports=c.get("transports"),
        )
        for c in existing
    ]

    options = generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        allow_credentials=allow_credentials if allow_credentials else None,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    # Store challenge
    _challenge_store[f"auth:{username}"] = options.challenge

    return _options_to_dict(options)


@router.post("/passkey/authenticate/verify")
async def passkey_authenticate_verify(
    body: AuthenticateVerifyRequest,
    response: Response,
) -> dict:
    """Verify WebAuthn authentication response and return JWT.

    This is a public endpoint - successful verification grants a JWT session.
    """
    settings = _settings_mod.get_settings()
    username = settings.auth_username
    challenge = _challenge_store.pop(f"auth:{username}", None)
    if not challenge:
        raise HTTPException(status_code=400, detail="No authentication challenge found.")

    # Find the credential
    raw_id = body.credential.get("rawId") or body.credential.get("id", "")
    raw_id_bytes = base64.urlsafe_b64decode(raw_id + "==") if isinstance(raw_id, str) else raw_id

    stored_cred = await get_credential_by_id(raw_id_bytes)
    if not stored_cred:
        raise HTTPException(status_code=400, detail="Unknown credential.")

    try:
        verification = verify_authentication_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
            credential_public_key=stored_cred["public_key"],
            credential_current_sign_count=stored_cred["sign_count"],
            require_user_verification=False,
        )
    except Exception as e:
        logger.warning("Passkey authentication failed: %s", e)
        raise HTTPException(
            status_code=401, detail="Authentication failed. Please try again."
        ) from None

    # Update sign count
    await update_credential_sign_count(
        stored_cred["credential_id"],
        verification.new_sign_count,
    )

    # Create JWT
    token = create_jwt_token(username, settings)

    # Set cookie
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

    return {"token": token, "username": username, "message": "Passkey authentication successful"}


# =============================================================================
# Passkey Management Endpoints
# =============================================================================


@router.get("/passkeys", response_model=PasskeyListResponse)
async def list_passkeys(request: Request) -> PasskeyListResponse:
    """List all registered passkeys for the current user."""
    username = _get_current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required.")

    credentials = await get_credentials_for_user(username)
    return PasskeyListResponse(
        passkeys=[
            PasskeyInfo(
                id=c["id"],
                device_name=c.get("device_name"),
                created_at=c.get("created_at"),
                last_used_at=c.get("last_used_at"),
            )
            for c in credentials
        ]
    )


@router.delete("/passkeys/{passkey_id}")
async def delete_passkey(passkey_id: str, request: Request) -> dict:
    """Delete a registered passkey."""
    username = _get_current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required.")

    deleted = await delete_credential_by_uuid(passkey_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Passkey not found.")

    return {"status": "ok", "message": "Passkey deleted"}


# =============================================================================
# Helpers
# =============================================================================


def _options_to_dict(options: Any) -> dict[str, Any]:
    """Convert WebAuthn options object to a JSON-serializable dict.

    py_webauthn returns dataclass-like objects; we convert to dict with
    base64url-encoded binary fields for the browser.
    """
    import json as _json

    from webauthn.helpers import options_to_json

    # options_to_json returns a JSON string
    return cast("dict[str, Any]", _json.loads(options_to_json(options)))
