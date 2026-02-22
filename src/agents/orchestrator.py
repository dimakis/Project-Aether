"""OrchestratorAgent for intent classification and agent routing.

Feature 30: Domain-Agnostic Orchestration.

The Orchestrator is the default entry point for all user messages when
agent selection is set to "auto". It classifies the user's intent via
a lightweight LLM call and routes to the appropriate domain agent.

When confidence is below threshold, it asks the user for clarification
rather than guessing. Falls back to the Knowledge agent when no domain
agent matches.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base import BaseAgent
from src.graph.state import AgentRole, ConversationState
from src.llm import get_llm

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.6
FALLBACK_AGENT = "knowledge"

_CLASSIFICATION_SYSTEM_PROMPT = """\
You are an intent classifier for a multi-agent AI assistant.

Given the user's message and a list of available agents, determine which agent
should handle the request. Return a JSON object with exactly these fields:

{{"agent": "<agent_name>", "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}}

Rules:
- "confidence" reflects how certain you are that this agent is correct.
- If no agent is a clear match, use agent "knowledge" as the fallback.
- If the request is genuinely ambiguous between two agents, set confidence below 0.5.
- Only return valid JSON, nothing else.

Available agents:
{agents_block}
"""


class OrchestratorAgent(BaseAgent):
    """Routes user messages to the appropriate domain agent.

    Uses an LLM to classify user intent against the registry of
    available agents. The classification is lightweight — a single
    LLM call with a structured JSON response.
    """

    def __init__(self, model_name: str | None = None):
        super().__init__(
            role=AgentRole.ORCHESTRATOR,
            name="Orchestrator",
        )
        self.model_name = model_name
        self._llm: BaseChatModel | None = None

    def _get_classification_llm(self) -> Any:
        """Get or create the LLM used for intent classification."""
        if self._llm is None:
            self._llm = get_llm(model=self.model_name, temperature=0.0)
        return self._llm

    async def classify_intent(
        self,
        user_message: str,
        available_agents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Classify the user's intent and select a target agent.

        Args:
            user_message: The user's latest message.
            available_agents: List of agent metadata dicts with
                name, domain, description, intent_patterns, capabilities.

        Returns:
            Dict with keys: agent, confidence, reasoning, needs_clarification.
        """
        agents_block = "\n".join(
            f"- {a['name']} (domain: {a.get('domain', 'general')}): "
            f"{a.get('description', '')}. "
            f"Patterns: {', '.join(a.get('intent_patterns', []))}."
            for a in available_agents
        )

        system = _CLASSIFICATION_SYSTEM_PROMPT.format(agents_block=agents_block)
        llm = self._get_classification_llm()

        response = await llm.ainvoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=user_message),
            ]
        )

        return self._parse_classification(response.content, available_agents)

    def _parse_classification(
        self,
        raw: str,
        available_agents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Parse the LLM's JSON classification response.

        Handles malformed responses by falling back to the Knowledge agent.
        """
        valid_names = {a["name"] for a in available_agents}

        try:
            data = json.loads(raw)
            agent = data.get("agent", FALLBACK_AGENT)
            confidence = float(data.get("confidence", 0.0))
            reasoning = data.get("reasoning", "")
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("Malformed classification response: %s", raw[:200])
            return {
                "agent": FALLBACK_AGENT,
                "confidence": 0.3,
                "reasoning": "Could not parse classification response",
                "needs_clarification": False,
            }

        if agent not in valid_names:
            agent = FALLBACK_AGENT
            confidence = min(confidence, 0.4)

        needs_clarification = confidence < CONFIDENCE_THRESHOLD

        return {
            "agent": agent,
            "confidence": confidence,
            "reasoning": reasoning,
            "needs_clarification": needs_clarification,
        }

    async def _get_available_agents(self) -> list[dict[str, Any]]:
        """Fetch routable agents from the database.

        Returns agent metadata dicts for classification context.
        Falls back to an empty list if the DB is unavailable.
        """
        try:
            from src.dal.agents import AgentRepository
            from src.storage import get_session_factory

            factory = get_session_factory()
            session = factory()
            try:
                repo = AgentRepository(session)
                agents = await repo.list_all()
                return [
                    {
                        "name": a.name,
                        "domain": a.domain,
                        "description": a.description,
                        "intent_patterns": a.intent_patterns or [],
                        "capabilities": a.capabilities or [],
                    }
                    for a in agents
                    if a.is_routable
                ]
            finally:
                await session.close()
        except Exception:
            logger.warning("Failed to fetch available agents", exc_info=True)
            return []

    async def invoke(
        self,
        state: ConversationState,  # type: ignore[override]
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Classify intent and return routing decision as state updates.

        Args:
            state: Current conversation state.

        Returns:
            State updates: active_agent, current_agent, and user_intent.
        """
        user_message = ""
        if state.messages:
            for msg in reversed(list(state.messages)):
                if hasattr(msg, "content") and type(msg).__name__ in (
                    "HumanMessage",
                    "UserMessage",
                ):
                    user_message = str(msg.content)[:2000]
                    break

        async with self.trace_span("invoke", state) as span:
            available_agents = await self._get_available_agents()
            classification = await self.classify_intent(user_message, available_agents)

            span["outputs"] = classification

            return {
                "active_agent": classification["agent"],
                "current_agent": AgentRole.ORCHESTRATOR,
                "user_intent": classification.get("reasoning", ""),
            }
