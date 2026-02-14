"""LLM usage logging and activity publishing."""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _publish_llm_activity(event: str, model: str, **extra: Any) -> None:
    """Broadcast an LLM activity event to the global SSE bus."""
    try:
        from src.llm_call_context import get_llm_call_context

        ctx = get_llm_call_context()
        from src.api.routes.activity_stream import publish_activity

        publish_activity(
            {
                "type": "llm",
                "event": event,
                "model": model,
                "agent_role": ctx.agent_role if ctx else None,
                **extra,
            }
        )
    except Exception:
        logger.debug(
            "Failed to publish LLM activity event", exc_info=True
        )  # Non-critical: never block on activity broadcast


def _log_usage_async(result: Any, provider: str, model: str, latency_ms: int) -> None:
    """Log LLM token usage asynchronously (fire-and-forget).

    Extracts token counts from the LLM response and writes a usage record
    to the database via the LLMUsageRepository. Non-blocking: errors are
    logged but do not propagate.
    """
    try:
        # Extract token usage from LangChain response metadata
        usage_meta = getattr(result, "usage_metadata", None)
        if usage_meta is None:
            # Try response_metadata for older LangChain versions
            resp_meta = getattr(result, "response_metadata", {})
            usage_meta = resp_meta.get("token_usage") or resp_meta.get("usage")

        if usage_meta is None:
            return  # No usage data available

        # Normalize field names
        if isinstance(usage_meta, dict):
            input_tokens = usage_meta.get("input_tokens") or usage_meta.get("prompt_tokens", 0)
            output_tokens = usage_meta.get("output_tokens") or usage_meta.get(
                "completion_tokens", 0
            )
            total_tokens = usage_meta.get("total_tokens", input_tokens + output_tokens)
        else:
            input_tokens = getattr(usage_meta, "input_tokens", 0) or getattr(
                usage_meta, "prompt_tokens", 0
            )
            output_tokens = getattr(usage_meta, "output_tokens", 0) or getattr(
                usage_meta, "completion_tokens", 0
            )
            total_tokens = getattr(usage_meta, "total_tokens", input_tokens + output_tokens)

        if total_tokens == 0:
            return

        # Calculate cost
        from src.llm_pricing import calculate_cost

        cost_usd = calculate_cost(model, input_tokens, output_tokens)

        # Get call context (conversation_id, agent_role, etc.)
        from src.llm_call_context import get_llm_call_context

        ctx = get_llm_call_context()

        # Fire-and-forget: write to DB
        # Intentionally not storing task reference - this is fire-and-forget logging
        asyncio.ensure_future(  # noqa: RUF006
            _write_usage_record(
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                conversation_id=ctx.conversation_id if ctx else None,
                agent_role=ctx.agent_role if ctx else None,
                request_type=ctx.request_type if ctx else "chat",
            )
        )
    except Exception as e:
        logger.debug(f"Failed to log LLM usage: {e}")


async def _write_usage_record(**kwargs: Any) -> None:
    """Write a usage record to the database. Silently fails."""
    try:
        from src.dal.llm_usage import LLMUsageRepository
        from src.storage import get_session

        async with get_session() as session:
            repo = LLMUsageRepository(session)
            await repo.record(**kwargs)
    except Exception as e:
        logger.debug(f"Failed to write usage record: {e}")
