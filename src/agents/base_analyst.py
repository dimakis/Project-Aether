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
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

from src.agents.analyst_config_mixin import AnalystConfigMixin
from src.agents.analyst_discussion_mixin import AnalystDiscussionMixin
from src.agents.analyst_persistence_mixin import AnalystPersistenceMixin
from src.agents.base import BaseAgent
from src.agents.execution_context import emit_communication
from src.agents.model_context import get_model_context, resolve_model
from src.agents.prompts import load_depth_fragment
from src.graph.state import (
    AgentRole,
    AnalysisState,
    SpecialistFinding,
    TeamAnalysis,
)
from src.ha import HAClient, get_ha_client
from src.llm import get_llm
from src.sandbox.policies import get_policy_for_depth
from src.sandbox.runner import SandboxResult, SandboxRunner
from src.settings import get_settings

logger = logging.getLogger(__name__)


class BaseAnalyst(
    AnalystConfigMixin,
    AnalystPersistenceMixin,
    AnalystDiscussionMixin,
    BaseAgent,
    ABC,
):
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
        self._llm: BaseChatModel | None = None
        self._sandbox = SandboxRunner()

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _append_depth_fragment(prompt: str, depth: str) -> str:
        """Append the depth-specific EDA prompt fragment to *prompt*.

        Feature 33: DS Deep Analysis — depth-aware prompt composition.

        Args:
            prompt: The base prompt text.
            depth: One of ``"quick"``, ``"standard"``, ``"deep"``.

        Returns:
            The prompt with the depth fragment appended (or unchanged if no
            fragment is found for *depth*).
        """
        fragment = load_depth_fragment(depth)
        if fragment:
            return prompt + "\n\n" + fragment
        return prompt

    @property
    def ha(self) -> HAClient:
        """Get HA client, creating if needed."""
        if self._ha_client is None:
            self._ha_client = get_ha_client()
        return self._ha_client

    @ha.setter
    def ha(self, value: HAClient) -> None:
        """Set HA client (for testing or injection)."""
        self._ha_client = value

    @property
    def llm(self) -> BaseChatModel:  # type: ignore[override]  # writeable in parent
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
        depth: str = "standard",
    ) -> SandboxResult:
        """Execute an analysis script in the gVisor sandbox.

        Injects data as a JSON preamble so the script can access it.
        Uses ``get_policy_for_depth()`` to build a depth-appropriate policy.
        Logs ``status`` communications at start and completion.

        Args:
            script: Python script to execute.
            data: Data dict to inject as context.
            depth: Analysis depth (``"quick"``, ``"standard"``, ``"deep"``).
                Controls sandbox timeout, memory, and artifact policy.

        Returns:
            SandboxResult with stdout, stderr, exit_code.
        """
        emit_communication(
            from_agent=self.NAME,
            to_agent="team",
            message_type="status",
            content=f"Executing analysis script in sandbox ({len(script)} chars, depth={depth})",
        )

        # Build depth-aware sandbox policy
        settings = get_settings()
        policy = get_policy_for_depth(depth, settings)

        # Inject data as a JSON variable at the top of the script
        data_json = json.dumps(data, default=str)
        injected_script = f"import json\ndata = json.loads('''{data_json}''')\n\n{script}"
        result = await self._sandbox.run(injected_script, policy=policy)

        status = "completed" if result.exit_code == 0 else "failed"
        emit_communication(
            from_agent=self.NAME,
            to_agent="team",
            message_type="status",
            content=f"Script execution {status} (exit_code={result.exit_code})",
            metadata={"exit_code": result.exit_code},
        )

        return result

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
        Logs a ``cross_reference`` communication when prior findings are found.

        Args:
            state: Current analysis state (may contain team_analysis).
            entity_id: Optional entity to filter by.

        Returns:
            List of findings from other specialists.
        """
        if state.team_analysis is None:
            return []

        own_specialist = self.ROLE.value
        findings = [f for f in state.team_analysis.findings if f.specialist != own_specialist]

        if entity_id:
            findings = [f for f in findings if entity_id in f.entities]

        if findings:
            sources = {f.specialist for f in findings}
            emit_communication(
                from_agent=self.NAME,
                to_agent="team",
                message_type="cross_reference",
                content=(
                    f"Reviewing {len(findings)} prior finding(s) from {', '.join(sorted(sources))}"
                ),
                metadata={"finding_count": len(findings), "sources": sorted(sources)},
            )

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
        Logs a ``finding`` communication to the execution context.

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

        # Log the finding to the communication log
        emit_communication(
            from_agent=self.NAME,
            to_agent="team",
            message_type="finding",
            content=f"[{finding.finding_type}] {finding.title}: {finding.description}",
            metadata={
                "finding_id": finding.id,
                "confidence": finding.confidence,
                "entities": finding.entities,
            },
        )

        # Return updated state
        state.team_analysis = ta
        return state
