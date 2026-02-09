"""Unit tests for Passkey (WebAuthn) API routes.

Tests registration, authentication, and management endpoints.
"""

import base64
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient


def _make_test_app():
    """Create a minimal FastAPI app with the passkey router."""
    from fastapi import FastAPI

    from src.api.routes.passkey import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def passkey_app():
    """Lightweight FastAPI app with passkey routes."""
    return _make_test_app()


@pytest.fixture
async def passkey_client(passkey_app):
    """Async HTTP client wired to the passkey test app."""
    async with AsyncClient(
        transport=ASGITransport(app=passkey_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_credential():
    """Create a mock passkey credential."""
    cred_id = b"test_credential_id"
    return {
        "id": str(uuid4()),
        "credential_id": cred_id,
        "public_key": b"test_public_key",
        "sign_count": 0,
        "transports": ["usb", "nfc"],
        "device_name": "Test Device",
        "username": "testuser",
        "created_at": datetime.now(UTC).isoformat(),
        "last_used_at": None,
    }


@pytest.fixture
def mock_jwt_token():
    """Create a mock JWT token."""
    return "mock.jwt.token"


@pytest.mark.asyncio
class TestRegisterOptions:
    """Tests for POST /api/v1/auth/passkey/register/options."""

    async def test_register_options_success(self, passkey_client, mock_jwt_token):
        """Should return registration options."""
        with (
            patch("src.api.routes.passkey._get_current_username") as mock_get_username,
            patch("src.api.routes.passkey.get_credentials_for_user") as mock_get_creds,
            patch("src.settings.get_settings") as mock_get_settings,
            patch("src.api.routes.passkey.generate_registration_options") as mock_gen_options,
        ):
            mock_get_username.return_value = "testuser"
            mock_get_creds.return_value = []
            mock_settings = MagicMock()
            mock_settings.webauthn_rp_id = "localhost"
            mock_settings.webauthn_rp_name = "Test App"
            mock_get_settings.return_value = mock_settings

            mock_options = MagicMock()
            mock_options.challenge = b"test_challenge"
            mock_gen_options.return_value = mock_options

            with patch(
                "webauthn.helpers.options_to_json",
                return_value='{"challenge": "dGVzdF9jaGFsbGVuZ2U"}',
            ):
                response = await passkey_client.post(
                    "/api/v1/auth/passkey/register/options",
                    headers={"Authorization": f"Bearer {mock_jwt_token}"},
                )

            assert response.status_code == 200
            assert "challenge" in response.json()

    async def test_register_options_unauthorized(self, passkey_client):
        """Should return 401 when not authenticated."""
        with patch("src.api.routes.passkey._get_current_username") as mock_get_username:
            mock_get_username.return_value = None

            response = await passkey_client.post("/api/v1/auth/passkey/register/options")

            assert response.status_code == 401


@pytest.mark.asyncio
class TestRegisterVerify:
    """Tests for POST /api/v1/auth/passkey/register/verify."""

    async def test_register_verify_success(
        self, passkey_client, mock_session, mock_jwt_token, mock_credential
    ):
        """Should verify and store credential."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.passkey._get_current_username") as mock_get_username,
            patch("src.api.routes.passkey._challenge_store", {"testuser": b"test_challenge"}),
            patch("src.api.routes.passkey.verify_registration_response") as mock_verify,
            patch("src.storage.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.passkey.store_credential"),
        ):
            mock_get_username.return_value = "testuser"

            mock_verification = MagicMock()
            mock_verification.credential_id = mock_credential["credential_id"]
            mock_verification.credential_public_key = mock_credential["public_key"]
            mock_verification.sign_count = 0
            mock_verify.return_value = mock_verification

            response = await passkey_client.post(
                "/api/v1/auth/passkey/register/verify",
                json={
                    "credential": {"id": "test_id", "response": {"transports": ["usb"]}},
                    "device_name": "Test Device",
                },
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    async def test_register_verify_no_challenge(self, passkey_client, mock_jwt_token):
        """Should return 400 when no challenge found."""
        with (
            patch("src.api.routes.passkey._get_current_username") as mock_get_username,
            patch("src.api.routes.passkey._challenge_store", {}),
        ):
            mock_get_username.return_value = "testuser"

            response = await passkey_client.post(
                "/api/v1/auth/passkey/register/verify",
                json={"credential": {"id": "test_id"}},
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

            assert response.status_code == 400

    async def test_register_verify_verification_failed(self, passkey_client, mock_jwt_token):
        """Should return 400 when verification fails."""
        with (
            patch("src.api.routes.passkey._get_current_username") as mock_get_username,
            patch("src.api.routes.passkey._challenge_store", {"testuser": b"test_challenge"}),
            patch("src.api.routes.passkey.verify_registration_response") as mock_verify,
        ):
            mock_get_username.return_value = "testuser"
            mock_verify.side_effect = Exception("Verification failed")

            response = await passkey_client.post(
                "/api/v1/auth/passkey/register/verify",
                json={"credential": {"id": "test_id"}},
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

            assert response.status_code == 400


@pytest.mark.asyncio
class TestAuthenticateOptions:
    """Tests for POST /api/v1/auth/passkey/authenticate/options."""

    async def test_authenticate_options_success(self, passkey_client, mock_credential):
        """Should return authentication options."""
        with (
            patch("src.settings.get_settings") as mock_get_settings,
            patch("src.api.routes.passkey.get_credentials_for_user") as mock_get_creds,
            patch("src.api.routes.passkey.generate_authentication_options") as mock_gen_options,
        ):
            mock_settings = MagicMock()
            mock_settings.webauthn_rp_id = "localhost"
            mock_settings.auth_username = "testuser"
            mock_get_settings.return_value = mock_settings

            mock_get_creds.return_value = [mock_credential]

            mock_options = MagicMock()
            mock_options.challenge = b"test_challenge"
            mock_gen_options.return_value = mock_options

            with patch(
                "webauthn.helpers.options_to_json",
                return_value='{"challenge": "dGVzdF9jaGFsbGVuZ2U"}',
            ):
                response = await passkey_client.post(
                    "/api/v1/auth/passkey/authenticate/options"
                )

            assert response.status_code == 200
            assert "challenge" in response.json()


@pytest.mark.asyncio
class TestAuthenticateVerify:
    """Tests for POST /api/v1/auth/passkey/authenticate/verify."""

    async def test_authenticate_verify_success(self, passkey_client, mock_session, mock_credential):
        """Should verify authentication and return JWT."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        cred_id_b64 = (
            base64.urlsafe_b64encode(mock_credential["credential_id"]).decode().rstrip("=")
        )

        with (
            patch("src.settings.get_settings") as mock_get_settings,
            patch("src.api.routes.passkey._challenge_store", {"auth:testuser": b"test_challenge"}),
            patch("src.api.routes.passkey.get_credential_by_id") as mock_get_cred,
            patch("src.api.routes.passkey.verify_authentication_response") as mock_verify,
            patch("src.storage.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.passkey.update_credential_sign_count"),
            patch("src.api.routes.passkey.create_jwt_token") as mock_create_jwt,
        ):
            mock_settings = MagicMock()
            mock_settings.webauthn_rp_id = "localhost"
            mock_settings.webauthn_origin = "http://localhost"
            mock_settings.auth_username = "testuser"
            mock_settings.environment = "development"
            mock_settings.jwt_expiry_hours = 24
            mock_get_settings.return_value = mock_settings

            mock_get_cred.return_value = mock_credential

            mock_verification = MagicMock()
            mock_verification.new_sign_count = 1
            mock_verify.return_value = mock_verification

            mock_create_jwt.return_value = "test.jwt.token"

            response = await passkey_client.post(
                "/api/v1/auth/passkey/authenticate/verify",
                json={"credential": {"id": cred_id_b64, "rawId": cred_id_b64}},
            )

            assert response.status_code == 200
            data = response.json()
            assert "token" in data
            assert data["username"] == "testuser"

    async def test_authenticate_verify_no_challenge(self, passkey_client):
        """Should return 400 when no challenge found."""
        with (
            patch("src.settings.get_settings") as mock_get_settings,
            patch("src.api.routes.passkey._challenge_store", {}),
        ):
            mock_settings = MagicMock()
            mock_settings.auth_username = "testuser"
            mock_get_settings.return_value = mock_settings

            response = await passkey_client.post(
                "/api/v1/auth/passkey/authenticate/verify",
                json={"credential": {"id": "test_id"}},
            )

            assert response.status_code == 400

    async def test_authenticate_verify_unknown_credential(self, passkey_client, mock_credential):
        """Should return 400 when credential not found."""
        cred_id_b64 = (
            base64.urlsafe_b64encode(mock_credential["credential_id"]).decode().rstrip("=")
        )

        with (
            patch("src.settings.get_settings") as mock_get_settings,
            patch("src.api.routes.passkey._challenge_store", {"auth:testuser": b"test_challenge"}),
            patch("src.api.routes.passkey.get_credential_by_id") as mock_get_cred,
        ):
            mock_settings = MagicMock()
            mock_settings.auth_username = "testuser"
            mock_get_settings.return_value = mock_settings

            mock_get_cred.return_value = None

            response = await passkey_client.post(
                "/api/v1/auth/passkey/authenticate/verify",
                json={"credential": {"id": cred_id_b64}},
            )

            assert response.status_code == 400

    async def test_authenticate_verify_failed(self, passkey_client, mock_credential):
        """Should return 401 when verification fails."""
        cred_id_b64 = (
            base64.urlsafe_b64encode(mock_credential["credential_id"]).decode().rstrip("=")
        )

        with (
            patch("src.settings.get_settings") as mock_get_settings,
            patch("src.api.routes.passkey._challenge_store", {"auth:testuser": b"test_challenge"}),
            patch("src.api.routes.passkey.get_credential_by_id") as mock_get_cred,
            patch("src.api.routes.passkey.verify_authentication_response") as mock_verify,
        ):
            mock_settings = MagicMock()
            mock_settings.webauthn_rp_id = "localhost"
            mock_settings.webauthn_origin = "http://localhost"
            mock_settings.auth_username = "testuser"
            mock_get_settings.return_value = mock_settings

            mock_get_cred.return_value = mock_credential
            mock_verify.side_effect = Exception("Verification failed")

            response = await passkey_client.post(
                "/api/v1/auth/passkey/authenticate/verify",
                json={"credential": {"id": cred_id_b64}},
            )

            assert response.status_code == 401


@pytest.mark.asyncio
class TestListPasskeys:
    """Tests for GET /api/v1/auth/passkeys."""

    async def test_list_passkeys_success(self, passkey_client, mock_credential, mock_jwt_token):
        """Should return list of registered passkeys."""
        with (
            patch("src.api.routes.passkey._get_current_username") as mock_get_username,
            patch("src.api.routes.passkey.get_credentials_for_user") as mock_get_creds,
        ):
            mock_get_username.return_value = "testuser"
            mock_get_creds.return_value = [mock_credential]

            response = await passkey_client.get(
                "/api/v1/auth/passkeys",
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["passkeys"]) == 1
            assert data["passkeys"][0]["id"] == mock_credential["id"]

    async def test_list_passkeys_unauthorized(self, passkey_client):
        """Should return 401 when not authenticated."""
        with patch("src.api.routes.passkey._get_current_username") as mock_get_username:
            mock_get_username.return_value = None

            response = await passkey_client.get("/api/v1/auth/passkeys")

            assert response.status_code == 401


@pytest.mark.asyncio
class TestDeletePasskey:
    """Tests for DELETE /api/v1/auth/passkeys/{passkey_id}."""

    async def test_delete_passkey_success(
        self, passkey_client, mock_session, mock_jwt_token, mock_credential
    ):
        """Should delete a passkey."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.passkey._get_current_username") as mock_get_username,
            patch("src.storage.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.passkey.delete_credential_by_uuid") as mock_delete,
        ):
            mock_get_username.return_value = "testuser"
            mock_delete.return_value = True

            response = await passkey_client.delete(
                f"/api/v1/auth/passkeys/{mock_credential['id']}",
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    async def test_delete_passkey_not_found(self, passkey_client, mock_session, mock_jwt_token):
        """Should return 404 when passkey not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.passkey._get_current_username") as mock_get_username,
            patch("src.storage.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.passkey.delete_credential_by_uuid") as mock_delete,
        ):
            mock_get_username.return_value = "testuser"
            mock_delete.return_value = False

            response = await passkey_client.delete(
                "/api/v1/auth/passkeys/nonexistent",
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

            assert response.status_code == 404

    async def test_delete_passkey_unauthorized(self, passkey_client):
        """Should return 401 when not authenticated."""
        with patch("src.api.routes.passkey._get_current_username") as mock_get_username:
            mock_get_username.return_value = None

            response = await passkey_client.delete("/api/v1/auth/passkeys/test-id")

            assert response.status_code == 401
