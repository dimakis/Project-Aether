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

from src.agents import BaseAgent
from src.agents.execution_context import emit_communication
from src.agents.model_context import get_model_context, resolve_model
from src.agents.prompts import load_depth_fragment
from src.dal import InsightRepository
from src.graph.state import (
    AgentRole,
    AnalysisState,
    CommunicationEntry,
    SpecialistFinding,
    TeamAnalysis,
)
from src.ha import HAClient, get_ha_client
from src.llm import get_llm
from src.sandbox.policies import get_policy_for_depth
from src.sandbox.runner import SandboxResult, SandboxRunner
from src.settings import get_settings
from src.storage.entities.insight import InsightType

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

    @property
    def llm(self) -> BaseChatModel:
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
    # Config review (used by review workflow)
    # -----------------------------------------------------------------

    async def analyze_config(
        self,
        configs: dict[str, str],
        entity_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze HA configs through this specialist's lens.

        Uses the LLM to review YAML configurations and produce findings
        from this specialist's domain perspective (energy, behavioral,
        diagnostic). Called by the config review workflow.

        Args:
            configs: Mapping of entity_id -> YAML config string.
            entity_context: Optional context (areas, entities, registry).

        Returns:
            Dict with ``findings`` key containing a list of finding dicts.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # Build a specialist-appropriate prompt
        role_name = self.NAME
        configs_block = "\n---\n".join(f"# {eid}\n{yaml_str}" for eid, yaml_str in configs.items())
        context_block = json.dumps(entity_context or {}, default=str)[:2000]

        system_prompt = (
            f"You are {role_name}, a specialist on the Data Science team.\n"
            f"Analyze the following Home Assistant configuration(s) from your "
            f"domain perspective. Focus on issues, improvements, and best "
            f"practices relevant to your specialty.\n\n"
            f"Return your findings as a JSON array. Each element must have:\n"
            f'  "title": short finding title,\n'
            f'  "description": detailed explanation,\n'
            f'  "specialist": "{self.ROLE.value}",\n'
            f'  "confidence": float 0-1,\n'
            f'  "entities": [list of entity_ids this applies to]\n\n'
            f"Return ONLY the JSON array, no markdown fencing."
        )

        user_prompt = (
            f"Configurations to review:\n```yaml\n{configs_block}\n```\n\n"
            f"Entity context:\n{context_block}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = str(response.content).strip()
            # Strip markdown fencing if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            findings = json.loads(content.strip())
            if not isinstance(findings, list):
                findings = []
        except json.JSONDecodeError:
            logger.warning(
                "%s: failed to parse analyze_config LLM response (JSON decode error)", self.NAME
            )
            findings = []
        except Exception:
            logger.warning("%s: failed to parse analyze_config LLM response", self.NAME)
            findings = []

        return {"findings": findings}

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

    # -----------------------------------------------------------------
    # Shared: Insight persistence
    # -----------------------------------------------------------------

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

    # -----------------------------------------------------------------
    # Discussion round (Feature 33: Advanced Collaboration — B1)
    # -----------------------------------------------------------------

    async def discuss(
        self,
        all_findings_summary: str,
    ) -> list[CommunicationEntry]:
        """Participate in a discussion round after all specialists have run.

        Receives a summary of *all* specialists' findings and returns
        cross-references, agreements, and disagreements as a list of
        ``CommunicationEntry`` objects.  Capped at one round to bound cost.

        Args:
            all_findings_summary: Textual summary of all specialist findings.

        Returns:
            List of discussion CommunicationEntry objects (may be empty on
            error or if the LLM produces unparseable output).
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = (
            f"You are {self.NAME}, a specialist on the Data Science team.\n"
            "You have already completed your analysis.  Now review the combined "
            "findings from ALL specialists and provide your discussion input.\n\n"
            "Return a JSON object with:\n"
            '  "cross_references": [list of cross-domain observations],\n'
            '  "agreements": [findings you agree with],\n'
            '  "disagreements": [findings you disagree with + reasoning]\n\n'
            "Return ONLY the JSON object, no markdown fencing."
        )

        user_prompt = (
            f"Combined findings from all specialists:\n\n{all_findings_summary}\n\n"
            "Provide your cross-references, agreements, and disagreements."
        )

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = str(response.content).strip()

            # Parse JSON response
            import json as _json

            # Strip markdown fencing if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]

            parsed = _json.loads(content.strip())

            entries: list[CommunicationEntry] = []

            for xref in parsed.get("cross_references", []):
                entries.append(
                    CommunicationEntry(
                        from_agent=self.NAME,
                        to_agent="team",
                        message_type="discussion",
                        content=f"Cross-reference: {xref}",
                        metadata={"sub_type": "cross_reference"},
                    )
                )
            for agreement in parsed.get("agreements", []):
                entries.append(
                    CommunicationEntry(
                        from_agent=self.NAME,
                        to_agent="team",
                        message_type="discussion",
                        content=f"Agreement: {agreement}",
                        metadata={"sub_type": "agreement"},
                    )
                )
            for disagreement in parsed.get("disagreements", []):
                entries.append(
                    CommunicationEntry(
                        from_agent=self.NAME,
                        to_agent="team",
                        message_type="discussion",
                        content=f"Disagreement: {disagreement}",
                        metadata={"sub_type": "disagreement"},
                    )
                )

            # Log each entry to execution context communication log
            for entry in entries:
                emit_communication(
                    from_agent=entry.from_agent,
                    to_agent=entry.to_agent,
                    message_type=entry.message_type,
                    content=entry.content,
                    metadata=entry.metadata,
                )

            return entries

        except Exception:
            logger.warning(
                "%s: discussion round failed",
                self.NAME,
                exc_info=True,
            )
            return []
