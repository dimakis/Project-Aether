"""Dashboard Designer agent for Lovelace dashboard generation.

Conversational agent that designs Home Assistant dashboards by
consulting DS team specialists and generating Lovelace YAML configs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import BaseTool

from langchain_core.messages import SystemMessage

from src.agents.base import BaseAgent
from src.agents.prompts import load_prompt
from src.graph.state import AgentRole, DashboardState
from src.llm import get_llm
from src.tools.dashboard_tools import get_dashboard_tools


class DashboardDesignerAgent(BaseAgent):
    """Dashboard Designer agent for conversational dashboard design.

    Responsibilities:
    - Understand user dashboard requirements through conversation
    - Consult DS team specialists for relevant entity/area data
    - Generate valid Lovelace YAML configurations
    - Present dashboards for preview before deployment
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
    ):
        """Initialize Dashboard Designer agent.

        Args:
            model_name: LLM model to use (defaults to settings)
            temperature: LLM temperature (defaults to settings)
        """
        super().__init__(
            role=AgentRole.DASHBOARD_DESIGNER,
            name="Dashboard Designer",
        )
        self.model_name = model_name
        self.temperature = temperature
        self._llm: BaseChatModel | None = None
        self._tools: list[BaseTool] | None = None

    @property
    def llm(self) -> BaseChatModel:
        """Get LLM instance, creating if needed."""
        if self._llm is None:
            self._llm = get_llm(
                model=self.model_name,
                temperature=self.temperature,
            )
        return self._llm

    @property
    def tools(self) -> list[BaseTool]:
        """Get agent tools."""
        if self._tools is None:
            self._tools = get_dashboard_tools()
        return self._tools

    async def invoke(
        self,
        state: DashboardState,
        **kwargs: object,
    ) -> dict[str, object]:
        """Process a user message and generate a dashboard design response.

        Args:
            state: Current dashboard state with messages and context.

        Returns:
            Dict with 'messages' key containing the agent's response.
        """
        # Load system prompt
        system_prompt = load_prompt("dashboard_designer_system")

        # Build message list: system + conversation history
        messages = [SystemMessage(content=system_prompt), *list(state.messages)]

        # Bind tools and invoke
        llm_with_tools = self.llm.bind_tools(self.tools)
        response = await llm_with_tools.ainvoke(messages)

        return {"messages": [response]}
