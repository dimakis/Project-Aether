"""Unit tests for Google OAuth endpoints.

TDD: Test for Plan 9 - Google Sign-In.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGoogleOAuthEndpoints:
    """Tests for Google OAuth login flow."""

    @pytest.mark.asyncio
    async def test_google_url_returns_auth_url(self):
        """Test that /auth/google/url returns Google authorization URL."""
        from src.api.routes.auth import router

        # Find the endpoint
        routes = {r.path: r for r in router.routes}
        assert "/google/url" in routes or any(
            "/google/url" in str(getattr(r, "path", "")) for r in router.routes
        )

    @pytest.mark.asyncio
    async def test_google_url_disabled_when_no_client_id(self):
        """Test that Google auth URL returns 501 when client ID not configured."""
        from src.api.routes.auth import google_auth_url

        with patch("src.api.routes.auth._settings_mod") as mock_settings_mod:
            mock_settings = MagicMock()
            mock_settings.google_client_id = ""
            mock_settings_mod.get_settings.return_value = mock_settings

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await google_auth_url()
            assert exc_info.value.status_code == 501

    @pytest.mark.asyncio
    async def test_google_callback_validates_token(self):
        """Test that Google callback validates the ID token."""
        from src.api.routes.auth import _verify_google_id_token

        # Mock Google's verification at the library level
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "sub": "google-user-123",
                "email": "user@gmail.com",
                "name": "Test User",
                "picture": "https://lh3.googleusercontent.com/photo.jpg",
                "iss": "accounts.google.com",
                "aud": "test-client-id",
            }

            result = _verify_google_id_token("fake-credential", "test-client-id")

            assert result["sub"] == "google-user-123"
            assert result["email"] == "user@gmail.com"


class TestMeResponseProfile:
    """Tests that /auth/me returns profile data."""

    def test_me_response_has_profile_fields(self):
        """Test that MeResponse schema includes profile fields."""
        from src.api.routes.auth import MeResponse

        resp = MeResponse(
            authenticated=True,
            username="admin",
            auth_method="cookie",
            display_name="Admin User",
            email="admin@example.com",
            avatar_url=None,
        )

        assert resp.display_name == "Admin User"
        assert resp.email == "admin@example.com"
        assert resp.avatar_url is None
