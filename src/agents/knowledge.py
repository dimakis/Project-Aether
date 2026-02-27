"""KnowledgeAgent for general-purpose question answering.

Feature 30: Domain-Agnostic Orchestration.

The simplest routable domain agent -- pure LLM, no tools.  Handles
general knowledge questions that don't require Home Assistant access
or external tool calls.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base import BaseAgent
from src.agents.prompts import load_prompt_for_agent
from src.graph.state import AgentRole, ConversationState
from src.llm import get_llm

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a knowledgeable AI assistant.  Answer the user's question "
    "clearly and concisely.  If you don't know the answer, say so rather "
    "than guessing."
)


class KnowledgeAgent(BaseAgent):
    """General-purpose knowledge agent (no tools, pure LLM)."""

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
    ):
        super().__init__(role=AgentRole.KNOWLEDGE, name="Knowledge")
        self.model_name = model_name
        self.temperature = temperature

    async def invoke(
        self,
        state: ConversationState,  # type: ignore[override]
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Answer a general knowledge question."""
        async with self.trace_span("invoke", state) as span:
            try:
                system_prompt = load_prompt_for_agent(
                    "knowledge",
                    db_prompt=getattr(self, "_runtime_prompt", None),
                )
            except FileNotFoundError:
                system_prompt = _DEFAULT_SYSTEM_PROMPT

            llm = get_llm(model=self.model_name, temperature=self.temperature)
            response = await llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    *[m for m in state.messages if isinstance(m, (HumanMessage, AIMessage))],
                ]
            )

            response_text = str(response.content or "")
            span["outputs"] = {"response": response_text[:2000]}

            return {
                "messages": [AIMessage(content=response_text)],
                "current_agent": AgentRole.KNOWLEDGE,
            }
