"""OrchestratorAgent for intent classification, task planning, and routing.

Feature 30: Domain-Agnostic Orchestration.

The Orchestrator is the default entry point for all user messages when
agent selection is set to "auto".  It:
1. Classifies the user's intent via a lightweight LLM call.
2. Plans the response strategy (direct, clarify, or multi-step).
3. Routes to the appropriate domain agent with the right config.

When confidence is below threshold, it asks the user for clarification
rather than guessing.  Falls back to the Knowledge agent when no domain
agent matches.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base import BaseAgent
from src.graph.state import AgentRole, ConversationState
from src.llm import get_llm

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from src.llm.model_tiers import ModelTier

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

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(content=user_message),
                ]
            )
        except Exception:
            logger.warning("LLM classification call failed", exc_info=True)
            return {
                "agent": FALLBACK_AGENT,
                "confidence": 0.0,
                "reasoning": "Classification unavailable — LLM call failed",
                "needs_clarification": False,
            }

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
        """Classify intent, plan response, and return routing decision.

        Args:
            state: Current conversation state.

        Returns:
            State updates: active_agent, current_agent, user_intent,
            and optionally a task_plan with clarification options.
        """
        user_message = ""
        if state.messages:
            for msg in reversed(list(state.messages)):
                if isinstance(msg, HumanMessage):
                    user_message = str(msg.content)[:2000]
                    break

        async with self.trace_span("invoke", state) as span:
            available_agents = await self._get_available_agents()
            classification = await self.classify_intent(user_message, available_agents)
            plan = await self.plan_response(user_message, classification)

            span["outputs"] = {
                "classification": classification,
                "plan": {
                    "response_type": plan.response_type,
                    "model_tier": plan.model_tier,
                    "target_agent": plan.target_agent,
                },
            }

            result: dict[str, Any] = {
                "active_agent": plan.target_agent,
                "current_agent": AgentRole.ORCHESTRATOR,
                "user_intent": classification.get("reasoning", ""),
            }

            if plan.response_type == "clarify" and plan.clarification_options:
                result["clarification_options"] = plan.clarification_options

            return result

    async def plan_response(
        self,
        user_message: str,
        classification: dict[str, Any],
    ) -> TaskPlan:
        """Plan the response strategy based on the classified intent.

        Evaluates task complexity and decides whether to:
        - Route directly to a single agent (``direct``)
        - Present clarification options (``clarify``)
        - Compose a multi-step workflow (``multi_step``)

        Also selects a model tier appropriate for the task.
        """
        agent = classification.get("agent", FALLBACK_AGENT)
        confidence = classification.get("confidence", 0.0)
        needs_clarification = classification.get("needs_clarification", False)

        if needs_clarification:
            options = await self._generate_clarification_options(user_message)
            return TaskPlan(
                response_type="clarify",
                target_agent=agent,
                model_tier="fast",
                clarification_options=options,
            )

        model_tier = self._assess_model_tier(user_message, agent)

        return TaskPlan(
            response_type="direct",
            target_agent=agent,
            model_tier=model_tier,
            confidence=confidence,
        )

    def _assess_model_tier(self, user_message: str, agent: str) -> ModelTier:
        """Heuristic model tier selection based on task signals."""
        msg_lower = user_message.lower()

        if agent == "knowledge" and len(user_message) < 100:
            return "fast"

        complexity_signals = [
            "analyze",
            "compare",
            "research",
            "optimize",
            "design",
            "explain in detail",
            "step by step",
            "comprehensive",
        ]
        if any(sig in msg_lower for sig in complexity_signals):
            return "frontier"

        return "standard"

    async def _generate_clarification_options(
        self,
        user_message: str,
    ) -> list[ClarificationOption]:
        """Use LLM to generate contextual clarification options."""
        llm = self._get_classification_llm()

        prompt = (
            f'The user said: "{user_message[:500]}"\n\n'
            "This is ambiguous.  Generate 3-5 clarification options the user "
            "can choose from.  Return a JSON array of objects with "
            '"title" (short action label) and "description" (one sentence).\n'
            "Only return valid JSON, nothing else."
        )

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant that generates clarification options."
                    ),
                    HumanMessage(content=prompt),
                ]
            )
            raw = str(response.content or "")
            items = json.loads(raw)
            if isinstance(items, list):
                return [
                    ClarificationOption(
                        title=str(item.get("title", "")),
                        description=str(item.get("description", "")),
                    )
                    for item in items[:5]
                    if item.get("title")
                ]
        except Exception:
            logger.warning("Failed to generate clarification options", exc_info=True)

        return [
            ClarificationOption(
                title="Tell me more",
                description="Provide more details about what you need.",
            ),
            ClarificationOption(
                title="General help",
                description="Get a general answer to your question.",
            ),
        ]


@dataclass
class ClarificationOption:
    """A single option in a clarification prompt."""

    title: str
    description: str = ""


@dataclass
class TaskPlan:
    """The Orchestrator's response plan.

    Attributes:
        response_type: How to handle the request.
        target_agent: Which agent should process the request.
        model_tier: Recommended model capability tier.
        confidence: Classification confidence (0-1).
        clarification_options: Options to present when clarifying.
        workflow_definition: Workflow spec for multi-step tasks.
    """

    response_type: Literal["direct", "clarify", "multi_step"] = "direct"
    target_agent: str = FALLBACK_AGENT
    model_tier: ModelTier = "standard"
    confidence: float = 0.0
    clarification_options: list[ClarificationOption] = field(default_factory=list)
    workflow_definition: dict[str, Any] | None = None
