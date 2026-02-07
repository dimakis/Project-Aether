"""Status and info commands."""

import asyncio

import typer
import httpx
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.cli.utils import console


def status() -> None:
    """Show system status.

    Displays the current status of all system components
    including database, MLflow, and Home Assistant connectivity.
    """
    asyncio.run(_show_status())


async def _show_status() -> None:
    """Fetch and display system status."""
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
            from sqlalchemy import text

            from src.storage import get_session

            async with get_session() as session:
                await session.execute(text("SELECT 1"))
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
