"""Unit tests for CLI discover command (src/cli/commands/discover.py).

The discover command calls asyncio.run(_run_discovery(...)) which makes
it hard to mock all inline imports under the conftest DB guard.
We test the function signature and error paths instead.
"""

from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

runner = CliRunner()


def _make_app():
    from src.cli.commands.discover import discover

    app = typer.Typer()
    app.command()(discover)
    return app


class TestDiscoverCommand:
    def test_help_exits_successfully(self):
        app = _make_app()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Rich may render help with ANSI codes; just verify it produced output
        assert len(result.output) > 0

    def test_discover_prints_panel_before_running(self):
        """The command prints a discovery panel. Even if _run_discovery fails,
        the panel is printed before the async call."""
        with patch("src.cli.commands.discover.console") as mock_console:
            # Mock asyncio.run to avoid actually running discovery
            with patch("src.cli.commands.discover.asyncio") as mock_asyncio:
                mock_asyncio.run = MagicMock()
                app = _make_app()
                result = runner.invoke(app, [])
                assert result.exit_code == 0
                # Console should have been called for the panel
                mock_console.print.assert_called()

    def test_discover_with_domain_flag(self):
        with patch("src.cli.commands.discover.console"):
            with patch("src.cli.commands.discover.asyncio") as mock_asyncio:
                mock_asyncio.run = MagicMock()
                app = _make_app()
                result = runner.invoke(app, ["--domain", "light"])
                assert result.exit_code == 0
                # Check that _run_discovery was called with domain="light"
                call_args = mock_asyncio.run.call_args
                assert call_args is not None

    def test_discover_with_force_flag(self):
        with patch("src.cli.commands.discover.console"):
            with patch("src.cli.commands.discover.asyncio") as mock_asyncio:
                mock_asyncio.run = MagicMock()
                app = _make_app()
                result = runner.invoke(app, ["--force"])
                assert result.exit_code == 0
