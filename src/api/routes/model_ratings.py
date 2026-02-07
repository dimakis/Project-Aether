"""Model ratings API routes.

CRUD endpoints for per-agent model quality ratings.
"""

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.storage import get_session
from src.storage.entities.model_rating import ModelRating

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Model Registry"])


# =============================================================================
# Schemas
# =============================================================================


class ModelRatingCreate(BaseModel):
    """Request body for creating a model rating."""

    model_name: str = Field(max_length=255, description="Model identifier")
    agent_role: str = Field(max_length=50, description="Agent role this rating applies to")
    rating: int = Field(ge=1, le=5, description="1-5 star rating")
    notes: str | None = Field(default=None, max_length=2000, description="Optional notes")
    config_snapshot: dict | None = Field(
        default=None,
        description="Model config at time of rating (temperature, context_window, cost, etc.)",
    )


class ModelRatingResponse(BaseModel):
    """Response for a single model rating."""

    id: str
    model_name: str
    agent_role: str
    rating: int
    notes: str | None
    config_snapshot: dict | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ModelRatingListResponse(BaseModel):
    """Response for list of model ratings."""

    items: list[ModelRatingResponse]
    total: int


class ModelSummaryResponse(BaseModel):
    """Aggregated model summary with average rating."""

    model_name: str
    agent_role: str
    avg_rating: float
    rating_count: int
    latest_config: dict | None


class ModelPerformanceResponse(BaseModel):
    """Auto-collected performance metrics from LLMUsage data."""

    model: str
    agent_role: str | None
    call_count: int
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float | None
    avg_cost_per_call: float | None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/ratings", response_model=ModelRatingListResponse)
async def list_ratings(
    model_name: str | None = None,
    agent_role: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ModelRatingListResponse:
    """List model ratings with optional filtering."""
    async with get_session() as session:
        query = select(ModelRating)

        if model_name:
            query = query.where(ModelRating.model_name == model_name)
        if agent_role:
            query = query.where(ModelRating.agent_role == agent_role)

        query = query.order_by(ModelRating.created_at.desc())

        # Count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total = (await session.execute(count_query)).scalar() or 0

        # Paginate
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        ratings = result.scalars().all()

        return ModelRatingListResponse(
            items=[
                ModelRatingResponse(
                    id=str(r.id),
                    model_name=r.model_name,
                    agent_role=r.agent_role,
                    rating=r.rating,
                    notes=r.notes,
                    config_snapshot=r.config_snapshot,
                    created_at=r.created_at.isoformat() if r.created_at else "",
                    updated_at=r.updated_at.isoformat() if r.updated_at else "",
                )
                for r in ratings
            ],
            total=total,
        )


@router.post("/ratings", response_model=ModelRatingResponse, status_code=201)
async def create_rating(body: ModelRatingCreate) -> ModelRatingResponse:
    """Create a new model rating."""
    async with get_session() as session:
        rating = ModelRating(
            id=str(uuid4()),
            model_name=body.model_name,
            agent_role=body.agent_role,
            rating=body.rating,
            notes=body.notes,
            config_snapshot=body.config_snapshot,
        )
        session.add(rating)
        await session.commit()
        await session.refresh(rating)

        return ModelRatingResponse(
            id=str(rating.id),
            model_name=rating.model_name,
            agent_role=rating.agent_role,
            rating=rating.rating,
            notes=rating.notes,
            config_snapshot=rating.config_snapshot,
            created_at=rating.created_at.isoformat() if rating.created_at else "",
            updated_at=rating.updated_at.isoformat() if rating.updated_at else "",
        )


@router.get("/summary", response_model=list[ModelSummaryResponse])
async def model_summary(
    agent_role: str | None = None,
) -> list[ModelSummaryResponse]:
    """Get aggregated model summaries with average ratings."""
    from sqlalchemy import func

    async with get_session() as session:
        query = (
            select(
                ModelRating.model_name,
                ModelRating.agent_role,
                func.avg(ModelRating.rating).label("avg_rating"),
                func.count(ModelRating.id).label("rating_count"),
            )
            .group_by(ModelRating.model_name, ModelRating.agent_role)
        )

        if agent_role:
            query = query.where(ModelRating.agent_role == agent_role)

        query = query.order_by(func.avg(ModelRating.rating).desc())
        result = await session.execute(query)
        rows = result.all()

        summaries = []
        for row in rows:
            # Get the latest config snapshot for this model+agent combo
            latest = await session.execute(
                select(ModelRating.config_snapshot)
                .where(
                    ModelRating.model_name == row.model_name,
                    ModelRating.agent_role == row.agent_role,
                )
                .order_by(ModelRating.created_at.desc())
                .limit(1)
            )
            latest_config = latest.scalar_one_or_none()

            summaries.append(
                ModelSummaryResponse(
                    model_name=row.model_name,
                    agent_role=row.agent_role,
                    avg_rating=round(float(row.avg_rating), 1),
                    rating_count=row.rating_count,
                    latest_config=latest_config,
                )
            )

        return summaries


@router.get("/performance", response_model=list[ModelPerformanceResponse])
async def model_performance(
    agent_role: str | None = None,
    hours: int = 168,  # Default: 7 days
) -> list[ModelPerformanceResponse]:
    """Get auto-collected performance metrics from LLM usage data.

    Aggregates latency, token counts, and cost from the LLMUsage table.
    No manual ratings required -- metrics come from actual usage.

    Args:
        agent_role: Filter by agent role (e.g. 'architect')
        hours: Time window in hours (default: 168 = 7 days)
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import case, func

    from src.storage.entities.llm_usage import LLMUsage

    async with get_session() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Base query filtered by time
        base = select(LLMUsage).where(LLMUsage.created_at >= cutoff)

        if agent_role:
            base = base.where(LLMUsage.agent_role == agent_role)

        # Aggregate metrics per model + agent_role
        query = (
            select(
                LLMUsage.model,
                LLMUsage.agent_role,
                func.count(LLMUsage.id).label("call_count"),
                func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
                func.percentile_cont(0.95)
                .within_group(LLMUsage.latency_ms)
                .label("p95_latency_ms"),
                func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
                func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
                func.sum(LLMUsage.total_tokens).label("total_tokens"),
                func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
                func.avg(LLMUsage.cost_usd).label("avg_cost_per_call"),
            )
            .where(LLMUsage.created_at >= cutoff)
            .group_by(LLMUsage.model, LLMUsage.agent_role)
            .order_by(func.count(LLMUsage.id).desc())
        )

        if agent_role:
            query = query.where(LLMUsage.agent_role == agent_role)

        result = await session.execute(query)
        rows = result.all()

        return [
            ModelPerformanceResponse(
                model=row.model,
                agent_role=row.agent_role,
                call_count=row.call_count,
                avg_latency_ms=round(float(row.avg_latency_ms), 1) if row.avg_latency_ms else None,
                p95_latency_ms=round(float(row.p95_latency_ms), 1) if row.p95_latency_ms else None,
                total_input_tokens=row.total_input_tokens or 0,
                total_output_tokens=row.total_output_tokens or 0,
                total_tokens=row.total_tokens or 0,
                total_cost_usd=round(float(row.total_cost_usd), 4) if row.total_cost_usd else None,
                avg_cost_per_call=round(float(row.avg_cost_per_call), 4) if row.avg_cost_per_call else None,
            )
            for row in rows
        ]
