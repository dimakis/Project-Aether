"""FastAPI application factory for Project Aether.

Provides the main application instance and factory function
for creating configured FastAPI apps.
"""

from src.api.main import create_app, get_app

__all__ = [
    "create_app",
    "get_app",
]
