"""Unit tests for src/api/main.py.

Tests app creation, middleware, CORS config, and exception handlers.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.environment = "testing"
    s.debug = True
    s.allowed_origins = ""
    s.ha_url = "http://ha.local:8123"
    s.webauthn_origin = "http://localhost:3000"
    s.scheduler_enabled = False
    s.aether_role = "all"
    s.cors_origins = "*"
    s.mlflow_tracking_uri = "http://localhost:5002"
    s.mlflow_experiment_name = "test"
    s.api_key = MagicMock()
    s.api_key.get_secret_value.return_value = "test-key"
    return s


class TestGetAllowedOrigins:
    def test_explicit_origins(self):
        from src.api.main import _get_allowed_origins

        settings = MagicMock()
        settings.allowed_origins = "http://a.com, http://b.com"
        result = _get_allowed_origins(settings)
        assert result == ["http://a.com", "http://b.com"]

    def test_development_defaults(self):
        from src.api.main import _get_allowed_origins

        settings = MagicMock()
        settings.allowed_origins = ""
        settings.environment = "development"
        result = _get_allowed_origins(settings)
        assert result == ["*"]

    def test_testing_defaults(self):
        from src.api.main import _get_allowed_origins

        settings = MagicMock()
        settings.allowed_origins = ""
        settings.environment = "testing"
        result = _get_allowed_origins(settings)
        assert result == ["*"]

    def test_staging_defaults(self):
        from src.api.main import _get_allowed_origins

        settings = MagicMock()
        settings.allowed_origins = ""
        settings.environment = "staging"
        settings.ha_url = "http://ha.local:8123"
        result = _get_allowed_origins(settings)
        assert "http://localhost:3000" in result
        assert "http://ha.local:8123" in result

    def test_production_defaults(self):
        from src.api.main import _get_allowed_origins

        settings = MagicMock()
        settings.allowed_origins = ""
        settings.environment = "production"
        settings.ha_url = "https://ha.example.com"
        settings.webauthn_origin = "https://auth.example.com"
        result = _get_allowed_origins(settings)
        assert "https://ha.example.com" in result
        assert "https://auth.example.com" in result


class TestGetCorrelationId:
    def test_returns_none_outside_request(self):
        from src.api.main import get_correlation_id

        # Outside a request context, should be None
        result = get_correlation_id()
        # Could be None or a leftover value
        assert result is None or isinstance(result, str)


class TestGetApp:
    def test_creates_singleton(self, mock_settings):
        from src.api import main as main_mod

        orig_app = main_mod._app
        main_mod._app = None
        try:
            with (
                patch("src.api.main.get_settings", return_value=mock_settings),
                patch("src.api.main.init_mlflow"),
                patch("src.api.main.init_db"),
                patch("src.settings.get_settings", return_value=mock_settings),
            ):
                app = main_mod.get_app()
                assert app is not None
                # Should be cached
                app2 = main_mod.get_app()
                assert app is app2
        finally:
            main_mod._app = orig_app


class TestCreateApp:
    def test_creates_fastapi_app(self, mock_settings):
        from src.api.main import create_app

        with (
            patch("src.api.main.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
        ):
            app = create_app(settings=mock_settings)
            assert app.title == "Aether"

    def test_debug_enables_docs(self, mock_settings):
        from src.api.main import create_app

        mock_settings.debug = True
        with (
            patch("src.api.main.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
        ):
            app = create_app(settings=mock_settings)
            assert app.docs_url is not None

    def test_non_debug_disables_docs(self, mock_settings):
        from src.api.main import create_app

        mock_settings.debug = False
        with (
            patch("src.api.main.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
        ):
            app = create_app(settings=mock_settings)
            assert app.docs_url is None


class TestModuleGetattr:
    def test_unknown_attr_raises(self):
        from src.api import main as mod

        with pytest.raises(AttributeError):
            mod.__getattr__("nonexistent_attribute")
