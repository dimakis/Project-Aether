"""CLI entry point and base commands.

Provides the main CLI application with commands for:
- serve: Run the API server
- discover: Trigger entity discovery
- chat: Interactive chat with the Architect agent
"""

import asyncio
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="aether",
    help="Agentic Home Automation System for Home Assistant",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="Host to bind to"),
    ] = "0.0.0.0",  # noqa: S104
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to bind to"),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option("--reload", "-r", help="Enable auto-reload for development"),
    ] = False,
    workers: Annotated[
        int,
        typer.Option("--workers", "-w", help="Number of worker processes"),
    ] = 1,
) -> None:
    """Start the Aether API server.

    Runs the FastAPI application with uvicorn.
    """
    import uvicorn

    console.print(
        Panel(
            f"[bold green]Starting Aether API Server[/bold green]\n"
            f"Host: {host}\n"
            f"Port: {port}\n"
            f"Workers: {workers}\n"
            f"Reload: {reload}",
            title="🏠 Aether",
            border_style="green",
        )
    )

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_level="info",
    )


@app.command()
def discover(
    domain: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--domain", "-d", help="Specific domain to discover (e.g., 'light')"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force full re-discovery"),
    ] = False,
) -> None:
    """Run entity discovery from Home Assistant.

    Connects to Home Assistant via MCP and discovers all entities,
    storing them in the local database for the agents to use.
    """
    console.print(
        Panel(
            "[bold blue]Starting Entity Discovery[/bold blue]\n"
            f"Domain filter: {domain or 'all'}\n"
            f"Force: {force}",
            title="🔍 Discovery",
            border_style="blue",
        )
    )

    asyncio.run(_run_discovery(domain, force))


async def _run_discovery(domain: str | None, force: bool) -> None:
    """Execute the discovery workflow."""
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table

    from src.dal.sync import run_discovery
    from src.mcp import get_mcp_client
    from src.storage import get_session

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Connecting to Home Assistant...", total=None)

        try:
            # Get MCP client and verify connection
            mcp = get_mcp_client()
            progress.update(task, description="Fetching entities from Home Assistant...")

            async with get_session() as session:
                discovery = await run_discovery(
                    session=session,
                    mcp_client=mcp,
                    triggered_by="cli",
                )

            progress.update(task, description="Discovery complete!")

        except Exception as e:
            progress.stop()
            console.print(f"[red]❌ Discovery failed: {e}[/red]")
            return

    # Show results
    table = Table(title="Discovery Results", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Entities Found", str(discovery.entities_found))
    table.add_row("Entities Added", str(discovery.entities_added))
    table.add_row("Entities Updated", str(discovery.entities_updated))
    table.add_row("Entities Removed", str(discovery.entities_removed))
    table.add_row("Areas Found", str(discovery.areas_found))
    table.add_row("Devices Found", str(discovery.devices_found))

    if discovery.duration_seconds:
        table.add_row("Duration", f"{discovery.duration_seconds:.2f}s")

    console.print(table)

    # Show domain breakdown
    if discovery.domain_counts:
        domain_table = Table(title="Entities by Domain", show_header=True)
        domain_table.add_column("Domain", style="cyan")
        domain_table.add_column("Count", justify="right")

        for dom, count in sorted(discovery.domain_counts.items(), key=lambda x: -x[1]):
            domain_table.add_row(dom, str(count))

        console.print(domain_table)

    console.print(f"\n[green]✅ Discovery session: {discovery.id}[/green]")


@app.command()
def entities(
    domain: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--domain", "-d", help="Filter by domain"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum entities to show"),
    ] = 50,
) -> None:
    """List entities from the database.

    Shows discovered entities with their current state.
    """
    asyncio.run(_list_entities(domain, limit))


async def _list_entities(domain: str | None, limit: int) -> None:
    """List entities from database."""
    from rich.table import Table

    from src.dal.entities import EntityRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = EntityRepository(session)
        entities = await repo.list_all(domain=domain, limit=limit)
        total = await repo.count(domain=domain)

    if not entities:
        console.print("[yellow]No entities found. Run 'aether discover' first.[/yellow]")
        return

    table = Table(
        title=f"Entities ({len(entities)}/{total})",
        show_header=True,
    )
    table.add_column("Entity ID", style="cyan")
    table.add_column("Name")
    table.add_column("State", justify="center")
    table.add_column("Area")

    for entity in entities:
        state_color = "green" if entity.state == "on" else "dim"
        table.add_row(
            entity.entity_id,
            entity.name,
            f"[{state_color}]{entity.state or 'unknown'}[/{state_color}]",
            entity.area.name if entity.area else "-",
        )

    console.print(table)


@app.command()
def areas() -> None:
    """List discovered areas."""
    asyncio.run(_list_areas())


async def _list_areas() -> None:
    """List areas from database."""
    from rich.table import Table

    from src.dal.areas import AreaRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = AreaRepository(session)
        area_list = await repo.list_all()

    if not area_list:
        console.print("[yellow]No areas found. Run 'aether discover' first.[/yellow]")
        return

    table = Table(title="Areas", show_header=True)
    table.add_column("Area ID", style="cyan")
    table.add_column("Name")
    table.add_column("Entities", justify="right")

    for area in area_list:
        entity_count = len(area.entities) if area.entities else 0
        table.add_row(area.ha_area_id, area.name, str(entity_count))

    console.print(table)


