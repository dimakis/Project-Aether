"""Unit tests for src/ha/base.py (BaseHAClient, config, URL handling)."""

from unittest.mock import MagicMock, patch

from src.ha.base import BaseHAClient, HAClientConfig, _try_get_db_config


class TestHAClientConfig:
    def test_required_fields(self):
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        assert cfg.ha_url == "http://ha.local:8123"
        assert cfg.ha_token == "tok"
        assert cfg.timeout == 30
        assert cfg.url_preference == "auto"

    def test_optional_remote(self):
        cfg = HAClientConfig(
            ha_url="http://ha.local:8123",
            ha_url_remote="https://remote.ha.io",
            ha_token="tok",
        )
        assert cfg.ha_url_remote == "https://remote.ha.io"

    def test_custom_timeout(self):
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok", timeout=60)
        assert cfg.timeout == 60


class TestBaseHAClientInit:
    def test_init_with_config(self):
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)
        assert client.config is cfg
        assert client._connected is False

    def test_init_without_config_uses_settings(self):
        mock_settings = MagicMock()
        mock_settings.ha_url = "http://ha.local:8123"
        mock_settings.ha_url_remote = None
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value.return_value = "test-token"

        with (
            patch("src.ha.base.get_settings", return_value=mock_settings),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            client = BaseHAClient()
            assert client.config.ha_url == "http://ha.local:8123"


class TestBuildUrlsToTry:
    def _client_with_pref(self, pref, remote=None):
        cfg = HAClientConfig(
            ha_url="http://local:8123",
            ha_url_remote=remote,
            ha_token="tok",
            url_preference=pref,
        )
        return BaseHAClient(config=cfg)

    def test_auto_local_only(self):
        c = self._client_with_pref("auto")
        urls = c._build_urls_to_try()
        assert urls == ["http://local:8123"]

    def test_auto_with_remote(self):
        c = self._client_with_pref("auto", remote="https://remote:443")
        urls = c._build_urls_to_try()
        assert urls == ["http://local:8123", "https://remote:443"]

    def test_local_preference(self):
        c = self._client_with_pref("local", remote="https://remote:443")
        urls = c._build_urls_to_try()
        assert urls == ["http://local:8123"]

    def test_remote_preference(self):
        c = self._client_with_pref("remote", remote="https://remote:443")
        urls = c._build_urls_to_try()
        assert urls == ["https://remote:443"]

    def test_remote_preference_no_remote(self):
        c = self._client_with_pref("remote")
        urls = c._build_urls_to_try()
        assert urls == ["http://local:8123"]  # fallback


class TestGetUrl:
    def test_uses_active_url(self):
        cfg = HAClientConfig(ha_url="http://local:8123", ha_token="tok")
        c = BaseHAClient(config=cfg)
        c._active_url = "https://remote:443"
        assert c._get_url() == "https://remote:443"

    def test_fallback_to_config(self):
        cfg = HAClientConfig(ha_url="http://local:8123", ha_token="tok")
        c = BaseHAClient(config=cfg)
        assert c._get_url() == "http://local:8123"


class TestTryGetDbConfig:
    def test_returns_none_on_error(self):
        with patch("src.settings.get_settings", side_effect=Exception("no settings")):
            result = _try_get_db_config(MagicMock())
            assert result is None

    def test_returns_none_in_async_context(self):
        result = _try_get_db_config(MagicMock())
        # In test context, typically returns None due to DB guard or other issues
        assert result is None


class TestResolveConfig:
    def test_fallback_to_env(self):
        mock_settings = MagicMock()
        mock_settings.ha_url = "http://local:8123"
        mock_settings.ha_url_remote = None
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value.return_value = "env-token"

        with (
            patch("src.ha.base.get_settings", return_value=mock_settings),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            cfg = BaseHAClient._resolve_config()
            assert cfg.ha_token == "env-token"

    def test_uses_db_config_when_available(self):
        mock_settings = MagicMock()
        mock_settings.ha_url_remote = "https://remote.ha.io"

        with (
            patch("src.ha.base.get_settings", return_value=mock_settings),
            patch(
                "src.ha.base._try_get_db_config",
                return_value=("http://db-url:8123", "db-token"),
            ),
        ):
            cfg = BaseHAClient._resolve_config()
            assert cfg.ha_url == "http://db-url:8123"
            assert cfg.ha_token == "db-token"
