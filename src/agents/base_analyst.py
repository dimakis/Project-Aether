"""Base analyst for DS team specialists.

Provides shared functionality for all analyst agents:
- HA client access (lazy singleton)
- LLM access with model context resolution
- Sandbox script execution (Constitution: Isolation)
- Insight persistence
- Cross-consultation (reading prior findings from TeamAnalysis)
- Finding management (add findings to TeamAnalysis)

Subclasses must implement:
- collect_data(state) -> dict
- generate_script(state, data) -> str
- extract_findings(result, state) -> list[SpecialistFinding]
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from src.agents import BaseAgent
from src.agents.model_context import get_model_context, resolve_model
from src.dal import InsightRepository
from src.graph.state import (
    AgentRole,
    AnalysisState,
    SpecialistFinding,
    TeamAnalysis,
)
from src.ha import HAClient, get_ha_client
from src.llm import get_llm
from src.sandbox.runner import SandboxResult, SandboxRunner
from src.settings import get_settings
from src.storage.entities.insight import InsightStatus, InsightType

logger = logging.getLogger(__name__)


class BaseAnalyst(BaseAgent, ABC):
    """Abstract base for DS team specialist agents.

    Provides shared infrastructure so specialists only need to implement
    their domain-specific logic: data collection, script generation,
    and finding extraction.
    """

    # Subclasses must set these
    ROLE: AgentRole
    NAME: str

    def __init__(self, ha_client: HAClient | None = None):
        """Initialize analyst with shared infrastructure.

        Args:
            ha_client: Optional HA client (lazy-created if not provided).
        """
        super().__init__(
            role=self.ROLE,
            name=self.NAME,
        )
        self._ha_client = ha_client
        self._llm = None
        self._sandbox = SandboxRunner()

    @property
    def ha(self) -> HAClient:
        """Get HA client, creating if needed."""
        if self._ha_client is None:
            self._ha_client = get_ha_client()
        return self._ha_client

    @property
    def llm(self):
        """Get LLM using model context resolution chain.

        Resolution order:
            1. Active model context (user's UI selection)
            2. Per-agent settings from .env
            3. Global default
        """
        settings = get_settings()
        # Use DATA_SCIENTIST_MODEL as fallback for all analysts
        model_name, temperature = resolve_model(
            agent_model=settings.data_scientist_model,
            agent_temperature=settings.data_scientist_temperature,
        )

        if get_model_context() is not None:
            return get_llm(model=model_name, temperature=temperature)

        if self._llm is None:
            self._llm = get_llm(model=model_name, temperature=temperature)
        return self._llm

    # -----------------------------------------------------------------
    # Abstract methods (subclass responsibility)
    # -----------------------------------------------------------------

    @abstractmethod
    async def collect_data(self, state: AnalysisState) -> dict[str, Any]:
        """Collect domain-specific data for analysis.

        Args:
            state: Current analysis state.

        Returns:
            Dict of collected data for script generation.
        """
        ...

    @abstractmethod
    async def generate_script(self, state: AnalysisState, data: dict[str, Any]) -> str:
        """Generate an analysis script for the sandbox.

        Args:
            state: Current analysis state.
            data: Collected data from collect_data().

        Returns:
            Python script as a string.
        """
        ...

    @abstractmethod
    def extract_findings(
        self, result: SandboxResult, state: AnalysisState
    ) -> list[SpecialistFinding]:
        """Extract SpecialistFinding objects from sandbox output.

        Args:
            result: Sandbox execution result.
            state: Current analysis state.

        Returns:
            List of findings.
        """
        ...

    # -----------------------------------------------------------------
    # Shared: Script execution (Constitution: Isolation)
    # -----------------------------------------------------------------

    async def execute_script(
        self,
        script: str,
        data: dict[str, Any],
    ) -> SandboxResult:
        """Execute an analysis script in the gVisor sandbox.

        Injects data as a JSON preamble so the script can access it.

        Args:
            script: Python script to execute.
            data: Data dict to inject as context.

        Returns:
            SandboxResult with stdout, stderr, exit_code.
        """
        # Inject data as a JSON variable at the top of the script
        data_json = json.dumps(data, default=str)
        injected_script = (
            f"import json\n"
            f"data = json.loads('''{data_json}''')\n\n"
            f"{script}"
        )
        return await self._sandbox.run(injected_script)

    # -----------------------------------------------------------------
    # Shared: Cross-consultation
    # -----------------------------------------------------------------

    def get_prior_findings(
        self,
        state: AnalysisState,
        entity_id: str | None = None,
    ) -> list[SpecialistFinding]:
        """Get findings from other specialists.

        Filters out own findings so a specialist doesn't see its own prior output.

        Args:
            state: Current analysis state (may contain team_analysis).
            entity_id: Optional entity to filter by.

        Returns:
            List of findings from other specialists.
        """
        if state.team_analysis is None:
            return []

        own_specialist = self.ROLE.value
        findings = [
            f for f in state.team_analysis.findings
            if f.specialist != own_specialist
        ]

        if entity_id:
            findings = [f for f in findings if entity_id in f.entities]

        return findings

    # -----------------------------------------------------------------
    # Shared: Finding management
    # -----------------------------------------------------------------

    def add_finding(
        self,
        state: AnalysisState,
        finding: SpecialistFinding,
    ) -> AnalysisState:
        """Add a finding to the TeamAnalysis in state.

        Creates TeamAnalysis if it doesn't exist yet.

        Args:
            state: Current analysis state.
            finding: The finding to add.

        Returns:
            Updated AnalysisState (new copy).
        """
        if state.team_analysis is None:
            ta = TeamAnalysis(
                request_id=str(uuid4()),
                request_summary=state.custom_query or f"Analysis: {state.analysis_type.value}",
                findings=[finding],
            )
        else:
            ta = state.team_analysis.model_copy(
                update={"findings": [*state.team_analysis.findings, finding]}
            )

        # Return updated state
        state.team_analysis = ta
        return state

    # -----------------------------------------------------------------
    # Shared: Insight persistence
    # -----------------------------------------------------------------

    async def persist_findings(
        self,
        findings: list[SpecialistFinding],
        session: Any,
    ) -> list[str]:
        """Persist findings as Insights in the database.

        Args:
            findings: Specialist findings to persist.
            session: Database session.

        Returns:
            List of persisted insight IDs.
        """
        repo = InsightRepository(session)
        ids = []

        for finding in findings:
            # Map finding_type to InsightType
            insight_type = self._map_finding_type(finding.finding_type)

            insight = await repo.create(
                title=finding.title,
                description=finding.description,
                insight_type=insight_type,
                confidence=finding.confidence,
                entity_ids=finding.entities,
                data=finding.evidence,
                status=InsightStatus.PENDING,
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
