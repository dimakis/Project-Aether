"""Proposals commands."""

import asyncio
from typing import Annotated

import typer
import yaml
from rich.panel import Panel
from rich.table import Table

from src.cli.utils import console

app = typer.Typer(
    name="proposals",
    help="Manage automation proposals",
    no_args_is_help=True,
)


@app.command("list")
def proposals_list(
    status: Annotated[
        str | None,
        typer.Option(
            "--status", "-s", help="Filter by status (proposed, approved, deployed, etc.)"
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number to show"),
    ] = 20,
) -> None:
    """List automation proposals."""
    asyncio.run(_list_proposals(status, limit))


async def _list_proposals(status: str | None, limit: int) -> None:
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
                status_filter = ProposalStatus(status.lower())
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


@app.command("show")
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


@app.command("approve")
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
            console.print(f"[red]Cannot approve proposal in status {proposal.status.value}.[/red]")
            return

        await repo.approve(proposal_id, user)
        await session.commit()

        console.print(f"[green]✅ Proposal {proposal_id[:12]}... approved![/green]")
        console.print("[dim]Use 'aether proposals deploy <id>' to deploy.[/dim]")


@app.command("reject")
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
            console.print(f"[red]Cannot reject proposal in status {proposal.status.value}.[/red]")
            return

        await repo.reject(proposal_id, reason)
        await session.commit()

        console.print(f"[red]❌ Proposal {proposal_id[:12]}... rejected.[/red]")


@app.command("deploy")
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

            console.print("[green]✅ Deployment successful![/green]")
            console.print(f"[dim]Method: {result.get('deployment_method', 'manual')}[/dim]")
            console.print(f"[dim]HA Automation ID: {result.get('ha_automation_id', 'N/A')}[/dim]")

            if result.get("instructions"):
                console.print("\n[yellow]Manual steps required:[/yellow]")
                console.print(result["instructions"])

        except Exception as e:
            console.print(f"[red]Deployment failed: {e}[/red]")


@app.command("rollback")
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
                console.print("[green]✅ Rollback successful![/green]")
                if result.get("note"):
                    console.print(f"[dim]{result['note']}[/dim]")
            else:
                console.print(f"[red]Rollback failed: {result.get('error', 'Unknown')}[/red]")

        except Exception as e:
            console.print(f"[red]Rollback failed: {e}[/red]")
