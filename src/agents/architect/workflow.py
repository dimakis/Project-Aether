"""Workflow orchestration for the Architect agent.

Contains ``ArchitectWorkflow`` with ``start_conversation``,
``continue_conversation``, and ``stream_conversation``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from src.agents.architect.stream_event import StreamEvent
from src.graph.state import AgentRole, ConversationState

logger = logging.getLogger(__name__)


class ArchitectWorkflow:
    """Workflow implementation for the Architect agent.

    Orchestrates the conversation flow:
    1. Receive user message
    2. Process with Architect agent
    3. Handle approvals/rejections
    4. Hand off to Developer for deployment
    """

    def __init__(self, model_name: str | None = None, temperature: float | None = None):
        """Initialize the Architect workflow.

        Args:
            model_name: LLM model to use (e.g., 'gpt-4o', 'gpt-4o-mini')
            temperature: LLM temperature for response generation
        """
        from src.agents.architect.agent import ArchitectAgent

        self.agent = ArchitectAgent(model_name=model_name, temperature=temperature)

    async def start_conversation(
        self,
        user_message: str,
        user_id: str = "default_user",
        session: AsyncSession | None = None,
    ) -> ConversationState:
        """Start a new conversation.

        Args:
            user_message: Initial user message
            user_id: User identifier
            session: Database session

        Returns:
            Initial conversation state
        """
        import mlflow

        state = ConversationState(
            current_agent=AgentRole.ARCHITECT,
            messages=[HumanMessage(content=user_message)],
        )

        @mlflow.trace(
            name="conversation_turn",
            span_type="CHAIN",
            attributes={
                "conversation_id": state.conversation_id,
                "user_id": user_id,
                "turn": 1,
                "type": "new_conversation",
            },
        )
        async def _traced_invoke() -> ConversationState:
            mlflow.update_current_trace(tags={"mlflow.trace.session": state.conversation_id})
            updates = await self.agent.invoke(state, session=session)
            return state.model_copy(update=updates)

        state = await _traced_invoke()
        return cast("ConversationState", state)

    async def continue_conversation(
        self,
        state: ConversationState,
        user_message: str,
        session: AsyncSession | None = None,
    ) -> ConversationState:
        """Continue an existing conversation.

        Creates an MLflow trace with span hierarchy.

        Args:
            state: Current conversation state
            user_message: New user message
            session: Database session

        Returns:
            Updated conversation state
        """
        import mlflow

        state.messages.append(HumanMessage(content=user_message))
        turn_number = (len(state.messages) + 1) // 2

        @mlflow.trace(
            name="conversation_turn",
            span_type="CHAIN",
            attributes={
                "conversation_id": state.conversation_id,
                "turn": turn_number,
                "message_count": len(state.messages),
                "type": "continue_conversation",
            },
        )
        async def _traced_invoke(
            user_message: str,
            conversation_id: str,
            turn: int,
        ) -> ConversationState:
            mlflow.update_current_trace(tags={"mlflow.trace.session": conversation_id})

            try:
                span = mlflow.get_current_active_span()
                if span:
                    request_id = getattr(span, "request_id", None)
                    if request_id:
                        state.last_trace_id = str(request_id)
            except Exception:
                logger.debug("trace capture failed", exc_info=True)

            updates = await self.agent.invoke(state, session=session)
            return state.model_copy(update=updates)

        state = await _traced_invoke(
            user_message=user_message,
            conversation_id=state.conversation_id,
            turn=turn_number,
        )
        return state

    async def stream_conversation(
        self,
        state: ConversationState,
        user_message: str,
        session: AsyncSession | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream a conversation turn, yielding token and tool events.

        Provides real LLM token streaming instead of batched responses.
        Yields ``StreamEvent`` dicts:
        - ``{"type": "token", "content": "..."}`` for each LLM token
        - ``{"type": "tool_start", "tool": "...", "agent": "..."}``
        - ``{"type": "tool_end", "tool": "...", "result": "..."}``
        - ``{"type": "state", "state": ConversationState}`` final state

        Args:
            state: Current conversation state.
            user_message: New user message.
            session: Database session.

        Yields:
            StreamEvent dicts.
        """
        import mlflow

        from src.agents.streaming import (
            consume_stream,
            dispatch_tool_calls,
            extract_inline_proposals,
            generate_fallback_events,
            parse_tool_calls,
        )

        state.messages.append(HumanMessage(content=user_message))

        # Capture trace ID early so the frontend can start polling
        try:
            mlflow.set_tag("session.id", state.conversation_id)
            span = mlflow.get_current_active_span()
            if span:
                request_id = getattr(span, "request_id", None)
                if request_id:
                    state.last_trace_id = str(request_id)
                    yield StreamEvent(type="trace_id", content=str(request_id))
        except Exception:
            logger.debug("trace ID capture failed", exc_info=True)

        # Build messages and bind tools
        messages = self.agent._build_messages(state)
        if session:
            entity_context = await self.agent._get_entity_context(session, state)
            if entity_context:
                messages.insert(1, SystemMessage(content=entity_context))

        tools = self.agent._get_ha_tools()
        tool_lookup = {tool.name: tool for tool in tools}
        llm = self.agent.llm
        tool_llm = llm.bind_tools(tools) if tools else llm

        # --- Initial LLM stream ---
        collected_content, tool_calls_buffer = "", []
        async for event in consume_stream(tool_llm.astream(messages)):
            if event["type"] == "_consume_result":
                collected_content = event["collected_content"]
                tool_calls_buffer = event["tool_calls_buffer"]
            else:
                yield event

        # --- Multi-turn tool loop ---
        MAX_TOOL_ITERATIONS = 10
        iteration = 0
        all_new_messages: list[BaseMessage] = []
        proposal_summaries: list[str] = []

        while tool_calls_buffer and iteration < MAX_TOOL_ITERATIONS:
            iteration += 1

            # Parse and dispatch tool calls
            parsed = parse_tool_calls(
                tool_calls_buffer,
                is_mutating_fn=self.agent._is_mutating_tool,
            )
            tool_results: dict[str, str] = {}
            full_tool_calls: list[dict[str, Any]] = []

            async for event in dispatch_tool_calls(
                tool_calls=parsed,
                tool_lookup=tool_lookup,
                conversation_id=state.conversation_id,
            ):
                if event["type"] == "_dispatch_result":
                    tool_results = event["tool_results"]
                    full_tool_calls = event["full_tool_calls"]
                    proposal_summaries.extend(event["proposal_summaries"])
                else:
                    yield event

            # Build AI message with tool_calls + ToolMessages
            ai_msg = AIMessage(content=collected_content, tool_calls=full_tool_calls)
            tool_msgs = [
                ToolMessage(content=tool_results.get(tc["id"], ""), tool_call_id=tc.get("id", ""))
                for tc in full_tool_calls
                if not self.agent._is_mutating_tool(tc["name"])
            ]
            all_new_messages.extend([ai_msg, *tool_msgs])

            # Follow-up LLM stream (reuses consume_stream — no duplication)
            follow_up_messages = messages + all_new_messages
            collected_content, tool_calls_buffer = "", []
            async for event in consume_stream(tool_llm.astream(follow_up_messages)):
                if event["type"] == "_consume_result":
                    collected_content = event["collected_content"]
                    tool_calls_buffer = event["tool_calls_buffer"]
                else:
                    yield event

            if not tool_calls_buffer:
                if collected_content:
                    all_new_messages.append(AIMessage(content=collected_content))
                break

        # Append content when no tool calls occurred
        if iteration == 0 and collected_content:
            all_new_messages.append(AIMessage(content=collected_content))

        # Fallback content generation
        for event in generate_fallback_events(
            collected_content=collected_content,
            proposal_summaries=proposal_summaries,
            iteration=iteration,
        ):
            collected_content = event["content"]
            all_new_messages.append(AIMessage(content=collected_content))
            yield event

        # Inline proposal extraction
        await extract_inline_proposals(
            agent=self.agent,
            session=session,
            conversation_id=state.conversation_id,
            collected_content=collected_content,
            proposal_summaries=proposal_summaries,
        )

        state.messages.extend(all_new_messages)  # type: ignore[arg-type]
        yield StreamEvent(type="state", state=state)
