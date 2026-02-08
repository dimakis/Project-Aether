"""Flow grading API routes.

Provides endpoints for submitting and querying user feedback on
conversation steps and overall flow quality.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.dal.flow_grades import FlowGradeRepository
from src.storage import get_session

router = APIRouter(prefix="/flow-grades", tags=["Flow Grades"])


class FlowGradeCreate(BaseModel):
    """Request body for creating/updating a grade."""

    conversation_id: str
    grade: int = Field(..., ge=-1, le=1, description="1 = thumbs up, -1 = thumbs down")
    span_id: str | None = Field(default=None, description="Span ID (null = overall)")
    comment: str | None = Field(default=None, max_length=2000)
    agent_role: str | None = Field(default=None, max_length=50)


class FlowGradeResponse(BaseModel):
    """Response schema for a grade."""

    id: str
    conversation_id: str
    span_id: str | None
    grade: int
    comment: str | None
    agent_role: str | None
    created_at: str


@router.post("", response_model=FlowGradeResponse, status_code=201)
async def submit_grade(body: FlowGradeCreate) -> FlowGradeResponse:
    """Submit or update a grade for a conversation step or overall."""
    if body.grade not in (1, -1):
        raise HTTPException(status_code=400, detail="Grade must be 1 or -1")

    async with get_session() as session:
        repo = FlowGradeRepository(session)
        fg = await repo.upsert(
            conversation_id=body.conversation_id,
            grade=body.grade,
            span_id=body.span_id,
            comment=body.comment,
            agent_role=body.agent_role,
        )
        await session.commit()

        return FlowGradeResponse(
            id=fg.id,
            conversation_id=fg.conversation_id,
            span_id=fg.span_id,
            grade=fg.grade,
            comment=fg.comment,
            agent_role=fg.agent_role,
            created_at=fg.created_at.isoformat() if fg.created_at else "",
        )


@router.get("/{conversation_id}")
async def get_grades(conversation_id: str) -> dict:
    """Get all grades for a conversation with summary."""
    async with get_session() as session:
        repo = FlowGradeRepository(session)
        return await repo.get_summary(conversation_id)


@router.delete("/{grade_id}", status_code=204)
async def delete_grade(grade_id: str) -> None:
    """Delete a grade."""
    async with get_session() as session:
        repo = FlowGradeRepository(session)
        deleted = await repo.delete(grade_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Grade not found")
        await session.commit()
