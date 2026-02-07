"""CLI entry point and base commands.

Provides the main CLI application with commands for:
- serve: Run the API server
- discover: Trigger entity discovery
- chat: Interactive chat with the Architect agent
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
            # Get MCP client and verify connection
            mcp = get_mcp_client()
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
                            mcp_client=mcp,
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
        table.add_column("Domain")
        table.add_column("State", justify="center")

        # Extract data while session is active
        rows = []
        for entity in entities:
            state_color = "green" if entity.state == "on" else "dim"
            rows.append((
                entity.entity_id,
                entity.name or entity.entity_id,
                entity.domain,
                f"[{state_color}]{entity.state or 'unknown'}[/{state_color}]",
            ))

    # Build table outside session (data already extracted)
    for row in rows:
        table.add_row(*row)

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
def devices(
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum devices to show"),
    ] = 50,
) -> None:
    """List discovered devices."""
    asyncio.run(_list_devices(limit))


async def _list_devices(limit: int) -> None:
    """List devices from database."""
    from rich.table import Table

    from src.dal.devices import DeviceRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = DeviceRepository(session)
        device_list = await repo.list_all(limit=limit)
        total = await repo.count()

    if not device_list:
        console.print("[yellow]No devices found. Run 'aether discover' first.[/yellow]")
        return

    table = Table(title=f"Devices ({len(device_list)}/{total})", show_header=True)
    table.add_column("Device ID", style="cyan")
    table.add_column("Name")
    table.add_column("Manufacturer", style="dim")
    table.add_column("Model", style="dim")
    table.add_column("Area")
    table.add_column("Entities", justify="right")

    for device in device_list:
        entity_count = len(device.entities) if device.entities else 0
        table.add_row(
            device.ha_device_id[:20] + "..." if len(device.ha_device_id) > 20 else device.ha_device_id,
            device.name,
            device.manufacturer or "-",
            device.model or "-",
            device.area.name if device.area else "-",
            str(entity_count),
        )

    console.print(table)


@app.command()
def automations(
    state: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--state", "-s", help="Filter by state (on/off)"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum automations to show"),
    ] = 50,
) -> None:
    """List HA automations."""
    asyncio.run(_list_automations(state, limit))


async def _list_automations(state: str | None, limit: int) -> None:
    """List automations from database."""
    from rich.table import Table

    from src.dal.entities import EntityRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = EntityRepository(session)
        # Query entities with domain='automation'
        automation_list = await repo.list_all(domain="automation", limit=limit)
        total = await repo.count(domain="automation")
        
        # Filter by state if specified
        if state:
            automation_list = [a for a in automation_list if a.state == state]

        if not automation_list:
            console.print("[yellow]No automations found. Run 'aether discover' first.[/yellow]")
            return

        # Extract data while session is active
        rows = []
        for auto in automation_list:
            state_color = "green" if auto.state == "on" else "dim"
            # Get mode from attributes if available
            mode = auto.attributes.get("mode", "single") if auto.attributes else "single"
            rows.append((
                auto.entity_id,
                auto.name or auto.entity_id,
                f"[{state_color}]{auto.state}[/{state_color}]",
                mode,
            ))

    table = Table(title=f"Automations ({len(rows)}/{total})", show_header=True)
    table.add_column("Entity ID", style="cyan")
    table.add_column("Name")
    table.add_column("State", justify="center")
    table.add_column("Mode")

    for row in rows:
        table.add_row(*row)

    console.print(table)


@app.command()
def scripts(
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum scripts to show"),
    ] = 50,
) -> None:
    """List HA scripts."""
    asyncio.run(_list_scripts(limit))


async def _list_scripts(limit: int) -> None:
    """List scripts from database."""
    from rich.table import Table

    from src.dal.entities import EntityRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = EntityRepository(session)
        script_list = await repo.list_all(domain="script", limit=limit)
        total = await repo.count(domain="script")

        if not script_list:
            console.print("[yellow]No scripts found. Run 'aether discover' first.[/yellow]")
            return

        rows = []
        for script in script_list:
            state_color = "green" if script.state == "on" else "dim"
            mode = script.attributes.get("mode", "single") if script.attributes else "single"
            icon = script.icon or (script.attributes.get("icon") if script.attributes else None) or "-"
            rows.append((
                script.entity_id,
                script.name or script.entity_id,
                f"[{state_color}]{script.state}[/{state_color}]",
                mode,
                icon,
            ))

    table = Table(title=f"Scripts ({len(rows)}/{total})", show_header=True)
    table.add_column("Entity ID", style="cyan")
    table.add_column("Name")
    table.add_column("State", justify="center")
    table.add_column("Mode")
    table.add_column("Icon")

    for row in rows:
        table.add_row(*row)

    console.print(table)


@app.command()
def scenes(
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum scenes to show"),
    ] = 50,
) -> None:
    """List HA scenes."""
    asyncio.run(_list_scenes(limit))


async def _list_scenes(limit: int) -> None:
    """List scenes from database."""
    from rich.table import Table

    from src.dal.entities import EntityRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = EntityRepository(session)
        scene_list = await repo.list_all(domain="scene", limit=limit)
        total = await repo.count(domain="scene")

        if not scene_list:
            console.print("[yellow]No scenes found. Run 'aether discover' first.[/yellow]")
            return

        rows = []
        for scene in scene_list:
            icon = scene.icon or (scene.attributes.get("icon") if scene.attributes else None) or "-"
            rows.append((
                scene.entity_id,
                scene.name or scene.entity_id,
                icon,
            ))

    table = Table(title=f"Scenes ({len(rows)}/{total})", show_header=True)
    table.add_column("Entity ID", style="cyan")
    table.add_column("Name")
    table.add_column("Icon")

    for row in rows:
        table.add_row(*row)

    console.print(table)


@app.command()
def services(
    domain: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--domain", "-d", help="Filter by domain"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum services to show"),
    ] = 100,
) -> None:
    """List known services."""
    asyncio.run(_list_services(domain, limit))


async def _list_services(domain: str | None, limit: int) -> None:
    """List services from database."""
    from rich.table import Table

    from src.dal.services import ServiceRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = ServiceRepository(session)
        service_list = await repo.list_all(domain=domain, limit=limit)
        total = await repo.count(domain=domain)

    if not service_list:
        console.print("[yellow]No services found. Run 'aether seed-services' first.[/yellow]")
        return

    table = Table(title=f"Services ({len(service_list)}/{total})", show_header=True)
    table.add_column("Service", style="cyan")
    table.add_column("Name")
    table.add_column("Source", justify="center")

    for svc in service_list:
        source = "[dim]seeded[/dim]" if svc.is_seeded else "[green]discovered[/green]"
        table.add_row(
            f"{svc.domain}.{svc.service}",
            svc.name or "-",
            source,
        )

    console.print(table)


@app.command(name="seed-services")
def seed_services_cmd() -> None:
    """Seed common services into the database."""
    asyncio.run(_seed_services())


async def _seed_services() -> None:
    """Seed common services."""
    from src.dal.services import seed_services
    from src.storage import get_session

    async with get_session() as session:
        stats = await seed_services(session)
        await session.commit()

    console.print(
        Panel(
            f"[green]Services seeded successfully![/green]\n\n"
            f"Added: {stats['added']}\n"
            f"Skipped (already exist): {stats['skipped']}",
            title="✅ Service Seeding",
            border_style="green",
        )
    )


@app.command(name="mcp-gaps")
def mcp_gaps() -> None:
    """Show MCP capability gaps and their impact."""
    asyncio.run(_show_mcp_gaps())


async def _show_mcp_gaps() -> None:
    """Display MCP gaps report."""
    from src.mcp.gaps import get_all_gaps, get_gaps_report

    gaps = get_all_gaps()
    report = get_gaps_report()

    console.print(
        Panel(
            f"[bold]MCP Capability Gap Report[/bold]\n\n"
            f"Total gaps identified: {len(gaps)}\n"
            f"High priority: {report['priority_counts'].get('P1', 0)}\n"
            f"Medium priority: {report['priority_counts'].get('P2', 0)}\n"
            f"Low priority: {report['priority_counts'].get('P3', 0)}",
            title="📊 MCP Gaps",
            border_style="yellow",
        )
    )

    table = Table(title="Known MCP Capability Gaps", show_header=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Priority")
    table.add_column("Impact")
    table.add_column("Workaround")

    priority_colors = {"P1": "red", "P2": "yellow", "P3": "dim"}

    for gap in gaps:
        color = priority_colors.get(gap["priority"], "white")
        table.add_row(
            gap["tool"],
            f"[{color}]{gap['priority']}[/{color}]",
            gap["impact"][:50] + "..." if len(gap["impact"]) > 50 else gap["impact"],
            gap["workaround"][:30] + "..." if len(gap["workaround"]) > 30 else gap["workaround"],
        )

    console.print(table)

    console.print("\n[dim]Run 'aether mcp-gaps --verbose' for full details[/dim]")


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


# =============================================================================
# USER STORY 2: CHAT AND PROPOSALS COMMANDS
# =============================================================================


@app.command()
def chat(
    message: Annotated[
        Optional[str],
        typer.Argument(help="Initial message (or leave empty for interactive mode)"),
    ] = None,
    conversation_id: Annotated[
        Optional[str],
        typer.Option("--continue", "-c", help="Continue an existing conversation"),
    ] = None,
) -> None:
    """Interactive chat with the Architect agent.

    Start a conversation to design automations. The Architect will help
    translate your requirements into Home Assistant automations.

    Examples:
        aether chat "Turn on lights when I get home"
        aether chat --continue <conversation-id>
        aether chat  # Interactive mode
    """
    asyncio.run(_chat_interactive(message, conversation_id))


async def _chat_interactive(
    initial_message: Optional[str],
    conversation_id: Optional[str],
) -> None:
    """Run interactive chat session."""
    from rich.markdown import Markdown
    from rich.prompt import Prompt

    from src.agents import ArchitectWorkflow
    from src.dal import ConversationRepository, MessageRepository
    from src.graph.state import ConversationState
    from src.storage import get_session
    from src.tracing import get_tracing_status, init_mlflow
    from src.tracing.context import session_context
    from langchain_core.messages import HumanMessage, AIMessage

    # Initialize MLflow tracing (enables autolog for OpenAI)
    init_mlflow()
    trace_status = get_tracing_status()
    console.print(
        "[dim]MLflow tracking: {uri} | experiment: {exp} | traces: {traces}[/dim]\n".format(
            uri=trace_status["tracking_uri"],
            exp=trace_status["experiment_name"],
            traces="on" if trace_status["traces_enabled"] else "off",
        )
    )

    # Use conversation_id as session ID if continuing, otherwise create new
    # This ensures all traces for a conversation are grouped together
    with session_context(session_id=conversation_id):
        console.print(
            Panel(
                "[bold blue]Architect Chat[/bold blue]\n\n"
                "Chat with the Architect to design automations.\n"
                "Type [cyan]'exit'[/cyan] or [cyan]'quit'[/cyan] to end.\n"
                "Type [cyan]'approve'[/cyan] to approve pending proposals.\n"
                "Type [cyan]'reject'[/cyan] to reject pending proposals.",
                title="🏗️ Architect Agent",
                border_style="blue",
            )
        )

        workflow = ArchitectWorkflow()
        state: ConversationState | None = None
        pending_proposal_id: str | None = None

        async with get_session() as session:
            conv_repo = ConversationRepository(session)
            msg_repo = MessageRepository(session)

            # Load existing conversation if specified
            if conversation_id:
                conv = await conv_repo.get_by_id(conversation_id, include_messages=True)
                if conv:
                    console.print(
                        f"[dim]Continuing conversation: {conversation_id}[/dim]\n"
                    )
                    # Show previous messages
                    for msg in conv.messages:
                        if msg.role == "user":
                            console.print(f"[bold cyan]You:[/bold cyan] {msg.content}")
                        else:
                            console.print(f"[bold green]Architect:[/bold green]")
                            console.print(Markdown(msg.content))
                    console.print()

                    # Build state from history
                    state = ConversationState(
                        conversation_id=conversation_id,
                        messages=[
                            HumanMessage(content=m.content) if m.role == "user"
                            else AIMessage(content=m.content)
                            for m in conv.messages
                        ],
                    )
                else:
                    console.print(f"[red]Conversation {conversation_id} not found.[/red]")
                    return

            # Process initial message if provided
            if initial_message:
                console.print(f"[bold cyan]You:[/bold cyan] {initial_message}\n")

                if state:
                    state = await workflow.continue_conversation(
                        state=state,
                        user_message=initial_message,
                        session=session,
                    )
                else:
                    state = await workflow.start_conversation(
                        user_message=initial_message,
                        session=session,
                    )
                    # Update session context to use conversation_id for trace correlation
                    from src.tracing.context import set_session_id
                    set_session_id(state.conversation_id)

                # Show response
                if state.messages:
                    for msg in state.messages:
                        if hasattr(msg, "type") and msg.type == "ai":
                            console.print("[bold green]Architect:[/bold green]")
                            console.print(Markdown(msg.content))
                            break

                # Check for proposals
                if state.pending_approvals:
                    pending_proposal_id = state.pending_approvals[0].id
                    console.print(
                        f"\n[yellow]📋 Proposal pending approval: {pending_proposal_id}[/yellow]"
                    )
                    console.print(
                        "[dim]Type 'approve' or 'reject <reason>' to respond.[/dim]\n"
                    )

                await session.commit()

            # Interactive loop
            while True:
                try:
                    user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                except (KeyboardInterrupt, EOFError):
                    break

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ("exit", "quit", "q"):
                    console.print("[dim]Ending conversation.[/dim]")
                    break

                if user_input.lower() == "approve" and pending_proposal_id:
                    from src.dal import ProposalRepository

                    proposal_repo = ProposalRepository(session)
                    await proposal_repo.approve(pending_proposal_id, "cli_user")
                    await session.commit()
                    console.print(f"[green]✅ Proposal {pending_proposal_id} approved![/green]")
                    console.print("[dim]Use 'aether proposals deploy <id>' to deploy.[/dim]")
                    pending_proposal_id = None
                    continue

                if user_input.lower().startswith("reject") and pending_proposal_id:
                    reason = user_input[6:].strip() or "Rejected by user"
                    from src.dal import ProposalRepository

                    proposal_repo = ProposalRepository(session)
                    await proposal_repo.reject(pending_proposal_id, reason)
                    await session.commit()
                    console.print(f"[red]❌ Proposal rejected: {reason}[/red]")
                    pending_proposal_id = None
                    continue

                # Process message
                console.print()

                if state:
                    state = await workflow.continue_conversation(
                        state=state,
                        user_message=user_input,
                        session=session,
                    )
                else:
                    state = await workflow.start_conversation(
                        user_message=user_input,
                        session=session,
                    )
                    # Update session context to use conversation_id for trace correlation
                    from src.tracing.context import set_session_id
                    set_session_id(state.conversation_id)

                # Show response
                if state.messages:
                    for msg in reversed(state.messages):
                        if hasattr(msg, "type") and msg.type == "ai":
                            console.print("[bold green]Architect:[/bold green]")
                            console.print(Markdown(msg.content))
                            break

                # Check for new proposals
                if state.pending_approvals:
                    pending_proposal_id = state.pending_approvals[0].id
                    console.print(
                        f"\n[yellow]📋 Proposal pending approval: {pending_proposal_id}[/yellow]"
                    )
                    console.print(
                        "[dim]Type 'approve' or 'reject <reason>' to respond.[/dim]"
                    )

                await session.commit()

        console.print("\n[dim]Chat session ended.[/dim]")


# Proposals sub-command group
proposals_app = typer.Typer(
    name="proposals",
    help="Manage automation proposals",
    no_args_is_help=True,
)
app.add_typer(proposals_app, name="proposals")


@proposals_app.command("list")
def proposals_list(
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s", help="Filter by status (proposed, approved, deployed, etc.)"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number to show"),
    ] = 20,
) -> None:
    """List automation proposals."""
    asyncio.run(_list_proposals(status, limit))


async def _list_proposals(status: Optional[str], limit: int) -> None:
    """List proposals."""
    from src.dal import ProposalRepository
    from src.storage import get_session
    from src.storage.entities import ProposalStatus

    async with get_session() as session:
        repo = ProposalRepository(session)

        # Get proposals
        proposals = []
        if status:
            try:
                status_filter = ProposalStatus(status.upper())
                proposals = await repo.list_by_status(status_filter, limit=limit)
            except ValueError:
                console.print(f"[red]Invalid status: {status}[/red]")
                return
        else:
            for s in ProposalStatus:
                proposals.extend(await repo.list_by_status(s, limit=limit))
            proposals = sorted(proposals, key=lambda p: p.created_at, reverse=True)[:limit]

        if not proposals:
            console.print("[dim]No proposals found.[/dim]")
            return

        table = Table(title=f"Proposals ({len(proposals)})", show_header=True)
        table.add_column("ID", style="cyan", max_width=12)
        table.add_column("Name", max_width=30)
        table.add_column("Status")
        table.add_column("Created")

        status_colors = {
            "draft": "dim",
            "proposed": "yellow",
            "approved": "green",
            "rejected": "red",
            "deployed": "blue",
            "rolled_back": "magenta",
            "archived": "dim",
        }

        for p in proposals:
            color = status_colors.get(p.status.value, "white")
            table.add_row(
                p.id[:12] + "...",
                p.name[:30],
                f"[{color}]{p.status.value}[/{color}]",
                p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "-",
            )

        console.print(table)


@proposals_app.command("show")
def proposals_show(
    proposal_id: Annotated[str, typer.Argument(help="Proposal ID")],
) -> None:
    """Show details of a proposal."""
    asyncio.run(_show_proposal(proposal_id))


async def _show_proposal(proposal_id: str) -> None:
    """Show proposal details."""
    from src.dal import ProposalRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            console.print(f"[red]Proposal {proposal_id} not found.[/red]")
            return

        # Generate YAML
        import yaml

        yaml_content = yaml.dump(proposal.to_ha_yaml_dict(), default_flow_style=False)

        console.print(
            Panel(
                f"[bold]Name:[/bold] {proposal.name}\n"
                f"[bold]Status:[/bold] {proposal.status.value}\n"
                f"[bold]Mode:[/bold] {proposal.mode}\n"
                f"[bold]Description:[/bold] {proposal.description or 'N/A'}\n\n"
                f"[bold]Approved by:[/bold] {proposal.approved_by or 'N/A'}\n"
                f"[bold]HA Automation ID:[/bold] {proposal.ha_automation_id or 'N/A'}\n\n"
                f"[bold]YAML:[/bold]\n```yaml\n{yaml_content}```",
                title=f"📋 Proposal {proposal_id[:12]}...",
                border_style="blue",
            )
        )


@proposals_app.command("approve")
def proposals_approve(
    proposal_id: Annotated[str, typer.Argument(help="Proposal ID to approve")],
    user: Annotated[
        str,
        typer.Option("--user", "-u", help="Approver name"),
    ] = "cli_user",
) -> None:
    """Approve a pending proposal."""
    asyncio.run(_approve_proposal(proposal_id, user))


async def _approve_proposal(proposal_id: str, user: str) -> None:
    """Approve a proposal."""
    from src.dal import ProposalRepository
    from src.storage import get_session
    from src.storage.entities import ProposalStatus

    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            console.print(f"[red]Proposal {proposal_id} not found.[/red]")
            return

        if proposal.status != ProposalStatus.PROPOSED:
            console.print(
                f"[red]Cannot approve proposal in status {proposal.status.value}.[/red]"
            )
            return

        await repo.approve(proposal_id, user)
        await session.commit()

        console.print(f"[green]✅ Proposal {proposal_id[:12]}... approved![/green]")
        console.print("[dim]Use 'aether proposals deploy <id>' to deploy.[/dim]")


@proposals_app.command("reject")
def proposals_reject(
    proposal_id: Annotated[str, typer.Argument(help="Proposal ID to reject")],
    reason: Annotated[str, typer.Argument(help="Rejection reason")],
) -> None:
    """Reject a pending proposal."""
    asyncio.run(_reject_proposal(proposal_id, reason))


async def _reject_proposal(proposal_id: str, reason: str) -> None:
    """Reject a proposal."""
    from src.dal import ProposalRepository
    from src.storage import get_session
    from src.storage.entities import ProposalStatus

    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            console.print(f"[red]Proposal {proposal_id} not found.[/red]")
            return

        if proposal.status not in (ProposalStatus.PROPOSED, ProposalStatus.APPROVED):
            console.print(
                f"[red]Cannot reject proposal in status {proposal.status.value}.[/red]"
            )
            return

        await repo.reject(proposal_id, reason)
        await session.commit()

        console.print(f"[red]❌ Proposal {proposal_id[:12]}... rejected.[/red]")


@proposals_app.command("deploy")
def proposals_deploy(
    proposal_id: Annotated[str, typer.Argument(help="Proposal ID to deploy")],
) -> None:
    """Deploy an approved proposal to Home Assistant."""
    asyncio.run(_deploy_proposal(proposal_id))


async def _deploy_proposal(proposal_id: str) -> None:
    """Deploy a proposal."""
    from src.agents import DeveloperWorkflow
    from src.dal import ProposalRepository
    from src.storage import get_session
    from src.storage.entities import ProposalStatus

    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            console.print(f"[red]Proposal {proposal_id} not found.[/red]")
            return

        if proposal.status != ProposalStatus.APPROVED:
            console.print(
                f"[red]Cannot deploy proposal in status {proposal.status.value}. "
                f"Must be approved first.[/red]"
            )
            return

        console.print(f"[yellow]Deploying proposal {proposal_id[:12]}...[/yellow]")

        workflow = DeveloperWorkflow()

        try:
            result = await workflow.deploy(proposal_id, session)
            await session.commit()

            console.print(f"[green]✅ Deployment successful![/green]")
            console.print(f"[dim]Method: {result.get('deployment_method', 'manual')}[/dim]")
            console.print(f"[dim]HA Automation ID: {result.get('ha_automation_id', 'N/A')}[/dim]")

            if result.get("instructions"):
                console.print("\n[yellow]Manual steps required:[/yellow]")
                console.print(result["instructions"])

        except Exception as e:
            console.print(f"[red]Deployment failed: {e}[/red]")


@proposals_app.command("rollback")
def proposals_rollback(
    proposal_id: Annotated[str, typer.Argument(help="Proposal ID to rollback")],
) -> None:
    """Rollback a deployed proposal."""
    asyncio.run(_rollback_proposal(proposal_id))


async def _rollback_proposal(proposal_id: str) -> None:
    """Rollback a proposal."""
    from src.agents import DeveloperWorkflow
    from src.dal import ProposalRepository
    from src.storage import get_session
    from src.storage.entities import ProposalStatus

    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            console.print(f"[red]Proposal {proposal_id} not found.[/red]")
            return

        if proposal.status != ProposalStatus.DEPLOYED:
            console.print(
                f"[red]Cannot rollback proposal in status {proposal.status.value}. "
                f"Must be deployed.[/red]"
            )
            return

        console.print(f"[yellow]Rolling back proposal {proposal_id[:12]}...[/yellow]")

        workflow = DeveloperWorkflow()

        try:
            result = await workflow.rollback(proposal_id, session)
            await session.commit()

            if result.get("rolled_back"):
                console.print(f"[green]✅ Rollback successful![/green]")
                if result.get("note"):
                    console.print(f"[dim]{result['note']}[/dim]")
            else:
                console.print(f"[red]Rollback failed: {result.get('error', 'Unknown')}[/red]")

        except Exception as e:
            console.print(f"[red]Rollback failed: {e}[/red]")


@app.command()
def analyze(
    analysis_type: Annotated[
        str,
        typer.Argument(help="Analysis type: energy, anomaly, pattern, custom"),
    ] = "energy",
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Days of history to analyze"),
    ] = 1,
    entity: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--entity", "-e", help="Specific entity to analyze"),
    ] = None,
    query: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--query", "-q", help="Custom analysis query"),
    ] = None,
) -> None:
    """Run energy analysis with the Data Scientist agent.

    Analyzes energy sensor data and generates insights.

    Examples:
        aether analyze energy --days 7
        aether analyze anomaly --entity sensor.grid_power
        aether analyze custom --query "Find peak usage times"
    """
    asyncio.run(_run_analysis(analysis_type, days, entity, query))


async def _run_analysis(
    analysis_type: str,
    days: int,
    entity: str | None,
    query: str | None,
) -> None:
    """Run energy analysis."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from src.agents import DataScientistWorkflow
    from src.graph.state import AnalysisType
    from src.storage import get_session
    from src.tracing import init_mlflow
    from src.tracing.context import session_context

    # Initialize MLflow
    init_mlflow()

    # Map analysis type
    type_map = {
        "energy": AnalysisType.ENERGY_OPTIMIZATION,
        "anomaly": AnalysisType.ANOMALY_DETECTION,
        "pattern": AnalysisType.USAGE_PATTERNS,
        "custom": AnalysisType.CUSTOM,
    }
    analysis_enum = type_map.get(analysis_type.lower(), AnalysisType.ENERGY_OPTIMIZATION)

    # Build entity list
    entity_ids = [entity] if entity else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running analysis...", total=None)

        try:
            workflow = DataScientistWorkflow()

            with session_context():
                async with get_session() as session:
                    progress.update(task, description="[cyan]Collecting energy data...")

                    state = await workflow.run_analysis(
                        analysis_type=analysis_enum,
                        entity_ids=entity_ids,
                        hours=days * 24,
                        custom_query=query,
                        session=session,
                    )
                    await session.commit()

                    progress.update(task, description="[green]Analysis complete!")

        except Exception as e:
            console.print(f"[red]Analysis failed: {e}[/red]")
            return

    # Display results
    console.print()
    console.print(
        Panel(
            f"[bold]Analysis: {analysis_type.title()}[/bold]\n"
            f"Period: {days} day(s)\n"
            f"Insights found: {len(state.insights)}",
            title="📊 Analysis Results",
            border_style="green",
        )
    )

    # Display insights
    if state.insights:
        for i, insight in enumerate(state.insights, 1):
            impact_color = {
                "critical": "red",
                "high": "yellow",
                "medium": "cyan",
                "low": "dim",
            }.get(insight.get("impact", "medium"), "white")

            confidence = insight.get("confidence", 0) * 100

            console.print()
            console.print(
                Panel(
                    f"[bold]{insight.get('title', 'Untitled')}[/bold]\n\n"
                    f"{insight.get('description', 'No description')}\n\n"
                    f"[dim]Confidence: {confidence:.0f}% | "
                    f"Impact: [{impact_color}]{insight.get('impact', 'unknown')}[/{impact_color}][/dim]",
                    title=f"💡 Insight {i}",
                    border_style=impact_color,
                )
            )

    # Display recommendations
    if state.recommendations:
        console.print()
        console.print("[bold]📋 Recommendations:[/bold]")
        for rec in state.recommendations:
            console.print(f"  • {rec}")
    else:
        console.print("\n[dim]No specific recommendations generated.[/dim]")


