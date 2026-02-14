"""Core Architect agent for conversational automation design.

The Architect helps users design Home Assistant automations through
natural language conversation, translating their desires into
structured automation proposals.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage
    from langchain_core.tools import BaseTool
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.graph.state import AutomationSuggestion
    from src.storage.entities import AutomationProposal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agents.architect.entity_context import get_entity_context
from src.agents.architect.proposals import (
    create_proposal,
    extract_proposal,
    extract_proposals,
    proposal_to_yaml,
)
from src.agents.architect.review import (
    receive_suggestion as _receive_suggestion,
)
from src.agents.architect.review import (
    refine_proposal as _refine_proposal,
)
from src.agents.architect.review import (
    synthesize_review as _synthesize_review,
)
from src.agents.architect.tools import READ_ONLY_TOOLS, get_ha_tools, is_mutating_tool
from src.agents.base import BaseAgent
from src.agents.prompts import load_prompt
from src.graph.state import AgentRole, ConversationState, ConversationStatus, HITLApproval
from src.llm import get_llm

logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """The Architect agent for conversational automation design.

    Responsibilities:
    - Understand user automation desires through conversation
    - Query available entities for context
    - Design automations using HA's trigger/condition/action model
    - Create proposals for HITL approval (Constitution: Safety First)
    - Refine designs based on user feedback
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
    ):
        """Initialize Architect agent.

        Args:
            model_name: LLM model to use (defaults to settings)
            temperature: LLM temperature for response generation (defaults to settings)
        """
        super().__init__(
            role=AgentRole.ARCHITECT,
            name="Architect",
        )
        self.model_name = model_name
        self.temperature = temperature
        self._llm: BaseChatModel | None = None

    @property
    def llm(self) -> BaseChatModel:
        """Get LLM instance, creating if needed."""
        if self._llm is None:
            self._llm = get_llm(
                model=self.model_name,
                temperature=self.temperature,
            )
        return self._llm

    async def invoke(  # type: ignore[override]
        self,
        state: ConversationState,
        **kwargs: object,
    ) -> dict[str, object]:
        """Process a user message and generate a response.

        Args:
            state: Current conversation state
            **kwargs: Additional arguments (session for DB access)

        Returns:
            State updates with response and any proposals
        """
        # Get the latest user message for trace inputs
        user_message = ""
        if state.messages:
            for msg in reversed(list(state.messages)):
                if hasattr(msg, "content") and type(msg).__name__ in (
                    "HumanMessage",
                    "UserMessage",
                ):
                    user_message = str(msg.content)[:1000]
                    break

        trace_inputs = {
            "user_message": user_message,
            "conversation_id": state.conversation_id,
            "message_count": len(state.messages),
        }

        async with self.trace_span("invoke", state, inputs=trace_inputs) as span:
            session = kwargs.get("session")

            messages = self._build_messages(state)

            if session:
                entity_context = await self._get_entity_context(
                    cast("AsyncSession", session), state
                )
                if entity_context:
                    messages.insert(1, SystemMessage(content=entity_context))

            tools = self._get_ha_tools()
            tool_llm = self.llm.bind_tools(tools) if tools else self.llm
            response = await tool_llm.ainvoke(messages)

            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_call_updates = await self._handle_tool_calls(
                    response,
                    messages,
                    tools,
                    state,
                )
                if tool_call_updates is not None:
                    tool_call_names = [tc.get("name", "") for tc in response.tool_calls]
                    final_response = ""
                    msgs = tool_call_updates.get("messages")
                    if msgs:
                        for msg in reversed(list(msgs)):  # type: ignore[call-overload]
                            if hasattr(msg, "content") and type(msg).__name__ == "AIMessage":
                                final_response = str(getattr(msg, "content", ""))[:2000]
                                break
                    span["outputs"] = {
                        "response": final_response,
                        "tool_calls": tool_call_names,
                        "has_tool_calls": True,
                        "requires_approval": "pending_approvals" in tool_call_updates,
                    }
                    return tool_call_updates

            response_text = str(response.content or "")

            tool_calls_data = None
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls_data = [
                    {"name": tc.get("name", ""), "args": tc.get("args", {})}
                    for tc in response.tool_calls
                ]

            self.log_conversation(
                conversation_id=state.conversation_id,
                messages=state.messages,
                response=response_text,
                tool_calls=tool_calls_data,
            )

            span["response_length"] = len(response_text)
            span["outputs"] = {
                "response": response_text[:2000],
                "has_tool_calls": bool(tool_calls_data),
            }

            proposal_data = self._extract_proposal(response_text)
            updates: dict[str, object] = {
                "messages": [AIMessage(content=response_text)],
            }

            if proposal_data and session:
                proposal = await self._create_proposal(
                    cast("AsyncSession", session),
                    state.conversation_id,
                    proposal_data,
                )
                updates["pending_approvals"] = [
                    HITLApproval(
                        id=proposal.id,
                        request_type="automation",
                        description=proposal.description or proposal.name,
                        yaml_content=self._proposal_to_yaml(proposal_data),
                    )
                ]
                updates["status"] = ConversationStatus.WAITING_APPROVAL
                updates["architect_design"] = proposal_data

                span["proposal_created"] = proposal.id
                span["outputs"]["proposal_name"] = proposal.name

            return updates

    # ------------------------------------------------------------------
    # Delegating methods (thin wrappers for backwards compatibility)
    # ------------------------------------------------------------------

    def _build_messages(self, state: ConversationState) -> list[BaseMessage]:
        """Build message list for LLM from state."""
        messages: list[BaseMessage] = [SystemMessage(content=load_prompt("architect_system"))]
        for msg in state.messages:
            if isinstance(msg, (HumanMessage, AIMessage, ToolMessage)):
                messages.append(msg)
        return messages

    def _serialize_messages(
        self,
        messages: list[BaseMessage],
        max_messages: int = 20,
        max_chars: int = 500,
    ) -> list[dict[str, str]]:
        """Serialize messages for MLflow logging."""
        serialized: list[dict[str, str]] = []
        for msg in messages[-max_messages:]:
            role = getattr(msg, "type", msg.__class__.__name__)
            content = getattr(msg, "content", "")
            serialized.append({"role": str(role), "content": str(content)[:max_chars]})
        return serialized

    def _get_ha_tools(self) -> list[BaseTool]:
        """Get the curated Architect tool set."""
        return get_ha_tools()

    _READ_ONLY_TOOLS = READ_ONLY_TOOLS

    def _is_mutating_tool(self, tool_name: str) -> bool:
        """Check if a tool call can mutate Home Assistant state."""
        return is_mutating_tool(tool_name)

    async def _handle_tool_calls(
        self,
        response: AIMessage,
        messages: list[BaseMessage],
        tools: list[BaseTool],
        state: ConversationState,
    ) -> dict[str, object] | None:
        """Handle tool calls from the LLM."""
        tool_lookup = {tool.name: tool for tool in tools}
        tool_calls = response.tool_calls or []

        mutating_calls = [call for call in tool_calls if is_mutating_tool(call["name"])]
        if mutating_calls:
            description_lines = []
            for call in mutating_calls:
                description_lines.append(f"- {call['name']}({call.get('args', {})})")

            approval_text = (
                "I can perform the following Home Assistant action(s), but need your approval:\n"
                + "\n".join(description_lines)
                + "\n\nPlease reply 'approve' to proceed or 'reject' to cancel."
            )

            return {
                "messages": [AIMessage(content=approval_text)],
                "pending_approvals": [
                    HITLApproval(
                        request_type="tool_action",
                        description=approval_text,
                        yaml_content=str(mutating_calls),
                    )
                ],
                "status": ConversationStatus.WAITING_APPROVAL,
            }

        async def _invoke_tool(call: dict[str, object]) -> ToolMessage | None:
            tool_name = str(call.get("name", ""))
            tool = tool_lookup.get(tool_name)
            if not tool:
                return None
            result = await tool.ainvoke(cast("dict[str, Any]", call.get("args", {})))
            return ToolMessage(
                content=str(result),
                tool_call_id=str(call.get("id", "")),
            )

        raw_results = await asyncio.gather(
            *(_invoke_tool(call) for call in tool_calls)  # type: ignore[arg-type]
        )
        tool_messages: list[ToolMessage] = [m for m in raw_results if m is not None]

        follow_up = await self.llm.ainvoke([*messages, response, *tool_messages])

        return {
            "messages": [
                response,
                *tool_messages,
                AIMessage(content=str(follow_up.content or "")),
            ],
        }

    async def _get_entity_context(
        self,
        session: AsyncSession,
        state: ConversationState,
    ) -> str | None:
        """Get relevant entity context for the conversation."""
        return await get_entity_context(session, state)

    def _extract_proposal(self, response: str) -> dict[str, Any] | None:
        """Extract the first proposal JSON from response if present."""
        return extract_proposal(response)

    def _extract_proposals(self, response: str) -> list[dict[str, Any]]:
        """Extract all proposal JSON blocks from response."""
        return extract_proposals(response)

    async def _create_proposal(
        self,
        session: AsyncSession,
        conversation_id: str,
        proposal_data: dict[str, Any],
    ) -> AutomationProposal:
        """Create an automation proposal from parsed data."""
        return await create_proposal(session, conversation_id, proposal_data)

    def _proposal_to_yaml(self, proposal_data: dict[str, Any]) -> str:
        """Convert proposal to YAML string for display."""
        return proposal_to_yaml(proposal_data)

    # ------------------------------------------------------------------
    # Config review methods (delegated to review module)
    # ------------------------------------------------------------------

    async def synthesize_review(
        self,
        configs: dict[str, str],
        ds_findings: list[dict[str, Any]],
        entity_context: dict[str, Any] | None = None,
        focus: str | None = None,
    ) -> list[dict[str, Any]]:
        """Synthesize DS team findings into concrete YAML improvement suggestions."""
        return await _synthesize_review(
            self.llm,
            configs,
            ds_findings,
            entity_context,
            focus,
        )

    async def refine_proposal(
        self,
        state: ConversationState,
        feedback: str,
        proposal_id: str,
        session: AsyncSession,
    ) -> dict[str, object]:
        """Refine a proposal based on user feedback."""
        return await _refine_proposal(
            self.llm,
            self._build_messages,
            state,
            feedback,
            proposal_id,
            session,
        )

    async def receive_suggestion(
        self,
        suggestion: AutomationSuggestion,
        session: AsyncSession,
    ) -> dict[str, object]:
        """Receive an AutomationSuggestion from the DS Team and create a proposal."""
        return await _receive_suggestion(
            self.llm,
            self.trace_span,
            suggestion,
            session,
        )
