"""Config review mixin for BaseAnalyst.

Provides analyze_config for the config review workflow (Feature 28).
Specialists review HA YAML configs through their domain lens.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from src.graph.state import AgentRole

logger = logging.getLogger(__name__)


class AnalystConfigMixin:
    """Mixin providing config review logic for analyst agents.

    Expects to be mixed into a class that has: NAME, ROLE, llm.
    """

    NAME: str
    ROLE: str | AgentRole
    llm: BaseChatModel

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

        system_prompt, user_prompt = self._build_config_review_prompt(configs, entity_context)

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
                "%s: failed to parse analyze_config LLM response (JSON decode error)",
                self.NAME,
            )
            findings = []
        except Exception:
            logger.warning("%s: failed to parse analyze_config LLM response", self.NAME)
            findings = []

        return {"findings": findings}

    def _build_config_review_prompt(
        self,
        configs: dict[str, str],
        entity_context: dict[str, Any] | None,
    ) -> tuple[str, str]:
        """Build system and user prompts for config review.

        Args:
            configs: Mapping of entity_id -> YAML config string.
            entity_context: Optional context dict.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
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
            f'  "specialist": "{getattr(self.ROLE, "value", self.ROLE)}",\n'
            f'  "confidence": float 0-1,\n'
            f'  "entities": [list of entity_ids this applies to]\n\n'
            f"Return ONLY the JSON array, no markdown fencing."
        )

        user_prompt = (
            f"Configurations to review:\n```yaml\n{configs_block}\n```\n\n"
            f"Entity context:\n{context_block}"
        )

        return system_prompt, user_prompt