@app.command()
def insights(
    status: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--status", "-s", help="Filter by status: pending, reviewed, actioned, dismissed"),
    ] = None,
    type: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--type", "-t", help="Filter by type: energy_optimization, anomaly_detection, etc."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number of insights to show"),
    ] = 20,
) -> None:
    """List stored insights from previous analyses.

    Examples:
        aether insights
        aether insights --status pending
        aether insights --type energy_optimization --limit 10
    """
    asyncio.run(_list_insights(status, type, limit))


async def _list_insights(
    status: str | None,
    insight_type: str | None,
    limit: int,
) -> None:
    """List insights from database."""
    from src.dal import InsightRepository
    from src.storage import get_session
    from src.storage.entities.insight import InsightStatus, InsightType

    async with get_session() as session:
        repo = InsightRepository(session)

        # Parse filters
        status_filter = None
        type_filter = None

        if status:
            try:
                status_filter = InsightStatus(status.lower())
            except ValueError:
                console.print(f"[yellow]Unknown status: {status}[/yellow]")

        if insight_type:
            try:
                type_filter = InsightType(insight_type.lower())
            except ValueError:
                console.print(f"[yellow]Unknown type: {insight_type}[/yellow]")

        # Fetch insights
        if type_filter:
            insights = await repo.list_by_type(type_filter, status=status_filter, limit=limit)
        elif status_filter:
            insights = await repo.list_by_status(status_filter, limit=limit)
        else:
            insights = await repo.list_all(limit=limit)

        total = await repo.count(type=type_filter, status=status_filter)

    if not insights:
        console.print("[dim]No insights found.[/dim]")
        return

    # Build table
    table = Table(title=f"Insights ({len(insights)} of {total})")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Type", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Impact", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Created", style="dim")

    for insight in insights:
        impact_color = {
            "critical": "red",
            "high": "yellow",
            "medium": "cyan",
            "low": "dim",
        }.get(insight.impact, "white")

        status_color = {
            "pending": "yellow",
            "reviewed": "cyan",
            "actioned": "green",
            "dismissed": "dim",
        }.get(insight.status.value, "white")

        table.add_row(
            insight.id[:12] + "...",
            insight.type.value.replace("_", " ").title(),
            insight.title[:40] + ("..." if len(insight.title) > 40 else ""),
            f"[{impact_color}]{insight.impact}[/{impact_color}]",
            f"[{status_color}]{insight.status.value}[/{status_color}]",
            insight.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@app.command(name="insight")
def show_insight(
    insight_id: Annotated[
        str,
        typer.Argument(help="Insight ID to show"),
    ],
) -> None:
    """Show details of a specific insight.

    Example:
        aether insight abc123
    """
    asyncio.run(_show_insight(insight_id))


async def _show_insight(insight_id: str) -> None:
    """Show insight details."""
    from src.dal import InsightRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = InsightRepository(session)

        # Try to find insight by ID or prefix
        insight = await repo.get_by_id(insight_id)

        if not insight:
            # Try prefix match
            all_insights = await repo.list_all(limit=100)
            matches = [i for i in all_insights if i.id.startswith(insight_id)]
            if len(matches) == 1:
                insight = matches[0]
            elif len(matches) > 1:
                console.print(f"[yellow]Multiple insights match '{insight_id}':[/yellow]")
                for m in matches[:5]:
                    console.print(f"  • {m.id[:12]}... - {m.title}")
                return

        if not insight:
            console.print(f"[red]Insight not found: {insight_id}[/red]")
            return

    # Display insight
    impact_color = {
        "critical": "red",
        "high": "yellow",
        "medium": "cyan",
        "low": "dim",
    }.get(insight.impact, "white")

    console.print(
        Panel(
            f"[bold]{insight.title}[/bold]\n\n"
            f"{insight.description}\n\n"
            f"[dim]Type: {insight.type.value} | "
            f"Confidence: {insight.confidence * 100:.0f}% | "
            f"Impact: [{impact_color}]{insight.impact}[/{impact_color}] | "
            f"Status: {insight.status.value}[/dim]\n\n"
            f"[dim]ID: {insight.id}[/dim]\n"
            f"[dim]Created: {insight.created_at}[/dim]",
            title="💡 Insight Details",
            border_style=impact_color,
        )
    )

    # Show entities
    if insight.entities:
        console.print("\n[bold]Related Entities:[/bold]")
        for entity in insight.entities:
            console.print(f"  • {entity}")

    # Show evidence summary
    if insight.evidence:
        console.print("\n[bold]Evidence:[/bold]")
        import json
        console.print(f"[dim]{json.dumps(insight.evidence, indent=2)[:500]}[/dim]")


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
