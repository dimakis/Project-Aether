"""Analysis commands."""

import asyncio
import json
from typing import Annotated, Optional

import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.cli.utils import console


def analyze(
    analysis_type: Annotated[
        str,
        typer.Argument(
            help="Analysis type: energy, anomaly, pattern, custom, "
            "behavior, automations, gaps, correlations, health, cost"
        ),
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
    """Run analysis with the Data Scientist agent.

    Analyzes energy sensor data or behavioral patterns and generates insights.

    Examples:
        aether analyze energy --days 7
        aether analyze anomaly --entity sensor.grid_power
        aether analyze custom --query "Find peak usage times"
        aether analyze behavior --days 7
        aether analyze automations --days 14
        aether analyze gaps --days 7
        aether analyze correlations --days 7
        aether analyze health --days 2
        aether analyze cost --days 30
    """
    asyncio.run(_run_analysis(analysis_type, days, entity, query))


async def _run_analysis(
    analysis_type: str,
    days: int,
    entity: str | None,
    query: str | None,
) -> None:
    """Run energy analysis."""
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
        # Feature 03: Behavioral analysis types
        "behavior": AnalysisType.BEHAVIOR_ANALYSIS,
        "automations": AnalysisType.AUTOMATION_ANALYSIS,
        "gaps": AnalysisType.AUTOMATION_GAP_DETECTION,
        "correlations": AnalysisType.CORRELATION_DISCOVERY,
        "health": AnalysisType.DEVICE_HEALTH,
        "cost": AnalysisType.COST_OPTIMIZATION,
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

    # Display automation suggestion (if any)
    suggestion = getattr(state, "automation_suggestion", None)
    if suggestion and hasattr(suggestion, "pattern"):
        console.print()
        console.print(
            Panel(
                f"[bold]Pattern:[/bold] {suggestion.pattern[:300]}\n"
                f"[bold]Trigger:[/bold] {suggestion.proposed_trigger}\n"
                f"[bold]Action:[/bold] {suggestion.proposed_action}",
                title="🤖 Automation Suggestion",
                border_style="yellow",
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
        console.print(f"[dim]{json.dumps(insight.evidence, indent=2)[:500]}[/dim]")


def optimize(
    analysis_type: Annotated[
        str,
        typer.Argument(
            help="Optimization type: behavior, automations, gaps, correlations, health, cost, all"
        ),
    ] = "all",
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Days of history to analyze"),
    ] = 7,
    entity: Annotated[
        Optional[str],  # noqa: UP007
        typer.Option("--entity", "-e", help="Specific entity to focus on"),
    ] = None,
) -> None:
    """Run intelligent optimization analysis.

    Analyzes behavioral patterns, detects automation gaps, and
    suggests automations. Combines Data Scientist insights with
    Architect proposals.

    Examples:
        aether optimize --days 7
        aether optimize gaps --days 14
        aether optimize automations --days 30
        aether optimize all --days 7
    """
    asyncio.run(_run_optimization(analysis_type, days, entity))


async def _run_optimization(
    analysis_type: str,
    days: int,
    entity: str | None,
) -> None:
    """Run optimization analysis."""
    from src.graph.state import AnalysisType
    from src.graph.workflows import run_optimization_workflow
    from src.storage import get_session
    from src.tracing import init_mlflow

    init_mlflow()

    # Map types
    type_map = {
        "behavior": "behavior_analysis",
        "automations": "automation_analysis",
        "gaps": "automation_gap_detection",
        "correlations": "correlation_discovery",
        "health": "device_health",
        "cost": "cost_optimization",
    }

    # If "all", run behavior analysis (the most comprehensive)
    opt_type = type_map.get(analysis_type.lower(), "behavior_analysis")
    entity_ids = [entity] if entity else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running optimization...", total=None)

        try:
            async with get_session() as session:
                progress.update(task, description="[cyan]Collecting behavioral data...")

                state = await run_optimization_workflow(
                    analysis_type=opt_type,
                    entity_ids=entity_ids,
                    hours=days * 24,
                    session=session,
                )
                await session.commit()

                progress.update(task, description="[green]Optimization complete!")

        except Exception as e:
            console.print(f"[red]Optimization failed: {e}[/red]")
            return

    # Display results
    console.print()
    console.print(
        Panel(
            f"[bold]Optimization: {analysis_type.title()}[/bold]\n"
            f"Period: {days} day(s)\n"
            f"Insights found: {len(state.insights)}\n"
            f"Automation suggestion: {'Yes' if state.automation_suggestion else 'No'}",
            title="🔍 Optimization Results",
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
            insight_type = insight.get("type", "").replace("_", " ").title()

            console.print()
            console.print(
                Panel(
                    f"[bold]{insight.get('title', 'Untitled')}[/bold]\n"
                    f"[dim]Type: {insight_type}[/dim]\n\n"
                    f"{insight.get('description', 'No description')}\n\n"
                    f"[dim]Confidence: {confidence:.0f}% | "
                    f"Impact: [{impact_color}]{insight.get('impact', 'unknown')}[/{impact_color}][/dim]",
                    title=f"💡 Insight {i}",
                    border_style=impact_color,
                )
            )

    # Display automation suggestion
    if state.automation_suggestion:
        s = state.automation_suggestion
        console.print()
        console.print(
            Panel(
                f"[bold]Pattern:[/bold] {s.pattern[:300]}\n\n"
                f"[bold]Trigger:[/bold] {s.proposed_trigger}\n"
                f"[bold]Action:[/bold] {s.proposed_action}\n"
                f"[bold]Confidence:[/bold] {s.confidence:.0%}\n"
                f"[bold]Entities:[/bold] {', '.join(s.entities[:5])}",
                title="🤖 Automation Suggestion",
                border_style="yellow",
            )
        )
        console.print(
            "[yellow]Run [bold]aether proposals[/bold] to view and approve this suggestion.[/yellow]"
        )

    # Display recommendations
    if state.recommendations:
        console.print()
        console.print("[bold]📋 Recommendations:[/bold]")
        for rec in state.recommendations:
            console.print(f"  • {rec}")
    else:
        console.print("\n[dim]No specific recommendations generated.[/dim]")
