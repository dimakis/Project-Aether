"""Agent base classes and MLflow tracing integration.

Provides the foundation for all agents in the system with
consistent tracing, error handling, and state management.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator

import mlflow
from pydantic import BaseModel

from src.graph.state import AgentRole, BaseState
from src.settings import get_settings
from src.tracing import get_mlflow_client, start_experiment_run


class AgentContext(BaseModel):
    """Context passed to agents during execution."""

    run_id: str
    mlflow_run_id: str | None = None
    started_at: datetime
    agent_role: AgentRole
    metadata: dict[str, Any] = {}


class BaseAgent(ABC):
    """Base class for all agents.

    Provides:
    - MLflow tracing integration (Constitution: Observability)
    - Error handling and retry logic
    - State management helpers
    - Logging infrastructure
    """

    role: AgentRole

    def __init__(
        self,
        role: AgentRole,
        name: str | None = None,
    ):
        """Initialize agent.

        Args:
            role: Agent's role in the system
            name: Optional display name (defaults to role)
        """
        self.role = role
        self.name = name or role.value
        self._settings = get_settings()

    @asynccontextmanager
    async def trace_span(
        self,
        operation: str,
        state: BaseState | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Create an MLflow span for tracing.

        Args:
            operation: Name of the operation being traced
            state: Current graph state for context

        Yields:
            Span metadata dict that can be updated
        """
        span_name = f"{self.name}.{operation}"
        span_metadata: dict[str, Any] = {
            "agent_role": self.role.value,
            "operation": operation,
            "started_at": datetime.utcnow().isoformat(),
        }

        if state:
            span_metadata["run_id"] = state.run_id

        try:
            # Log to MLflow if available
            if mlflow.active_run():
                mlflow.log_param(f"{span_name}_started", datetime.utcnow().isoformat())

            yield span_metadata

            span_metadata["completed_at"] = datetime.utcnow().isoformat()
            span_metadata["status"] = "success"

            if mlflow.active_run():
                mlflow.log_param(f"{span_name}_status", "success")

        except Exception as e:
            span_metadata["completed_at"] = datetime.utcnow().isoformat()
            span_metadata["status"] = "error"
            span_metadata["error"] = str(e)

            if mlflow.active_run():
                mlflow.log_param(f"{span_name}_status", "error")
                mlflow.log_param(f"{span_name}_error", str(e)[:500])

            raise

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        """Log a metric to MLflow.

        Args:
            key: Metric name
            value: Metric value
            step: Optional step number
        """
        if mlflow.active_run():
            mlflow.log_metric(f"{self.name}.{key}", value, step=step)

    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter to MLflow.

        Args:
            key: Parameter name
            value: Parameter value
        """
        if mlflow.active_run():
            mlflow.log_param(f"{self.name}.{key}", str(value)[:500])

    @abstractmethod
    async def invoke(
        self,
        state: BaseState,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the agent's main function.

        Args:
            state: Current graph state
            **kwargs: Additional arguments

        Returns:
            State updates to apply
        """
        ...


class LibrarianAgent(BaseAgent):
    """The Librarian agent for entity discovery.

    Responsibilities:
    - Discover HA entities via MCP
    - Infer devices and areas from entity attributes
    - Sync entities to the local database
    - Track MCP capability gaps
    """

    def __init__(self):
        """Initialize Librarian agent."""
        super().__init__(
            role=AgentRole.LIBRARIAN,
            name="Librarian",
        )

    async def invoke(
        self,
        state: BaseState,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run entity discovery.

        This method is typically called from the discovery workflow graph.

        Args:
            state: Current discovery state
            **kwargs: Additional arguments (mcp_client, session)

        Returns:
            State updates with discovery results
        """
        # Implementation delegated to graph nodes for modularity
        # This method serves as the entry point
        from src.graph.nodes import run_discovery_node

        return await run_discovery_node(state, **kwargs)


# Import other agents
from src.agents.architect import ArchitectAgent, ArchitectWorkflow
from src.agents.developer import DeveloperAgent, DeveloperWorkflow

# Exports
__all__ = [
    "AgentContext",
    "BaseAgent",
    "LibrarianAgent",
    "ArchitectAgent",
    "ArchitectWorkflow",
    "DeveloperAgent",
    "DeveloperWorkflow",
]
