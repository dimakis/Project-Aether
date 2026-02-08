"""CLI entry point and base commands.

Provides the main CLI application with commands for:
- serve: Run the API server
- discover: Trigger entity discovery
- chat: Interactive chat with the Architect agent
- analyze: Run analysis with the Data Science team
- proposals: Manage automation proposals
"""

# Suppress noisy MLflow type hint warnings
# These warnings come from MLflow's own internal types (ResponsesAgentRequest),
# not our code - it's a bug in MLflow itself
import logging
import warnings

# Suppress MLflow type hint warnings (they use Python warnings module)
warnings.filterwarnings("ignore", message=".*Union type hint.*AnyType.*")
warnings.filterwarnings("ignore", message=".*MLflow doesn't validate.*")

# Also suppress via logging (belt and suspenders)
_mlflow_logger = logging.getLogger("mlflow.types.type_hints")
_mlflow_logger.setLevel(logging.ERROR)
_mlflow_logger.addHandler(logging.NullHandler())

# Configure logging early before other imports
import src.logging_config  # noqa: F401

import typer

# Import command modules
from src.cli.commands import analyze as analyze_commands
from src.cli.commands import chat as chat_commands
from src.cli.commands import discover as discover_commands
from src.cli.commands import list as list_commands
from src.cli.commands import proposals as proposals_commands
from src.cli.commands import serve as serve_commands
from src.cli.commands import status as status_commands

# Create main Typer app
app = typer.Typer(
    name="aether",
    help="Agentic Home Automation System for Home Assistant",
    add_completion=False,
    no_args_is_help=True,
)

# Register top-level commands
app.command()(serve_commands.serve)
app.command()(discover_commands.discover)
app.command()(chat_commands.chat)
app.command()(analyze_commands.analyze)
app.command()(analyze_commands.insights)
app.command(name="insight")(analyze_commands.show_insight)
app.command()(analyze_commands.optimize)
app.command()(status_commands.status)
app.command()(status_commands.version)

# Register list commands
app.command()(list_commands.entities)
app.command()(list_commands.areas)
app.command()(list_commands.devices)
app.command()(list_commands.automations)
app.command()(list_commands.scripts)
app.command()(list_commands.scenes)
app.command()(list_commands.services)
app.command(name="seed-services")(list_commands.seed_services_cmd)
app.command(name="ha-gaps")(list_commands.mcp_gaps)

# Register proposals as a sub-command group
app.add_typer(proposals_commands.app, name="proposals")


# Entry point for: python -m src.cli.main
if __name__ == "__main__":
    app()
