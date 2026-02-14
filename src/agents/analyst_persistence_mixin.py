"""Insight persistence mixin for BaseAnalyst.

Provides persist_findings and related helpers for storing
SpecialistFinding objects as Insights in the database.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.dal import InsightRepository
from src.storage.entities.insight import InsightType

if TYPE_CHECKING:
    from src.graph.state import SpecialistFinding

logger = logging.getLogger(__name__)


class AnalystPersistenceMixin:
    """Mixin providing insight persistence for analyst agents.

    Expects to be mixed into a class that has: NAME, _map_finding_type.
    """

    NAME: str

    async def persist_findings(
        self,
        findings: list[SpecialistFinding],
        session: Any,
    ) -> list[str]:
        """Persist findings as Insights in the database.

        Reads conversation_id and task_label from the active execution
        context (if present) to tag insights with their originating task.

        Args:
            findings: Specialist findings to persist.
            session: Database session.

        Returns:
            List of persisted insight IDs.
        """
        from src.agents.execution_context import get_execution_context

        ctx = get_execution_context()
        conversation_id = ctx.conversation_id if ctx else None
        task_label = ctx.task_label if ctx else None

        repo = InsightRepository(session)
        ids = []

        for finding in findings:
            # Map finding_type to InsightType
            mapped_type = self._map_finding_type(finding.finding_type)

            # Derive impact from confidence
            if finding.confidence >= 0.8:
                impact = "high"
            elif finding.confidence >= 0.5:
                impact = "medium"
            else:
                impact = "low"

            insight = await repo.create(
                title=finding.title,
                description=finding.description,
                type=mapped_type,
                confidence=finding.confidence,
                entities=finding.entities,
                evidence=finding.evidence or {},
                impact=impact,
                conversation_id=conversation_id,
                task_label=task_label,
            )
            ids.append(str(insight.id))

        return ids

    async def _persist_with_fallback(
        self,
        findings: list[SpecialistFinding],
        session: Any | None = None,
    ) -> list[str]:
        """Persist findings using explicit session or execution context fallback.

        Resolution order:
            1. Explicit session (passed as argument)
            2. Session from active execution context's session_factory
            3. Skip persistence (no session available)

        Args:
            findings: Specialist findings to persist.
            session: Optional explicit database session.

        Returns:
            List of persisted insight IDs, or empty list if no session.
        """
        if not findings:
            return []

        # Priority 1: Explicit session
        if session is not None:
            return await self.persist_findings(findings, session)

        # Priority 2: Execution context session factory
        from src.agents.execution_context import get_execution_context

        ctx = get_execution_context()
        if ctx and ctx.session_factory:
            async with ctx.session_factory() as ctx_session:
                return await self.persist_findings(findings, ctx_session)

        # No session available — skip persistence
        logger.debug(
            "%s: skipping insight persistence (no session or execution context)",
            self.NAME,
        )
        return []

    def _map_finding_type(self, finding_type: str) -> InsightType:
        """Map specialist finding_type to InsightType enum."""
        mapping = {
            "insight": InsightType.USAGE_PATTERN,
            "concern": InsightType.ANOMALY_DETECTION,
            "recommendation": InsightType.ENERGY_OPTIMIZATION,
            "data_quality_flag": InsightType.ANOMALY_DETECTION,
        }
        return mapping.get(finding_type, InsightType.USAGE_PATTERN)
