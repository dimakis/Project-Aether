"""Workflow orchestration for the Architect agent.

Contains ``ArchitectWorkflow`` with ``start_conversation``,
``continue_conversation``, and ``stream_conversation``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from src.agents.architect.stream_event import StreamEvent
from src.graph.state import AgentRole, ConversationState

logger = logging.getLogger(__name__)

# Lazy-safe import: mlflow may not be installed or reachable.
try:
    import mlflow
except ImportError:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]


class ArchitectWorkflow:
    """Workflow implementation for the Architect agent.

    Orchestrates the conversation flow:
    1. Receive user message
    2. Process with Architect agent
    3. Handle approvals/rejections
    4. Hand off to Developer for deployment
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None,
    ):
        """Initialize the Architect workflow.

        Args:
            model_name: LLM model to use (e.g., 'gpt-4o', 'gpt-4o-mini')
            temperature: LLM temperature for response generation
            session_factory: Optional session factory for execution context
                so tools can persist reports/insights to the DB.
        """
        from src.agents.architect.agent import ArchitectAgent

        self.agent = ArchitectAgent(model_name=model_name, temperature=temperature)
        self.session_factory = session_factory

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
        state = ConversationState(
            current_agent=AgentRole.ARCHITECT,
            messages=[HumanMessage(content=user_message)],
        )

        # Set LLM call context for usage tracking
        from src.llm_call_context import LLMCallContext, set_llm_call_context

        set_llm_call_context(
            LLMCallContext(
                conversation_id=state.conversation_id,
                agent_role="architect",
                request_type="chat",
            )
        )

        if mlflow is None:
            updates = await self.agent.invoke(state, session=session)
            return cast("ConversationState", state.model_copy(update=updates))

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
            mlflow.update_current_trace(
                metadata={"mlflow.trace.session": state.conversation_id},
                tags={"conversation_id": state.conversation_id},
            )
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
        state.messages.append(HumanMessage(content=user_message))
        turn_number = (len(state.messages) + 1) // 2

        # Set LLM call context for usage tracking
        from src.llm_call_context import LLMCallContext, set_llm_call_context

        set_llm_call_context(
            LLMCallContext(
                conversation_id=state.conversation_id,
                agent_role="architect",
                request_type="chat",
            )
        )

        if mlflow is None:
            updates = await self.agent.invoke(state, session=session)
            return state.model_copy(update=updates)

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
            mlflow.update_current_trace(
                metadata={"mlflow.trace.session": conversation_id},
                tags={"conversation_id": conversation_id},
            )

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

        Uses ``@mlflow.trace`` on an inner async generator to get
        automatic input/output capture, proper trace lifecycle, and
        session metadata per MLflow 3.x patterns.

        Args:
            state: Current conversation state.
            user_message: New user message.
            session: Database session.

        Yields:
            StreamEvent dicts.
        """
        from src.agents.streaming import (
            consume_stream,
            dispatch_tool_calls,
            extract_inline_proposals,
            generate_fallback_events,
            parse_tool_calls,
        )

        state.messages.append(HumanMessage(content=user_message))
        turn_number = (len(state.messages) + 1) // 2

        # ── Inner generator that is MLflow-traced ──
        # @mlflow.trace on async generators (since 2.20.2) automatically:
        # - creates a trace with a root span
        # - captures the function inputs as span inputs
        # - captures all yielded events as span outputs (via output_reducer)
        # - closes the span when the generator is exhausted or raises
        # - autolog LLM calls nest as child spans

        async def _stream_inner(
            user_message: str,
            conversation_id: str,
            turn: int,
        ) -> AsyncGenerator[StreamEvent, None]:
            """Core streaming logic — wrapped by @mlflow.trace when available."""
            # Set LLM call context so usage records capture conversation_id
            # and agent_role (used by _log_usage_async in ResilientLLM).
            from src.llm_call_context import LLMCallContext, set_llm_call_context

            set_llm_call_context(
                LLMCallContext(
                    conversation_id=conversation_id,
                    agent_role="architect",
                    request_type="chat",
                )
            )

            # Build messages and bind tools
            messages = self.agent._build_messages(state)
            entity_context, entity_warning = await self.agent._get_entity_context(state)
            if entity_context:
                messages.insert(1, SystemMessage(content=entity_context))
            if entity_warning:
                yield StreamEvent(
                    type="error",
                    content=entity_warning,
                    error_code="entity_context_degraded",
                    recoverable=True,
                )

            tools = self.agent._get_ha_tools()
            tool_lookup = {tool.name: tool for tool in tools}
            tool_llm = self.agent.get_tool_llm()

            # --- Initial LLM stream ---
            collected_content, tool_calls_buffer = "", []
            async for event in consume_stream(tool_llm.astream(messages)):
                if event["type"] == "_consume_result":
                    collected_content = event["collected_content"]
                    tool_calls_buffer = event["tool_calls_buffer"]
                else:
                    yield event

            # --- Multi-turn tool loop ---
            # Read max iterations from runtime settings (cached, fast)
            try:
                from src.dal.app_settings import get_chat_setting

                max_iter_setting = await get_chat_setting("max_tool_iterations")
                MAX_TOOL_ITERATIONS = int(max_iter_setting) if max_iter_setting else 10
            except Exception:
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
                    session_factory=self.session_factory,
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
                    ToolMessage(
                        content=tool_results.get(tc["id"], ""), tool_call_id=tc.get("id", "")
                    )
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

        # ── Apply @mlflow.trace when mlflow is available ──
        if mlflow is not None:

            def _reduce_stream_output(events: list[Any]) -> dict[str, Any]:
                """Summarize yielded StreamEvents for the MLflow trace output."""
                tokens = sum(1 for e in events if isinstance(e, dict) and e.get("type") == "token")
                tools_used = [
                    e.get("tool")
                    for e in events
                    if isinstance(e, dict) and e.get("type") == "tool_start"
                ]
                return {"token_count": tokens, "tools_used": tools_used}

            traced_stream = mlflow.trace(
                name="conversation_turn",
                span_type="CHAIN",
                attributes={
                    "conversation_id": state.conversation_id,
                    "turn": turn_number,
                    "model": self.agent.model_name or "default",
                    "type": "stream_conversation",
                },
                output_reducer=_reduce_stream_output,
            )(_stream_inner)
        else:
            traced_stream = _stream_inner

        # ── Yield from the (possibly traced) inner generator ──
        # Emit trace_id early so the frontend can start polling the activity panel.
        trace_id_emitted = False
        async for event in traced_stream(
            user_message=user_message,
            conversation_id=state.conversation_id,
            turn=turn_number,
        ):
            # On the first event, capture and emit the trace ID
            if not trace_id_emitted and mlflow is not None:
                trace_id_emitted = True
                try:
                    span = mlflow.get_current_active_span()
                    if span:
                        request_id = getattr(span, "request_id", None)
                        if request_id:
                            state.last_trace_id = str(request_id)
                            yield StreamEvent(type="trace_id", content=str(request_id))
                    # Set session metadata for this trace
                    mlflow.update_current_trace(
                        metadata={"mlflow.trace.session": state.conversation_id},
                        tags={"conversation_id": state.conversation_id},
                    )
                except Exception:
                    logger.debug("trace ID capture failed", exc_info=True)

            yield event
