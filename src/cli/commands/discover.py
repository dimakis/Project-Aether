"""Discovery commands."""

import asyncio
from typing import Annotated, Optional

import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.cli.utils import console


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
    from src.dal.sync import run_discovery
    from src.ha import get_ha_client
    from src.storage import get_session
    from src.tracing import init_mlflow, start_experiment_run, log_param, log_metric
    from src.tracing.context import session_context

    # Initialize MLflow tracing
    init_mlflow()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Connecting to Home Assistant...", total=None)

        try:
            # Get HA client and verify connection
            ha = get_ha_client()
            progress.update(task, description="Fetching entities from Home Assistant...")

            # Run discovery with session context and MLflow tracking
            with session_context() as session_id:
                with start_experiment_run(run_name="librarian_discovery") as run:
                    log_param("triggered_by", "cli")
                    log_param("domain_filter", domain or "all")
                    log_param("session.id", session_id)

                    async with get_session() as session:
                        discovery = await run_discovery(
                            session=session,
                            ha_client=ha,
                            triggered_by="cli",
                        )

                    # Log discovery metrics
                    log_metric("entities_found", float(discovery.entities_found))
                    log_metric("entities_added", float(discovery.entities_added))
                    log_metric("entities_updated", float(discovery.entities_updated))
                    log_metric("entities_removed", float(discovery.entities_removed))
                    log_metric("duration_seconds", discovery.duration_seconds or 0.0)

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
