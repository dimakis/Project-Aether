"""LLM usage tracking API routes.

Provides endpoints for querying LLM usage statistics, costs, and
daily/model breakdowns.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dal.llm_usage import LLMUsageRepository
from src.storage import get_session

router = APIRouter(prefix="/usage", tags=["Usage"])


async def get_db():
    """Dependency to get database session."""
    async with get_session() as session:
        yield session


@router.get("/summary")
async def get_usage_summary(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to summarize"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get LLM usage summary for the specified period.

    Returns total calls, tokens, cost, and per-model breakdown.
    """
    repo = LLMUsageRepository(session)
    return await repo.get_summary(days=days)


@router.get("/daily")
async def get_daily_usage(
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get daily LLM usage breakdown for charting.

    Returns a list of daily entries with calls, tokens, and cost.
    """
    repo = LLMUsageRepository(session)
    daily = await repo.get_daily(days=days)
    return {"days": days, "data": daily}


@router.get("/models")
async def get_usage_by_model(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get per-model LLM usage breakdown.

    Returns calls, tokens, cost, and average latency for each model.
    """
    repo = LLMUsageRepository(session)
    models = await repo.get_by_model(days=days)
    return {"days": days, "models": models}
