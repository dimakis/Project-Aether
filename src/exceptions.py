"""Aether exception hierarchy.

Base exceptions for all application layers with correlation ID support.

Usage:
    from src.exceptions import AgentError, DALError, HAClientError

    try:
        await agent.invoke(state)
    except AgentError as e:
        logger.error("Agent failed", correlation_id=e.correlation_id, cause=e.__cause__)
"""

import uuid
from typing import Any


class AetherError(Exception):
    """Base exception for all Aether application errors.

    Carries a correlation_id for tracing errors across layers.
    """

    def __init__(self, message: str, *, correlation_id: str | None = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        super().__init__(message)


class AgentError(AetherError):
    """Errors from agent operations."""

    def __init__(self, message: str, *, agent_role: str | None = None, **kwargs):
        self.agent_role = agent_role
        super().__init__(message, **kwargs)


class DALError(AetherError):
    """Errors from data access layer operations."""

    pass


class HAClientError(AetherError):
    """Errors from Home Assistant client operations.

    Raised when HA REST API calls fail, with optional tool name
    and detail context for diagnostics.
    """

    def __init__(
        self,
        message: str,
        tool: str | None = None,
        details: dict[str, Any] | None = None,
        *,
        status_code: int | None = None,
        correlation_id: str | None = None,
    ):
        self.tool = tool
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message, correlation_id=correlation_id)


class SandboxError(AetherError):
    """Errors from sandbox script execution."""

    def __init__(self, message: str, *, timeout: bool = False, **kwargs):
        self.timeout = timeout
        super().__init__(message, **kwargs)


class LLMError(AetherError):
    """Errors from LLM provider operations."""

    def __init__(self, message: str, *, provider: str | None = None, **kwargs):
        self.provider = provider
        super().__init__(message, **kwargs)


class ValidationError(AetherError):
    """Errors from input validation (beyond Pydantic)."""

    pass


class ConfigurationError(AetherError):
    """Errors from application configuration."""

    pass
