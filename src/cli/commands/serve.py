"""Server commands."""

from typing import Annotated

import typer
from rich.panel import Panel

from src.cli.utils import console
from src.settings import get_settings


def serve(
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="Host to bind to"),
    ] = "",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to bind to"),
    ] = 0,
    reload: Annotated[
        bool,
        typer.Option("--reload", "-r", help="Enable auto-reload for development"),
    ] = False,
    workers: Annotated[
        int,
        typer.Option("--workers", "-w", help="Number of worker processes"),
    ] = 0,
) -> None:
    """Start the Aether API server.

    Runs the FastAPI application with uvicorn.
    Defaults are loaded from settings (env vars / .env).
    """
    import uvicorn

    settings = get_settings()
    resolved_host = host or settings.api_host
    resolved_port = port or settings.api_port
    resolved_workers = workers or settings.api_workers

    console.print(
        Panel(
            f"[bold green]Starting Aether API Server[/bold green]\n"
            f"Host: {resolved_host}\n"
            f"Port: {resolved_port}\n"
            f"Workers: {resolved_workers}\n"
            f"Reload: {reload}",
            title="🏠 Aether",
            border_style="green",
        )
    )

    uvicorn.run(
        "src.api.main:app",
        host=resolved_host,
        port=resolved_port,
        reload=reload,
        workers=resolved_workers if not reload else 1,
        log_level="info",
    )
