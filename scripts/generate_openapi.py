#!/usr/bin/env python3
"""Generate the OpenAPI spec from the running FastAPI application.

Usage:
    python scripts/generate_openapi.py
    # or
    make openapi

Outputs to: specs/001-project-aether/contracts/api.yaml
"""

import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os  # noqa: E402

import yaml  # noqa: E402

# Set testing environment to skip DB/MLflow initialization
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("HA_URL", "http://localhost:8123")
os.environ.setdefault("HA_TOKEN", "dummy")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("OPENAI_API_KEY", "dummy")

from src.api.main import create_app  # noqa: E402

app = create_app()

OUTPUT = Path("specs/001-project-aether/contracts/api.yaml")


def main() -> None:
    schema = app.openapi()

    # Enhance info
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

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        yaml.dump(
            schema,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )

    path_count = len(schema["paths"])
    schema_count = len(schema.get("components", {}).get("schemas", {}))
    print(f"✅ OpenAPI spec written to {OUTPUT}")
    print(f"   {path_count} paths, {schema_count} schemas")


if __name__ == "__main__":
    main()
