"""Discussion round mixin for BaseAnalyst.

Provides discuss() for Feature 33: Advanced Collaboration — B1.
Specialists review combined findings and return cross-references,
agreements, and disagreements.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from src.agents.execution_context import emit_communication
from src.graph.state import CommunicationEntry

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class AnalystDiscussionMixin:
    """Mixin providing discussion round logic for analyst agents.

    Expects to be mixed into a class that has: NAME, llm.
    """

    NAME: str
    llm: BaseChatModel

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

        system_prompt, user_prompt = self._build_discussion_prompt(all_findings_summary)

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = str(response.content).strip()

            # Strip markdown fencing if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]

            parsed = json.loads(content.strip())

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

    def _build_discussion_prompt(self, all_findings_summary: str) -> tuple[str, str]:
        """Build system and user prompts for discussion round.

        Args:
            all_findings_summary: Textual summary of all specialist findings.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
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

        return system_prompt, user_prompt
