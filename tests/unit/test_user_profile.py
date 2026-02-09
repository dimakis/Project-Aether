"""Unit tests for user profile model and repository.

TDD: Test for Plan 9 - User Profile table.
"""


class TestUserProfileModel:
    """Test UserProfile entity model."""

    def test_create_user_profile(self):
        """Test creating a UserProfile instance."""
        from src.storage.entities.user_profile import UserProfile

        profile = UserProfile(
            id="test-uuid",
            username="admin",
            display_name="Admin User",
            email="admin@example.com",
            avatar_url=None,
            google_sub=None,
        )

        assert profile.username == "admin"
        assert profile.display_name == "Admin User"
        assert profile.email == "admin@example.com"
        assert profile.avatar_url is None
        assert profile.google_sub is None

    def test_user_profile_google_fields(self):
        """Test UserProfile with Google OAuth fields."""
        from src.storage.entities.user_profile import UserProfile

        profile = UserProfile(
            id="test-uuid",
            username="google_user",
            display_name="Google User",
            email="user@gmail.com",
            avatar_url="https://lh3.googleusercontent.com/photo.jpg",
            google_sub="123456789",
        )

        assert profile.google_sub == "123456789"
        assert profile.avatar_url == "https://lh3.googleusercontent.com/photo.jpg"

    def test_user_profile_repr(self):
        """Test UserProfile repr."""
        from src.storage.entities.user_profile import UserProfile

        profile = UserProfile(
            id="test-uuid",
            username="admin",
            display_name="Admin",
        )

        assert "admin" in repr(profile)


class TestGoogleOAuthSettings:
    """Test that Google OAuth settings are available."""

    def test_google_client_id_setting(self):
        """Test that google_client_id is defined in settings."""
        from src.settings import Settings

        # Create settings with defaults
        settings = Settings(
            _env_file=None,
            ha_url="http://localhost:8123",
            ha_token="test",
        )

        assert hasattr(settings, "google_client_id")
        assert settings.google_client_id == ""

    def test_google_client_secret_setting(self):
        """Test that google_client_secret is defined in settings."""
        from src.settings import Settings

        settings = Settings(
            _env_file=None,
            ha_url="http://localhost:8123",
            ha_token="test",
        )

        assert hasattr(settings, "google_client_secret")
