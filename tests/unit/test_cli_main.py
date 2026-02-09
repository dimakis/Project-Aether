"""Unit tests for CLI main app and utilities."""

import pytest
from typer.testing import CliRunner

from src.cli.main import app
from src.cli.utils import console


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


class TestMainApp:
    """Test main CLI app registration."""

    def test_app_exists(self):
        """Test that app exists."""
        assert app is not None
        assert app.info.name == "aether"

    def test_app_help(self, runner):
        """Test app help command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Agentic Home Automation System" in result.stdout

    def test_app_no_args_shows_help(self, runner):
        """Test that app shows help when no args provided."""
        result = runner.invoke(app, [])

        # Typer returns exit code 2 for no args (shows help)
        assert result.exit_code == 2
        assert "Usage:" in result.stdout or "Commands:" in result.stdout

    def test_all_commands_registered(self, runner):
        """Test that all expected commands are registered."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # Check for key commands
        assert "serve" in result.stdout
        assert "discover" in result.stdout
        assert "chat" in result.stdout
        assert "analyze" in result.stdout
        assert "insights" in result.stdout
        assert "optimize" in result.stdout
        assert "status" in result.stdout
        assert "version" in result.stdout
        assert "entities" in result.stdout
        assert "areas" in result.stdout
        assert "devices" in result.stdout
        assert "automations" in result.stdout
        assert "scripts" in result.stdout
        assert "scenes" in result.stdout
        assert "services" in result.stdout
        assert "proposals" in result.stdout

    def test_proposals_subcommand_group(self, runner):
        """Test that proposals is registered as a subcommand group."""
        result = runner.invoke(app, ["proposals", "--help"])

        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "show" in result.stdout
        assert "approve" in result.stdout
        assert "reject" in result.stdout
        assert "deploy" in result.stdout
        assert "rollback" in result.stdout


class TestCliUtils:
    """Test CLI utility functions."""

    def test_console_exists(self):
        """Test that console utility exists."""
        assert console is not None

    def test_console_is_rich_console(self):
        """Test that console is a Rich Console instance."""
        from rich.console import Console

        assert isinstance(console, Console)
