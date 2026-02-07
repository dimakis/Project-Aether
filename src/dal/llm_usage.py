"""LLM Usage data access layer.

Provides queries for LLM usage tracking and aggregation.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities.llm_usage import LLMUsage


class LLMUsageRepository:
    """Repository for LLM usage records with aggregation queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost_usd: float | None = None,
        latency_ms: int | None = None,
        conversation_id: str | None = None,
        agent_role: str | None = None,
        request_type: str = "chat",
    ) -> LLMUsage:
        """Record a new LLM usage entry.

        Args:
            provider: LLM provider name
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total token count
            cost_usd: Estimated cost in USD
            latency_ms: Response latency in ms
            conversation_id: Associated conversation UUID
            agent_role: Agent role that made the call
            request_type: Type of request

        Returns:
            Created LLMUsage instance
        """
        usage = LLMUsage(
            id=str(uuid4()),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            conversation_id=conversation_id,
            agent_role=agent_role,
            request_type=request_type,
        )
        self.session.add(usage)
        await self.session.commit()
        return usage

    async def get_summary(
        self,
        days: int = 30,
    ) -> dict:
        """Get usage summary for the specified period.

        Returns:
            Dict with total_calls, total_tokens, total_cost_usd, by_model
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Total aggregates
        result = await self.session.execute(
            select(
                func.count(LLMUsage.id).label("total_calls"),
                func.coalesce(func.sum(LLMUsage.input_tokens), 0).label("total_input_tokens"),
                func.coalesce(func.sum(LLMUsage.output_tokens), 0).label("total_output_tokens"),
                func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(LLMUsage.cost_usd), 0.0).label("total_cost_usd"),
            ).where(LLMUsage.created_at >= since)
        )
        row = result.one()

        # Per-model breakdown
        model_result = await self.session.execute(
            select(
                LLMUsage.model,
                LLMUsage.provider,
                func.count(LLMUsage.id).label("calls"),
                func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("tokens"),
                func.coalesce(func.sum(LLMUsage.cost_usd), 0.0).label("cost_usd"),
            )
            .where(LLMUsage.created_at >= since)
            .group_by(LLMUsage.model, LLMUsage.provider)
            .order_by(func.sum(LLMUsage.cost_usd).desc())
        )

        return {
            "period_days": days,
            "total_calls": row.total_calls,
            "total_input_tokens": row.total_input_tokens,
            "total_output_tokens": row.total_output_tokens,
            "total_tokens": row.total_tokens,
            "total_cost_usd": round(float(row.total_cost_usd), 4),
            "by_model": [
                {
                    "model": r.model,
                    "provider": r.provider,
                    "calls": r.calls,
                    "tokens": r.tokens,
                    "cost_usd": round(float(r.cost_usd), 4),
                }
                for r in model_result
            ],
        }

    async def get_daily(self, days: int = 30) -> list[dict]:
        """Get daily usage breakdown.

        Returns:
            List of dicts with date, calls, tokens, cost_usd
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.session.execute(
            select(
                func.date_trunc("day", LLMUsage.created_at).label("day"),
                func.count(LLMUsage.id).label("calls"),
                func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("tokens"),
                func.coalesce(func.sum(LLMUsage.cost_usd), 0.0).label("cost_usd"),
            )
            .where(LLMUsage.created_at >= since)
            .group_by(text("1"))
            .order_by(text("1"))
        )

        return [
            {
                "date": r.day.isoformat() if r.day else None,
                "calls": r.calls,
                "tokens": r.tokens,
                "cost_usd": round(float(r.cost_usd), 4),
            }
            for r in result
        ]

    async def get_by_model(self, days: int = 30) -> list[dict]:
        """Get per-model usage breakdown.

        Returns:
            List of dicts with model, provider, calls, input_tokens,
            output_tokens, tokens, cost_usd, avg_latency_ms
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.session.execute(
            select(
                LLMUsage.model,
                LLMUsage.provider,
                func.count(LLMUsage.id).label("calls"),
                func.coalesce(func.sum(LLMUsage.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(LLMUsage.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("tokens"),
                func.coalesce(func.sum(LLMUsage.cost_usd), 0.0).label("cost_usd"),
                func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
            )
            .where(LLMUsage.created_at >= since)
            .group_by(LLMUsage.model, LLMUsage.provider)
            .order_by(func.sum(LLMUsage.cost_usd).desc())
        )

        return [
            {
                "model": r.model,
                "provider": r.provider,
                "calls": r.calls,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "tokens": r.tokens,
                "cost_usd": round(float(r.cost_usd), 4),
                "avg_latency_ms": round(float(r.avg_latency_ms), 0) if r.avg_latency_ms else None,
            }
            for r in result
        ]
