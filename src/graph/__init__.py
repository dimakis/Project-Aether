"""LangGraph configuration and utilities.

Provides core LangGraph imports, configuration, and shared utilities
for building agent graphs (Constitution: State).
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph as CompiledGraph

from src.settings import get_settings

# Re-export common LangGraph types for convenience
__all__ = [
    # Graph building
    "StateGraph",
    "CompiledGraph",
    "START",
    "END",
    # Messages
    "AIMessage",
    "HumanMessage",
    "SystemMessage",
    # Utilities
    "get_llm",
    "create_graph",
    # Workflows
    "get_workflow",
    "run_discovery_workflow",
]


def get_workflow(name: str, **kwargs):  # type: ignore[no-untyped-def]
    """Get a workflow graph by name.

    Lazy import to avoid circular dependencies.
    """
    from src.graph.workflows import get_workflow as _get_workflow
    return _get_workflow(name, **kwargs)


async def run_discovery_workflow(**kwargs):  # type: ignore[no-untyped-def]
    """Run the discovery workflow.

    Lazy import to avoid circular dependencies.
    """
    from src.graph.workflows import run_discovery_workflow as _run
    return await _run(**kwargs)


def get_llm(
    model: str | None = None,
    temperature: float = 0.0,
    **kwargs: Any,
) -> ChatOpenAI:
    """Get configured LLM instance.

    Args:
        model: OpenAI model name (default from settings)
        temperature: Sampling temperature (default 0 for determinism)
        **kwargs: Additional kwargs passed to ChatOpenAI

    Returns:
        Configured ChatOpenAI instance

    Raises:
        ValueError: If OpenAI API key is not configured
    """
    settings = get_settings()

    api_key = settings.openai_api_key.get_secret_value()
    if not api_key:
        msg = "OPENAI_API_KEY not configured. Set it in .env or environment."
        raise ValueError(msg)

    return ChatOpenAI(
        model=model or settings.openai_model,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )


def create_graph[S](state_class: type[S]) -> StateGraph[S]:
    """Create a new StateGraph with the given state class.

    Type-safe factory for creating LangGraph state graphs.

    Args:
        state_class: Pydantic model or TypedDict defining the state schema

    Returns:
        New StateGraph instance ready for node/edge configuration

    Example:
        >>> from pydantic import BaseModel
        >>> class MyState(BaseModel):
        ...     messages: list[str] = []
        >>> graph = create_graph(MyState)
        >>> graph.add_node("process", process_fn)
    """
    return StateGraph(state_class)
