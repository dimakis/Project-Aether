#!/usr/bin/env python3
"""Generate the OpenAPI spec from the running FastAPI application.

Usage:
    python scripts/generate_openapi.py            # write to default output
    python scripts/generate_openapi.py --check     # exit non-zero if committed spec is stale
    python scripts/generate_openapi.py -o /tmp/x   # write to custom path

Outputs to: specs/001-project-aether/contracts/api.yaml
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

import yaml

# Set testing environment to skip DB/MLflow initialization
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("HA_URL", "http://localhost:8123")
os.environ.setdefault("HA_TOKEN", "dummy")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("OPENAI_API_KEY", "dummy")

from src.api.main import create_app

DEFAULT_OUTPUT = Path("specs/001-project-aether/contracts/api.yaml")


def _build_schema() -> dict[str, Any]:
    app = create_app()
    schema = app.openapi()

    schema["info"] = {
        "title": "Project Aether API",
        "description": (
            "API for Project Aether — an intelligent home automation system "
            "with multi-agent architecture.\n\n"
            "## Architecture\n\n"
            "Aether uses a multi-agent system (Architect, Data Scientist, Librarian, Developer) "
            "orchestrated via LangGraph workflows and traced via MLflow. The Architect agent "
            "handles user conversations, delegates to specialists, and proposes Home Assistant "
            "automations.\n\n"
            "## Constitution Compliance\n\n"
            "- **Safety First**: All automation proposals require explicit HITL approval before deployment\n"
            "- **Isolation**: All analysis scripts run in sandboxed containers (gVisor/Podman)\n"
            "- **Observability**: Every agent interaction is traced via MLflow\n"
            "- **State**: LangGraph + PostgreSQL for persistent state management\n\n"
            "## OpenAI Compatibility\n\n"
            "The /v1/chat/completions and /v1/models endpoints are OpenAI-compatible, "
            "allowing integration with tools like Open WebUI.\n"
        ),
        "version": "0.4.0",
        "contact": {"name": "Project Aether"},
        "license": {"name": "MIT"},
    }

    schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "http://aether.local:8000", "description": "Home network"},
    ]

    return schema


def _dump_yaml(schema: dict[str, Any]) -> str:
    return yaml.dump(
        schema,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )


def _write(schema: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_dump_yaml(schema))

    path_count = len(schema["paths"])
    schema_count = len(schema.get("components", {}).get("schemas", {}))
    print(f"OpenAPI spec written to {output}")
    print(f"   {path_count} paths, {schema_count} schemas")


def _check(schema: dict[str, Any]) -> int:
    """Return 0 if committed spec matches, 1 if stale."""
    fresh = _dump_yaml(schema)

    if not DEFAULT_OUTPUT.exists():
        print(f"ERROR: {DEFAULT_OUTPUT} does not exist. Run 'make openapi' first.")
        return 1

    committed = DEFAULT_OUTPUT.read_text()

    if fresh == committed:
        print(f"OpenAPI spec is up-to-date ({DEFAULT_OUTPUT})")
        return 0

    diff = difflib.unified_diff(
        committed.splitlines(keepends=True),
        fresh.splitlines(keepends=True),
        fromfile=f"{DEFAULT_OUTPUT} (committed)",
        tofile=f"{DEFAULT_OUTPUT} (regenerated)",
    )
    sys.stdout.writelines(diff)
    print(f"\nERROR: {DEFAULT_OUTPUT} is stale. Run 'make openapi' and commit the result.")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or check OpenAPI spec")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Custom output path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed spec matches; exit non-zero if stale",
    )
    args = parser.parse_args()

    schema = _build_schema()

    if args.check:
        sys.exit(_check(schema))
    else:
        _write(schema, args.output or DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
