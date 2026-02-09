"""Unit tests for CLI serve command."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli.main import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


class TestServe:
    """Test serve command."""

    def test_serve_default_settings(self, runner):
        """Test serve command with default settings."""
        mock_settings = MagicMock()
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.api_workers = 1

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(app, ["serve"])

            assert result.exit_code == 0
            mock_uvicorn_run.assert_called_once_with(
                "src.api.main:app",
                host="127.0.0.1",
                port=8000,
                reload=False,
                workers=1,
                log_level="info",
            )

    def test_serve_custom_host_port(self, runner):
        """Test serve command with custom host and port."""
        mock_settings = MagicMock()
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.api_workers = 1

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(app, ["serve", "--host", "127.0.0.1", "--port", "9000"])

            assert result.exit_code == 0
            mock_uvicorn_run.assert_called_once_with(
                "src.api.main:app",
                host="127.0.0.1",
                port=9000,
                reload=False,
                workers=1,
                log_level="info",
            )

    def test_serve_with_reload(self, runner):
        """Test serve command with reload enabled."""
        mock_settings = MagicMock()
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.api_workers = 4

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(app, ["serve", "--reload"])

            assert result.exit_code == 0
            # When reload is True, workers should be 1
            mock_uvicorn_run.assert_called_once_with(
                "src.api.main:app",
                host="127.0.0.1",
                port=8000,
                reload=True,
                workers=1,
                log_level="info",
            )

    def test_serve_with_workers(self, runner):
        """Test serve command with custom workers."""
        mock_settings = MagicMock()
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.api_workers = 1

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(app, ["serve", "--workers", "4"])

            assert result.exit_code == 0
            mock_uvicorn_run.assert_called_once_with(
                "src.api.main:app",
                host="127.0.0.1",
                port=8000,
                reload=False,
                workers=4,
                log_level="info",
            )

    def test_serve_all_options(self, runner):
        """Test serve command with all options."""
        mock_settings = MagicMock()
        mock_settings.api_host = "0.0.0.0"
        mock_settings.api_port = 8000
        mock_settings.api_workers = 1

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(
                app,
                ["serve", "--host", "192.168.1.1", "--port", "8080", "--reload", "--workers", "2"],
            )

            assert result.exit_code == 0
            # When reload is True, workers should be 1 regardless of --workers flag
            mock_uvicorn_run.assert_called_once_with(
                "src.api.main:app",
                host="192.168.1.1",
                port=8080,
                reload=True,
                workers=1,
                log_level="info",
            )