@app.command()
def chat(
    message: Annotated[
        Optional[str],  # noqa: UP007
        typer.Argument(help="Initial message to send (or enter interactive mode)"),
    ] = None,
) -> None:
    """Chat with the Architect agent.

    Start an interactive conversation to design automations,
    ask questions about your home, or request insights.
    """
    if message:
        # Single message mode
        console.print(f"[bold]You:[/bold] {message}")
        asyncio.run(_send_message(message))
    else:
        # Interactive mode
        asyncio.run(_interactive_chat())


async def _send_message(message: str) -> None:
    """Send a single message and print the response."""
    # TODO: Implement actual chat with Architect agent
    console.print(
        "[yellow]⚠️ Chat not yet implemented. "
        "Will be available after Architect agent is complete.[/yellow]"
    )


async def _interactive_chat() -> None:
    """Run interactive chat session."""
    console.print(
        Panel(
            "[bold green]Aether Interactive Chat[/bold green]\n"
            "Chat with the Architect agent to design automations.\n"
            "Type 'exit' or 'quit' to end the session.\n"
            "Type 'help' for available commands.",
            title="💬 Chat",
            border_style="green",
        )
    )

    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.lower() == "help":
            _show_chat_help()
            continue

        if not user_input.strip():
            continue

        # TODO: Send to Architect agent
        console.print(
            "[yellow]⚠️ Chat not yet implemented. "
            "Will be available after Architect agent is complete.[/yellow]"
        )


def _show_chat_help() -> None:
    """Show help for chat commands."""
    table = Table(title="Chat Commands", show_header=True)
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    table.add_row("exit, quit, q", "Exit the chat session")
    table.add_row("help", "Show this help message")
    table.add_row("status", "Show system status")
    table.add_row("discover", "Trigger entity discovery")

    console.print(table)


@app.command()
def status() -> None:
    """Show system status.

    Displays the current status of all system components
    including database, MLflow, and Home Assistant connectivity.
    """
    asyncio.run(_show_status())


async def _show_status() -> None:
    """Fetch and display system status."""
    import httpx

    from src.settings import get_settings

    settings = get_settings()

    console.print(
        Panel(
            "[bold]Checking System Status...[/bold]",
            title="📊 Status",
            border_style="blue",
        )
    )

    # Try to fetch from running API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://{settings.api_host}:{settings.api_port}/api/v1/status"
            )

            if response.status_code == 200:
                data = response.json()
                _display_status(data)
                return
    except httpx.ConnectError:
        console.print("[yellow]API server not running. Checking components directly...[/yellow]\n")
    except Exception as e:
        console.print(f"[red]Error fetching status: {e}[/red]\n")

    # Fallback: check components directly
    await _check_components_directly()


def _display_status(data: dict) -> None:  # type: ignore[type-arg]
    """Display status from API response."""
    status_colors = {
        "healthy": "green",
        "degraded": "yellow",
        "unhealthy": "red",
    }

    overall = data.get("status", "unknown")
    color = status_colors.get(overall, "white")

    console.print(f"[bold]Overall Status:[/bold] [{color}]{overall.upper()}[/{color}]")
    console.print(f"[bold]Environment:[/bold] {data.get('environment', 'unknown')}")
    console.print(f"[bold]Version:[/bold] {data.get('version', 'unknown')}")

    if data.get("uptime_seconds"):
        uptime = data["uptime_seconds"]
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        console.print(f"[bold]Uptime:[/bold] {hours}h {minutes}m {seconds}s")

    console.print()

    # Component table
    table = Table(title="Components", show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Message")
    table.add_column("Latency")

    for component in data.get("components", []):
        status = component.get("status", "unknown")
        color = status_colors.get(status, "white")
        latency = component.get("latency_ms")
        latency_str = f"{latency:.1f}ms" if latency else "-"

        table.add_row(
            component.get("name", "unknown"),
            f"[{color}]{status}[/{color}]",
            component.get("message", "-"),
            latency_str,
        )

    console.print(table)


async def _check_components_directly() -> None:
    """Check components without the API server."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    table = Table(title="Components", show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Message")

    status_colors = {
        "healthy": "green",
        "degraded": "yellow",
        "unhealthy": "red",
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        # Check database
        progress.add_task("Checking database...", total=None)
        try:
            from src.storage import get_session

            async with get_session() as session:
                await session.execute("SELECT 1")  # type: ignore[arg-type]
            table.add_row("database", "[green]healthy[/green]", "PostgreSQL connected")
        except Exception as e:
            table.add_row("database", "[red]unhealthy[/red]", str(e)[:50])

        # Check settings
        progress.update(progress.task_ids[0], description="Checking configuration...")
        try:
            from src.settings import get_settings

            settings = get_settings()
            if settings.ha_url and settings.ha_token.get_secret_value():
                table.add_row("config", "[green]healthy[/green]", "Settings loaded")
            else:
                table.add_row("config", "[yellow]degraded[/yellow]", "HA credentials missing")
        except Exception as e:
            table.add_row("config", "[red]unhealthy[/red]", str(e)[:50])

    console.print(table)


@app.command()
def version() -> None:
    """Show Aether version information."""
    console.print(
        Panel(
            "[bold]Aether[/bold] v0.1.0\n"
            "Agentic Home Automation System\n\n"
            "[dim]https://github.com/dsaridak/home_agent[/dim]",
            title="🏠 Version",
            border_style="blue",
        )
    )


# Entry point for: python -m src.cli.main
if __name__ == "__main__":
    app()
