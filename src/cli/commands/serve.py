"""Server commands."""

from typing import Annotated

import typer
from rich.panel import Panel

from src.cli.utils import console


def serve(
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="Host to bind to"),
    ] = "0.0.0.0",
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
