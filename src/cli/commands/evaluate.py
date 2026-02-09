"""Evaluate command -- run MLflow 3.x GenAI evaluation on recent traces.

Uses custom scorers from src.tracing.scorers to assess agent quality
across dimensions like latency, safety, and delegation depth.

Example:
    aether evaluate --traces 50
    aether evaluate --hours 48 --traces 100
"""

import asyncio
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from src.cli.utils import console


def evaluate(
    traces: Annotated[
        int,
        typer.Option("--traces", "-t", help="Maximum number of traces to evaluate"),
    ] = 50,
    hours: Annotated[
        int,
        typer.Option("--hours", "-h", help="Only evaluate traces from the last N hours"),
    ] = 24,
    experiment: Annotated[
        str | None,
        typer.Option("--experiment", "-e", help="MLflow experiment name (default from settings)"),
    ] = None,
) -> None:
    """Evaluate recent agent traces with quality scorers.

    Runs MLflow 3.x GenAI evaluation on recent traces using custom
    scorers that measure latency, safety, delegation depth, and tool usage.

    Results are logged to MLflow and displayed in the terminal.

    Examples:
        aether evaluate                    # Last 24h, up to 50 traces
        aether evaluate --traces 100       # More traces
        aether evaluate --hours 48         # Wider time window
    """
    asyncio.run(_run_evaluation(traces, hours, experiment))


async def _run_evaluation(
    max_traces: int,
    hours: int,
    experiment_name: str | None,
) -> None:
    """Run trace evaluation with custom scorers."""
    from src.tracing import init_mlflow

    # Initialize MLflow
    client = init_mlflow()
    if client is None:
        console.print("[red]MLflow is not available. Cannot run evaluation.[/red]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"Evaluating up to {max_traces} traces from the last {hours}h",
            title="Aether Trace Evaluation",
            border_style="blue",
        )
    )

    # Search for recent traces
    console.print("[dim]Searching for traces...[/dim]")

    try:
        import mlflow

        from src.settings import get_settings

        settings = get_settings()
        names = [experiment_name] if experiment_name else [settings.mlflow_experiment_name]

        trace_df = mlflow.search_traces(
            experiment_names=names,
            max_results=max_traces,
        )
    except Exception as e:
        console.print(f"[red]Failed to search traces: {e}[/red]")
        raise typer.Exit(code=1) from e

    if trace_df is None or len(trace_df) == 0:
        console.print("[yellow]No traces found in the specified time window.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[green]Found {len(trace_df)} trace(s)[/green]")

    # Load scorers
    from src.tracing.scorers import get_all_scorers

    scorers = get_all_scorers()
    if not scorers:
        console.print("[red]No scorers available. Is mlflow.genai installed?[/red]")
        raise typer.Exit(code=1)

    scorer_names = [getattr(s, "__name__", str(s)) for s in scorers]
    console.print(f"[dim]Running {len(scorers)} scorer(s): {', '.join(scorer_names)}[/dim]")

    # Run evaluation
    try:
        import mlflow.genai

        eval_result = mlflow.genai.evaluate(
            data=trace_df,
            scorers=scorers,
        )
    except Exception as e:
        console.print(f"[red]Evaluation failed: {e}[/red]")
        raise typer.Exit(code=1) from e

    # Display results
    _display_results(eval_result, len(trace_df))

    console.print(
        "\n[dim]Full results are available in the MLflow UI "
        "under the evaluation run.[/dim]"
    )


def _display_results(eval_result: object, trace_count: int) -> None:
    """Format and display evaluation results in the terminal.

    Args:
        eval_result: The result from mlflow.genai.evaluate()
        trace_count: Number of traces evaluated
    """
    # Extract metrics from the evaluation result
    metrics_table = getattr(eval_result, "metrics", None)
    aggregate_results = getattr(eval_result, "aggregate_results", None)

    # Summary table
    table = Table(
        title=f"Evaluation Results ({trace_count} traces)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Scorer", style="bold")
    table.add_column("Pass Rate", justify="right")
    table.add_column("Details", style="dim")

    if metrics_table is not None and hasattr(metrics_table, "items"):
        for metric_name, metric_value in metrics_table.items():
            _format = _format_metric(metric_value)
            table.add_row(metric_name, _format, "")
    elif aggregate_results is not None and hasattr(aggregate_results, "items"):
        for scorer_name, result in aggregate_results.items():
            if hasattr(result, "items"):
                for metric_name, metric_value in result.items():
                    _format = _format_metric(metric_value)
                    table.add_row(f"{scorer_name}/{metric_name}", _format, "")
            else:
                _format = _format_metric(result)
                table.add_row(scorer_name, _format, "")
    else:
        # Fall back to string representation
        table.add_row("Result", str(eval_result), "")

    console.print(table)

    # Show run ID if available
    run_id = getattr(eval_result, "run_id", None)
    if run_id:
        console.print(f"\n[dim]MLflow evaluation run ID: {run_id}[/dim]")


def _format_metric(value: object) -> str:
    """Format a metric value for display."""
    if isinstance(value, float):
        return f"{value:.1%}" if 0 <= value <= 1 else f"{value:.2f}"
    if isinstance(value, bool):
        return "[green]PASS[/green]" if value else "[red]FAIL[/red]"
    return str(value)
