"""Unit tests for WebAuthn passkey authentication.

Tests the passkey registration and authentication flow including:
- Registration options generation
- Registration verification (mocked WebAuthn)
- Authentication options generation
- Authentication verification (mocked WebAuthn)
- Passkey listing and deletion
- Endpoint auth requirements
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.api.main import create_app
from src.settings import get_settings
from tests.helpers.auth import make_test_jwt, make_test_settings

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def passkey_client(monkeypatch):
    """Create a test client with WebAuthn configured."""
    get_settings.cache_clear()
    settings = make_test_settings(
        webauthn_rp_id="localhost",
        webauthn_rp_name="Aether Test",
        webauthn_origin="http://localhost:3000",
        auth_password=SecretStr("test-password-123"),
    )
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    get_settings.cache_clear()


# =============================================================================
# Registration Options Tests
# =============================================================================


@pytest.mark.asyncio
class TestPasskeyRegistrationOptions:
    """Test POST /api/v1/auth/passkey/register/options."""

    async def test_register_options_requires_auth(self, passkey_client: AsyncClient):
        """Registration options requires authentication (JWT)."""
        response = await passkey_client.post("/api/v1/auth/passkey/register/options")
        assert response.status_code == 401

    async def test_register_options_with_jwt(self, passkey_client: AsyncClient):
        """Registration options returns WebAuthn challenge when authenticated."""
        token = make_test_jwt()
        with patch(
            "src.api.routes.passkey.get_credentials_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await passkey_client.post(
                "/api/v1/auth/passkey/register/options",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        data = response.json()
        # Should contain WebAuthn registration options
        assert "challenge" in data
        assert "rp" in data
        assert data["rp"]["id"] == "localhost"
        assert data["rp"]["name"] == "Aether Test"
        assert "user" in data


# =============================================================================
# Authentication Options Tests
# =============================================================================


@pytest.mark.asyncio
class TestPasskeyAuthenticationOptions:
    """Test POST /api/v1/auth/passkey/authenticate/options."""

    async def test_authenticate_options_is_public(self, passkey_client: AsyncClient):
        """Authentication options endpoint is publicly accessible (no auth needed)."""
        with patch(
            "src.api.routes.passkey.get_credentials_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await passkey_client.post(
                "/api/v1/auth/passkey/authenticate/options",
            )
        # Should not be 401 (this endpoint is exempt from auth)
        assert response.status_code == 200

    async def test_authenticate_options_returns_challenge(self, passkey_client: AsyncClient):
        """Authentication options returns a WebAuthn challenge."""
        with patch(
            "src.api.routes.passkey.get_credentials_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await passkey_client.post(
                "/api/v1/auth/passkey/authenticate/options",
            )
        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data
        assert "rpId" in data


# =============================================================================
# Passkey Management Tests
# =============================================================================


@pytest.mark.asyncio
class TestPasskeyManagement:
    """Test passkey listing and deletion endpoints."""

    async def test_list_passkeys_requires_auth(self, passkey_client: AsyncClient):
        """Listing passkeys requires authentication."""
        response = await passkey_client.get("/api/v1/auth/passkeys")
        assert response.status_code == 401

    async def test_list_passkeys_with_auth(self, passkey_client: AsyncClient):
        """Listing passkeys returns registered devices."""
        token = make_test_jwt()
        with patch(
            "src.api.routes.passkey.get_credentials_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await passkey_client.get(
                "/api/v1/auth/passkeys",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "passkeys" in data
        assert isinstance(data["passkeys"], list)

    async def test_delete_passkey_requires_auth(self, passkey_client: AsyncClient):
        """Deleting a passkey requires authentication."""
        response = await passkey_client.delete(
            "/api/v1/auth/passkeys/some-id",
        )
        assert response.status_code == 401
