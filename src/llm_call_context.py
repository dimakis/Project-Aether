"""LLM call context for passing metadata through the call stack.

Uses Python contextvars to propagate conversation_id, agent_role,
and request_type from the caller to the ResilientLLM wrapper,
which logs usage records after each LLM call.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass
class LLMCallContext:
    """Metadata about the current LLM call."""

    conversation_id: str | None = None
    agent_role: str | None = None
    request_type: str = "chat"


# Context variable holding the current LLM call context
_llm_call_context: ContextVar[LLMCallContext | None] = ContextVar(
    "llm_call_context", default=None
)


def set_llm_call_context(ctx: LLMCallContext) -> Token:
    """Set the LLM call context for the current async task.

    Args:
        ctx: LLM call context with metadata

    Returns:
        Token for resetting the context
    """
    return _llm_call_context.set(ctx)


def get_llm_call_context() -> LLMCallContext | None:
    """Get the current LLM call context.

    Returns:
        Current LLMCallContext or None if not set
    """
    return _llm_call_context.get()


def reset_llm_call_context(token: Token) -> None:
    """Reset the LLM call context to its previous state.

    Args:
        token: Token returned by set_llm_call_context
    """
    _llm_call_context.reset(token)
