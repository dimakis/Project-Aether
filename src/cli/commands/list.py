"""List commands for entities, areas, devices, etc."""

import asyncio
from typing import Annotated, Optional

import typer
from rich.panel import Panel
from rich.table import Table

from src.cli.utils import console


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


def areas() -> None:
    """List discovered areas."""
    asyncio.run(_list_areas())


async def _list_areas() -> None:
    """List areas from database."""
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
