"""Flow grading data access layer.

Provides CRUD and aggregation for flow grades (user feedback on
conversation steps and overall quality).
"""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities.flow_grade import FlowGrade


class FlowGradeRepository:
    """Repository for flow grade CRUD and queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        conversation_id: str,
        grade: int,
        span_id: str | None = None,
        comment: str | None = None,
        agent_role: str | None = None,
    ) -> FlowGrade:
        """Create or update a grade for a conversation/span pair.

        If a grade already exists for the same conversation+span, updates it.
        """
        existing = await self.session.execute(
            select(FlowGrade).where(
                FlowGrade.conversation_id == conversation_id,
                FlowGrade.span_id == span_id if span_id else FlowGrade.span_id.is_(None),
            )
        )
        fg = existing.scalar_one_or_none()

        if fg:
            fg.grade = grade
            fg.comment = comment
            fg.agent_role = agent_role
        else:
            fg = FlowGrade(
                id=str(uuid4()),
                conversation_id=conversation_id,
                span_id=span_id,
                grade=grade,
                comment=comment,
                agent_role=agent_role,
            )
            self.session.add(fg)

        await self.session.flush()
        return fg

    async def list_for_conversation(self, conversation_id: str) -> list[FlowGrade]:
        """List all grades for a conversation."""
        result = await self.session.execute(
            select(FlowGrade)
            .where(FlowGrade.conversation_id == conversation_id)
            .order_by(FlowGrade.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_summary(self, conversation_id: str) -> dict:
        """Get grade summary for a conversation.

        Returns overall grade, per-step grades, and aggregate stats.
        """
        grades = await self.list_for_conversation(conversation_id)

        overall = None
        steps = []
        for g in grades:
            entry = {
                "id": g.id,
                "span_id": g.span_id,
                "grade": g.grade,
                "comment": g.comment,
                "agent_role": g.agent_role,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            if g.span_id is None:
                overall = entry
            else:
                steps.append(entry)

        thumbs_up = sum(1 for g in grades if g.grade > 0)
        thumbs_down = sum(1 for g in grades if g.grade < 0)

        return {
            "conversation_id": conversation_id,
            "overall": overall,
            "steps": steps,
            "total_grades": len(grades),
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
        }

    async def delete(self, grade_id: str) -> bool:
        """Delete a grade by ID."""
        result = await self.session.execute(select(FlowGrade).where(FlowGrade.id == grade_id))
        fg = result.scalar_one_or_none()
        if fg:
            await self.session.delete(fg)
            await self.session.flush()
            return True
        return False
