"""A2A service wrapper for BaseAgent (Phase 3).

Wraps any ``BaseAgent`` subclass into an A2A-protocol-compliant service
using the ``a2a-sdk``.  The service exposes:

- JSON-RPC endpoint (``/``) for ``SendMessage`` / ``SendStreamingMessage``
- Agent Card at ``/.well-known/agent.json``
- Health (``/health``) and readiness (``/ready``) endpoints

The wrapper is agent-agnostic — it receives the agent instance and
metadata as parameters, not import-time dependencies.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.events import InMemoryQueueManager
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from starlette.applications import Starlette  # noqa: TC002 — used as return type
from starlette.requests import Request  # noqa: TC002 — used in route handler signatures
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from a2a.server.agent_execution.context import RequestContext
    from a2a.server.events import EventQueue

    from src.agents.base import BaseAgent
    from src.graph.state import BaseState

logger = logging.getLogger(__name__)

_MAX_USER_MESSAGE_LEN = 4000


def pack_state_to_data(state: BaseState) -> dict[str, Any]:
    """Serialize a Pydantic state to a dict suitable for A2A DataPart.

    LangChain messages are serialized separately via ``dumpd()``
    to preserve their type information across the wire.
    """
    from langchain_core.load import dumpd

    data = state.model_dump(mode="json", exclude={"messages"})

    if hasattr(state, "messages") and state.messages:
        data["_lc_messages"] = [dumpd(m) for m in state.messages]

    return data


def unpack_data_to_state_updates(data: dict[str, Any]) -> dict[str, Any]:
    """Convert an A2A DataPart dict back to state update fields.

    Strips internal keys (prefixed with ``_``) and returns only
    the fields that should be merged into the graph state.
    """
    return {k: v for k, v in data.items() if not k.startswith("_")}


class AetherAgentExecutor(AgentExecutor):
    """Bridges a ``BaseAgent`` to the A2A ``AgentExecutor`` interface.

    On ``execute()``, extracts the user message from the A2A request
    context, constructs a minimal state, invokes the agent, and
    pushes the result onto the event queue.
    """

    def __init__(
        self,
        agent: BaseAgent,
        state_type: str = "ConversationState",
    ) -> None:
        self.agent = agent
        self.state_type = state_type

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle an A2A SendMessage request."""
        state = _extract_state_from_context(context, self.state_type)

        try:
            task_id = context.task_id or "unknown"
            context_id = context.context_id or "unknown"

            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    final=False,
                    status=TaskStatus(state=TaskState.working),
                )
            )

            result = await self.agent.invoke(state)

            from a2a.types import (
                Artifact,
                DataPart,
                Part,
                TaskArtifactUpdateEvent,
            )

            artifact = Artifact(
                artifact_id="result-0",
                parts=[Part(root=DataPart(data=result))],
            )

            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    artifact=artifact,
                )
            )

            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    final=True,
                    status=TaskStatus(state=TaskState.completed),
                )
            )
        except Exception:
            logger.exception("Agent execution failed")
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id or "unknown",
                    context_id=context.context_id or "unknown",
                    final=True,
                    status=TaskStatus(state=TaskState.failed),
                )
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle task cancellation."""
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or "unknown",
                context_id=context.context_id or "unknown",
                final=True,
                status=TaskStatus(state=TaskState.canceled),
            )
        )


def _extract_user_text(context: RequestContext) -> str:
    """Extract plain text from the A2A request context."""
    if context.message and context.message.parts:
        for part in context.message.parts:
            inner = part.root if hasattr(part, "root") else part
            if hasattr(inner, "text"):
                return str(inner.text)
    return ""


_STATE_TYPE_MAP: dict[str, type] = {}


def _get_state_class(state_type: str) -> type | None:
    """Resolve a state type name to its class (lazy-loaded)."""
    if not _STATE_TYPE_MAP:
        from src.graph.state import AnalysisState, ConversationState

        _STATE_TYPE_MAP.update(
            {
                "ConversationState": ConversationState,
                "AnalysisState": AnalysisState,
            }
        )
    return _STATE_TYPE_MAP.get(state_type)


def _extract_state_from_context(
    context: RequestContext,
    state_type: str = "ConversationState",
) -> Any:
    """Extract full state from A2A context, checking DataPart first.

    If the message contains a DataPart with serialized state fields,
    reconstructs the full state object including LangChain messages.
    Falls back to creating a minimal state from text content.

    Args:
        context: The A2A request context.
        state_type: Name of the state class to construct.

    Returns:
        A state object (ConversationState, AnalysisState, etc.).
    """
    from langchain_core.load import load
    from langchain_core.messages import HumanMessage

    state_cls = _get_state_class(state_type)
    if state_cls is None:
        from src.graph.state import ConversationState

        state_cls = ConversationState

    if context.message and context.message.parts:
        for part in context.message.parts:
            inner = part.root if hasattr(part, "root") else part
            if hasattr(inner, "data") and isinstance(inner.data, dict):
                data = dict(inner.data)
                lc_messages_raw = data.pop("_lc_messages", None)

                messages = []
                if lc_messages_raw:
                    messages = [load(m) for m in lc_messages_raw]

                if messages:
                    data["messages"] = messages

                return state_cls(**data)

    user_text = _extract_user_text(context)
    return state_cls(
        messages=[HumanMessage(content=user_text[:_MAX_USER_MESSAGE_LEN])],
    )


async def _health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def _ready(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ready"})


def _noop_agent() -> Any:
    """Return a minimal agent stub for when no real agent is provided."""

    class _Noop:
        async def invoke(self, state: Any, **kwargs: Any) -> dict[str, Any]:
            return {}

    return _Noop()


def create_a2a_service(
    agent_name: str,
    agent_description: str,
    agent_skills: list[dict[str, str]],
    agent: BaseAgent | None = None,
) -> Starlette:
    """Create an A2A-compliant service wrapping a BaseAgent.

    Args:
        agent_name: Name for the Agent Card.
        agent_description: Description for the Agent Card.
        agent_skills: List of skill dicts (id, name, description).
        agent: Optional BaseAgent instance (for executor).

    Returns:
        A Starlette/FastAPI application ready to serve.
    """
    skills = [
        AgentSkill(
            id=s["id"],
            name=s["name"],
            description=s.get("description", ""),
            input_modes=["text"],
            output_modes=["text"],
            tags=[],
        )
        for s in agent_skills
    ]

    card = AgentCard(
        name=agent_name,
        description=agent_description,
        url="http://localhost:8000",
        version="0.3.0",
        skills=skills,
        capabilities=AgentCapabilities(),
        default_input_modes=["text"],
        default_output_modes=["text"],
    )

    if agent is not None:
        executor = AetherAgentExecutor(agent)
    else:
        executor = AetherAgentExecutor(_noop_agent())

    task_store = InMemoryTaskStore()
    queue_manager = InMemoryQueueManager()

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        queue_manager=queue_manager,
    )

    a2a_app = A2AFastAPIApplication(
        agent_card=card,
        http_handler=handler,
    )

    app = a2a_app.build()
    app.add_route("/health", _health, methods=["GET"])
    app.add_route("/ready", _ready, methods=["GET"])

    # Prometheus metrics endpoint at /metrics
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, include_in_schema=False)

    return app
