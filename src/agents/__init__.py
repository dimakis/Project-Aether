"""Agent base classes and MLflow tracing integration.

Provides the foundation for all agents in the system with
consistent tracing, error handling, and state management.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

from src.agents.execution_context import emit_progress
from src.graph.state import AgentRole, BaseState
from src.settings import get_settings
from src.tracing import add_span_event, get_active_span, log_dict, log_param


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
    - Session context correlation for trace linking
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
        inputs: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Create a tracing span for an operation.

        This is defensive - if MLflow is unavailable, the operation
        continues without tracing. Automatically includes session ID
        for trace correlation.

        Args:
            operation: Name of the operation being traced
            state: Current graph state for context
            inputs: Optional input data to log on the span

        Yields:
            Span metadata dict that can be updated. Set 'outputs' key
            to log output data on the span.
        """
        span_name = f"{self.name}.{operation}"
        span_metadata: dict[str, Any] = {
            "agent_role": self.role.value,
            "operation": operation,
            "started_at": datetime.now(UTC).isoformat(),
        }

        if state:
            span_metadata["run_id"] = state.run_id

        # Get session ID for correlation
        # Prefer conversation_id from state for multi-turn trace correlation
        session_id = None
        try:
            # First try to use conversation_id from state (most reliable)
            if state and hasattr(state, "conversation_id"):
                session_id = getattr(state, "conversation_id", None)

            # Fall back to session context if no conversation_id
            if not session_id:
                from src.tracing.context import get_session_id

                session_id = get_session_id()

            if session_id:
                span_metadata["session_id"] = session_id
        except Exception:
            logger.debug("Failed to get session ID for trace correlation", exc_info=True)

        # Log state context (session, messages, etc.)
        self._log_state_context(state)

        # Try to create MLflow span, but don't fail if unavailable
        span = None
        mlflow_available = False
        ctx = None

        try:
            import mlflow

            mlflow.set_tracking_uri(self._settings.mlflow_tracking_uri)
            mlflow_available = True
        except Exception:
            logger.debug("MLflow not available, tracing disabled", exc_info=True)

        if mlflow_available:
            try:
                span_attrs = {
                    "agent": self.name,
                    "agent_role": self.role.value,
                    "operation": operation,
                }
                if state:
                    span_attrs["run_id"] = state.run_id
                if session_id:
                    span_attrs["session.id"] = session_id

                # Try to create span
                import mlflow

                ctx = mlflow.start_span(name=span_name, span_type="CHAIN", attributes=span_attrs)
                ctx.__enter__()
                span = get_active_span()
                add_span_event(span, "start", {"operation": operation})

                # Set trace session metadata for multi-turn correlation
                # This enables MLflow UI to group traces by session
                if session_id:
                    try:
                        mlflow.update_current_trace(tags={"mlflow.trace.session": session_id})
                    except Exception:
                        logger.debug("Failed to update trace session metadata", exc_info=True)

                # Set span inputs if provided
                if inputs and span:
                    self._set_span_inputs(span, inputs)
            except Exception:
                # MLflow span creation failed, continue without tracing
                logger.debug("Failed to create MLflow span", exc_info=True)
                mlflow_available = False
                span = None
                ctx = None

        try:
            # Auto-emit agent_start to execution context progress queue
            emit_progress("agent_start", self.role.value, f"{self.name} started")

            yield span_metadata

            span_metadata["completed_at"] = datetime.now(UTC).isoformat()
            span_metadata["status"] = "success"

            # Set span outputs if provided in metadata
            if span and "outputs" in span_metadata:
                self._set_span_outputs(span, span_metadata["outputs"])

            add_span_event(span, "end", {"status": "success"})

            # Auto-emit agent_end on success
            emit_progress("agent_end", self.role.value, f"{self.name} completed")

        except Exception as e:
            span_metadata["completed_at"] = datetime.now(UTC).isoformat()
            span_metadata["status"] = "error"
            span_metadata["error"] = str(e)

            if span and hasattr(span, "set_status"):
                try:
                    span.set_status("ERROR")
                except Exception:
                    logger.debug("Failed to set span error status", exc_info=True)
            add_span_event(span, "error", {"error": str(e)[:250]})

            # Auto-emit agent_end on error
            emit_progress("agent_end", self.role.value, f"{self.name} failed")
            raise

        finally:
            # Clean up span context if we created one
            if mlflow_available and ctx is not None:
                try:
                    ctx.__exit__(None, None, None)
                except Exception:
                    logger.debug("Failed to close MLflow span context", exc_info=True)

    def _set_span_inputs(self, span: Any, inputs: dict[str, Any]) -> None:
        """Set inputs on a span for MLflow trace visualization.

        Args:
            span: MLflow span object
            inputs: Input data to set
        """
        if span is None:
            return
        try:
            if hasattr(span, "set_inputs"):
                span.set_inputs(inputs)
            elif hasattr(span, "set_attribute"):
                # Fallback for older MLflow versions
                import json

                span.set_attribute("inputs", json.dumps(inputs, default=str)[:4000])
        except Exception:
            logger.debug("Failed to set span inputs", exc_info=True)

    def _set_span_outputs(self, span: Any, outputs: dict[str, Any]) -> None:
        """Set outputs on a span for MLflow trace visualization.

        Args:
            span: MLflow span object
            outputs: Output data to set
        """
        if span is None:
            return
        try:
            if hasattr(span, "set_outputs"):
                span.set_outputs(outputs)
            elif hasattr(span, "set_attribute"):
                # Fallback for older MLflow versions
                import json

                span.set_attribute("outputs", json.dumps(outputs, default=str)[:4000])
        except Exception:
            logger.debug("Failed to set span outputs", exc_info=True)

    def _log_state_context(self, state: BaseState | None) -> None:
        """Log state context to MLflow.

        Args:
            state: Current state to log
        """
        if state is None:
            return

        # Log basic state info
        log_param(f"{self.name}.run_id", state.run_id)
        log_param(
            f"{self.name}.agent",
            state.current_agent.value if state.current_agent else "unknown",
        )

        # Log session ID if available
        try:
            from src.tracing.context import get_session_id

            session_id = get_session_id()
            if session_id:
                log_param(f"{self.name}.session_id", session_id)
        except Exception:
            logger.debug("Failed to log session ID to MLflow", exc_info=True)

        # Log conversation-specific context if available
        if hasattr(state, "conversation_id"):
            log_param(f"{self.name}.conversation_id", state.conversation_id)

        # Log messages if available (for conversation states)
        if hasattr(state, "messages") and state.messages:
            messages = state.messages
            log_param(f"{self.name}.message_count", len(messages))

            # Log the latest message
            if messages:
                latest = messages[-1]
                content = getattr(latest, "content", str(latest))
                msg_type = type(latest).__name__
                log_param(f"{self.name}.latest_message_type", msg_type)
                log_param(f"{self.name}.latest_message", str(content)[:500])

        # Log discovery-specific context if available
        if hasattr(state, "status"):
            log_param(f"{self.name}.status", str(state.status))

    def log_conversation(
        self,
        conversation_id: str,
        messages: list[Any],
        response: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        """Log a conversation to MLflow as an artifact.

        Note: Token usage is automatically captured by MLflow autolog for
        LangChain and OpenAI calls, so it's not tracked here.

        Args:
            conversation_id: Unique conversation ID
            messages: List of messages in the conversation
            response: Optional new response to append
            tool_calls: Optional list of tool calls made
        """
        import time

        # Serialize messages
        serialized = []
        for msg in messages:
            msg_type = type(msg).__name__
            if "Human" in msg_type or "user" in msg_type.lower():
                role = "user"
            elif "AI" in msg_type or "assistant" in msg_type.lower():
                role = "assistant"
            elif "System" in msg_type:
                role = "system"
            elif "Tool" in msg_type:
                role = "tool"
            else:
                role = msg_type.lower()

            content = getattr(msg, "content", str(msg))

            # Build message dict
            msg_dict: dict[str, Any] = {
                "role": role,
                "content": str(content)[:2000],
            }

            # Include tool call info if present
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "name": tc.get("name", "unknown"),
                        "args": tc.get("args", {}),
                    }
                    for tc in msg.tool_calls[:10]  # Limit to 10 tool calls
                ]

            serialized.append(msg_dict)

        # Add new response if provided
        if response:
            serialized.append({"role": "assistant", "content": response[:2000]})

        # Build artifact data
        artifact_data: dict[str, Any] = {
            "agent": self.name,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "message_count": len(serialized),
            "messages": serialized,
        }

        # Add session ID if available
        try:
            from src.tracing.context import get_session_id

            session_id = get_session_id()
            if session_id:
                artifact_data["session_id"] = session_id
        except Exception:
            logger.debug("Failed to get session ID for conversation log", exc_info=True)

        # Add tool calls if provided
        if tool_calls:
            artifact_data["tool_calls"] = [
                {
                    "name": tc.get("name", "unknown"),
                    "args": tc.get("args", {}),
                    "result": str(tc.get("result", ""))[:500] if tc.get("result") else None,
                }
                for tc in tool_calls[:20]  # Limit to 20 tool calls
            ]

        # Log as artifact
        log_dict(
            artifact_data,
            f"conversations/{self.name}_{conversation_id}_{int(time.time())}.json",
        )

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        """Log a metric to MLflow.

        Args:
            key: Metric name
            value: Metric value
            step: Optional step number
        """
        try:
            import mlflow

            if mlflow.active_run():
                mlflow.log_metric(f"{self.name}.{key}", value, step=step)
        except Exception:
            logger.debug("Failed to log metric %s to MLflow", key, exc_info=True)

    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter to MLflow.

        Args:
            key: Parameter name
            value: Parameter value
        """
        log_param(f"{self.name}.{key}", str(value)[:500])

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

    def __init__(self) -> None:
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
            **kwargs: Additional arguments (ha_client, session)

        Returns:
            State updates with discovery results
        """
        # Implementation delegated to graph nodes for modularity
        # This method serves as the entry point
        from typing import cast

        from src.graph.nodes import run_discovery_node
        from src.graph.state import DiscoveryState

        return await run_discovery_node(cast("DiscoveryState", state), **kwargs)


# Import other agents
from src.agents.architect import ArchitectAgent, ArchitectWorkflow, StreamEvent
from src.agents.behavioral_analyst import BehavioralAnalyst
from src.agents.dashboard_designer import DashboardDesignerAgent
from src.agents.data_scientist import DataScientistAgent, DataScientistWorkflow
from src.agents.developer import DeveloperAgent, DeveloperWorkflow
from src.agents.diagnostic_analyst import DiagnosticAnalyst
from src.agents.energy_analyst import EnergyAnalyst

# Exports
__all__ = [
    "AgentContext",
    "ArchitectAgent",
    "ArchitectWorkflow",
    "BaseAgent",
    "BehavioralAnalyst",
    "DashboardDesignerAgent",
    "DataScientistAgent",
    "DataScientistWorkflow",
    "DeveloperAgent",
    "DeveloperWorkflow",
    "DiagnosticAnalyst",
    "EnergyAnalyst",
    "LibrarianAgent",
    "StreamEvent",
]
