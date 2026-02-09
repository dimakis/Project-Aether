"""Unit tests for CLI status commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from src.cli.main import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_session():
    """Mock database session."""
    return AsyncMock()


class TestStatus:
    """Test status command."""

    def test_status_api_success(self, runner):
        """Test status command when API is available."""
        mock_response_data = {
            "status": "healthy",
            "environment": "test",
            "version": "0.1.0",
            "uptime_seconds": 3600,
            "components": [
                {
                    "name": "database",
                    "status": "healthy",
                    "message": "Connected",
                    "latency_ms": 5.2,
                },
                {
                    "name": "mlflow",
                    "status": "healthy",
                    "message": "Running",
                    "latency_ms": 10.1,
                },
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        with (
            patch("src.settings.get_settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_settings.return_value.api_host = "localhost"
            mock_settings.return_value.api_port = 8000

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            assert "Overall Status" in result.stdout
            assert "healthy" in result.stdout

    def test_status_api_not_running(self, runner, mock_session):
        """Test status command when API is not running."""
        with (
            patch("src.settings.get_settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_settings.return_value.api_host = "localhost"
            mock_settings.return_value.api_port = 8000

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_class.return_value = mock_client

            with patch("src.storage.get_session") as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

                with patch("sqlalchemy.text"):
                    result = runner.invoke(app, ["status"])

                    assert result.exit_code == 0
                    assert "API server not running" in result.stdout

    def test_status_direct_check_success(self, runner, mock_session):
        """Test status command checking components directly."""
        with (
            patch("src.settings.get_settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_settings.return_value.api_host = "localhost"
            mock_settings.return_value.api_port = 8000

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_class.return_value = mock_client

            with patch("src.storage.get_session") as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_execute = AsyncMock()
                mock_session.execute = mock_execute

                with patch("sqlalchemy.text"):
                    result = runner.invoke(app, ["status"])

                    assert result.exit_code == 0
                    assert "Components" in result.stdout

    def test_status_direct_check_db_error(self, runner, mock_session):
        """Test status command with database error."""
        with (
            patch("src.settings.get_settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_settings.return_value.api_host = "localhost"
            mock_settings.return_value.api_port = 8000

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_class.return_value = mock_client

            with patch("src.storage.get_session") as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session
                mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_execute = AsyncMock(side_effect=Exception("DB error"))
                mock_session.execute = mock_execute

                with patch("sqlalchemy.text"):
                    result = runner.invoke(app, ["status"])

                    assert result.exit_code == 0
                    assert "unhealthy" in result.stdout or "error" in result.stdout.lower()


class TestVersion:
    """Test version command."""

    def test_version_success(self, runner):
        """Test version command."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "Aether" in result.stdout
        assert "v0.1.0" in result.stdout
