"""Architect agent for conversational automation design.

The Architect helps users design Home Assistant automations through
natural language conversation, translating their desires into
structured automation proposals.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agents import BaseAgent
from src.dal import AreaRepository, DeviceRepository, EntityRepository, ProposalRepository, ServiceRepository
from src.graph.state import AgentRole, ConversationState, ConversationStatus, HITLApproval
from src.llm import get_llm
from src.settings import get_settings
from src.storage.entities import AutomationProposal, ProposalStatus

# System prompt for the Architect agent
ARCHITECT_SYSTEM_PROMPT = """You are the Architect agent for Project Aether, a Home Assistant automation assistant.

Your role is to help users design home automations through conversation. You:
1. Understand what the user wants to automate
2. Ask clarifying questions when needed
3. Design automations using Home Assistant's trigger/condition/action model
4. Present proposals for human approval before any deployment

## Response Formatting

Use rich markdown formatting in your responses to make them clear and scannable:
- Use **bold** for emphasis and `code` for entity IDs, service calls, and YAML keys
- Use headings (##, ###) to organize longer responses
- Use bullet points and numbered lists for steps and options
- Use code blocks with language tags (```yaml, ```json) for automation configs
- Use tables when comparing options or showing entity states
- Use emojis naturally to improve scanability:
  💡 for lights/ideas, ⚡ for automations/energy, 🌡️ for climate/temperature,
  🔧 for configuration/fixes, ✅ for confirmations, ⚠️ for warnings,
  📊 for data/analysis, 🏠 for home/areas, 🔒 for security,
  🎯 for goals/targets, 💰 for cost savings, 🕐 for time/schedules

When designing automations:
- Use clear, descriptive names (alias)
- Include helpful descriptions
- Choose appropriate triggers (state, time, sun, event, etc.)
- Add conditions when needed to limit when automations run
- Define actions that achieve the user's goal

When you have enough information to propose an automation, respond with a JSON block:
```json
{
  "proposal": {
    "name": "Descriptive automation name",
    "description": "What this automation does",
    "trigger": [{"platform": "...", ...}],
    "conditions": [{"condition": "...", ...}],
    "actions": [{"service": "...", ...}],
    "mode": "single"
  }
}
```

Available entity domains: light, switch, sensor, binary_sensor, climate, cover, fan, 
media_player, automation, script, scene, input_boolean, input_number, input_select, etc.

Available trigger types: state, numeric_state, time, time_pattern, sun, zone, device, 
mqtt, webhook, event, homeassistant, tag, calendar, template.

Available condition types: state, numeric_state, time, sun, zone, template, and, or, not.

Always confirm your understanding before proposing an automation.

## Diagnostic Capabilities

You have tools for diagnosing Home Assistant issues:

### Basic Tools
- **get_ha_logs**: Fetch raw HA error/warning logs.
- **check_ha_config**: Run basic HA config validation.
- **get_entity_history** (with detailed=true): Get rich history with gap detection, statistics,
  and state distribution. Use to identify missing data or connectivity problems.
- **diagnose_issue**: Delegate analysis to the Data Scientist with your collected evidence.

### Advanced Diagnostic Tools
- **analyze_error_log**: Fetch AND analyze the HA error log — parses entries, groups by
  integration, matches against known error patterns, and provides actionable recommendations.
  Prefer this over raw get_ha_logs for structured diagnosis.
- **find_unavailable_entities**: Find all entities in 'unavailable' or 'unknown' state,
  grouped by integration with common-cause detection. Use as a first step when users
  report device or sensor problems.
- **diagnose_entity**: Deep-dive into a single entity — current state, 24h history,
  state transitions, and related error log entries. Use after find_unavailable_entities
  to investigate specific problematic entities.
- **check_integration_health**: Check the health of all HA integrations (config entries).
  Finds integrations in setup_error, not_loaded, or other unhealthy states. Use when
  users report broad integration problems.
- **validate_config**: Run a structured HA configuration check with parsed errors and
  warnings. Prefer this over raw check_ha_config for structured results.

### Diagnostic Workflow

When a user reports a system issue (missing data, broken sensor, unexpected behavior):

1. **Triage**: Start with `analyze_error_log` and `find_unavailable_entities` to get a
   broad picture of system health.
2. **Deep-dive**: For specific entities, use `diagnose_entity`. For integration issues,
   use `check_integration_health`.
3. **Validate**: If config issues are suspected, use `validate_config`.
4. **Delegate to Data Scientist**: Use `diagnose_issue` with:
   - entity_ids: the affected entities
   - diagnostic_context: your collected evidence (logs, history observations, config results)
   - instructions: specific analysis you want the DS to perform
5. **Synthesize**: Combine DS findings with your own observations into a clear diagnosis.
6. **Iterate if Needed**: If the DS results suggest additional investigation, gather more data
   and re-delegate with refined instructions.

Present diagnostic findings clearly: what's wrong, what caused it, and what the user can do."""


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

    async def invoke(
        self,
        state: ConversationState,
        **kwargs: Any,
    ) -> dict[str, Any]:
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
            for msg in reversed(state.messages):
                if hasattr(msg, "content") and type(msg).__name__ in ("HumanMessage", "UserMessage"):
                    user_message = str(msg.content)[:1000]
                    break

        # Build inputs for tracing
        trace_inputs = {
            "user_message": user_message,
            "conversation_id": state.conversation_id,
            "message_count": len(state.messages),
        }

        async with self.trace_span("invoke", state, inputs=trace_inputs) as span:
            session = kwargs.get("session")

            # Build messages for LLM (state context logged by trace_span)
            messages = self._build_messages(state)

            # Add entity context if session available
            if session:
                entity_context = await self._get_entity_context(session, state)
                if entity_context:
                    messages.insert(1, SystemMessage(content=entity_context))

            # Generate response (with HA tools available)
            tools = self._get_ha_tools()
            tool_llm = self.llm.bind_tools(tools) if tools else self.llm
            response = await tool_llm.ainvoke(messages)

            # Handle tool calls with strict approval for any HA-altering actions
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_call_updates = await self._handle_tool_calls(
                    response,
                    messages,
                    tools,
                    state,
                )
                if tool_call_updates is not None:
                    # Set outputs before returning for trace visualization
                    tool_call_names = [tc.get("name", "") for tc in response.tool_calls]
                    final_response = ""
                    if tool_call_updates.get("messages"):
                        # Get the last AI message as the final response
                        for msg in reversed(tool_call_updates["messages"]):
                            if hasattr(msg, "content") and type(msg).__name__ == "AIMessage":
                                final_response = str(msg.content)[:2000]
                                break
                    span["outputs"] = {
                        "response": final_response,
                        "tool_calls": tool_call_names,
                        "has_tool_calls": True,
                        "requires_approval": "pending_approvals" in tool_call_updates,
                    }
                    return tool_call_updates

            response_text = response.content

            # Log conversation with response and tool calls
            # Note: Token usage is captured automatically by MLflow autolog
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

            # Track metrics and set outputs for trace visualization
            span["response_length"] = len(response_text)
            span["outputs"] = {
                "response": response_text[:2000],
                "has_tool_calls": bool(tool_calls_data),
            }

            # Parse for proposal
            proposal_data = self._extract_proposal(response_text)
            updates: dict[str, Any] = {
                "messages": [AIMessage(content=response_text)],
            }

            # If we have a proposal, create it and add to pending approvals
            if proposal_data and session:
                proposal = await self._create_proposal(
                    session,
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

    def _build_messages(self, state: ConversationState) -> list:
        """Build message list for LLM from state.

        Args:
            state: Current conversation state

        Returns:
            List of messages for LLM
        """
        from langchain_core.messages import ToolMessage

        messages = [SystemMessage(content=ARCHITECT_SYSTEM_PROMPT)]

        for msg in state.messages:
            if isinstance(msg, HumanMessage):
                messages.append(msg)
            elif isinstance(msg, AIMessage):
                messages.append(msg)
            elif isinstance(msg, ToolMessage):
                # Must include tool responses after AI messages with tool_calls
                messages.append(msg)

        return messages

    def _serialize_messages(
        self,
        messages: list[Any],
        max_messages: int = 20,
        max_chars: int = 500,
    ) -> list[dict[str, str]]:
        """Serialize messages for MLflow logging."""
        serialized: list[dict[str, str]] = []
        for msg in messages[-max_messages:]:
            role = getattr(msg, "type", msg.__class__.__name__)
            content = getattr(msg, "content", "")
            serialized.append(
                {
                    "role": str(role),
                    "content": str(content)[:max_chars],
                }
            )
        return serialized

    def _get_ha_tools(self) -> list[Any]:
        """Get all tools for the Architect agent.

        Includes:
        - HA tools: entity queries, control
        - Agent tools: energy analysis, discovery (delegated to specialists)
        """
        try:
            from src.tools import get_all_tools
            return get_all_tools()
        except Exception:
            return []

    def _is_mutating_tool(self, tool_name: str) -> bool:
        """Check if a tool call can mutate Home Assistant state."""
        return tool_name in {"control_entity"}

    async def _handle_tool_calls(
        self,
        response: AIMessage,
        messages: list[Any],
        tools: list[Any],
        state: ConversationState,
    ) -> dict[str, Any] | None:
        """Handle tool calls from the LLM.

        Read-only tools are executed immediately. Any mutating tool requires
        explicit user approval before execution.
        """
        tool_lookup = {tool.name: tool for tool in tools}
        tool_calls = response.tool_calls or []

        mutating_calls = [call for call in tool_calls if self._is_mutating_tool(call["name"])]
        if mutating_calls:
            # Require explicit approval for HA-altering actions
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

        # Execute read-only tools and continue the conversation
        tool_messages: list[ToolMessage] = []
        for call in tool_calls:
            tool = tool_lookup.get(call["name"])
            if not tool:
                continue
            result = await tool.ainvoke(call.get("args", {}))
            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=call.get("id", ""),
                )
            )

        # Ask LLM to produce a final response with tool results
        follow_up = await self.llm.ainvoke(
            messages + [response] + tool_messages
        )

        return {
            "messages": [response, *tool_messages, AIMessage(content=follow_up.content)],
        }

    async def _get_entity_context(
        self,
        session: Any,
        state: ConversationState,
    ) -> str | None:
        """Get relevant entity context for the conversation.

        Args:
            session: Database session
            state: Current conversation state

        Returns:
            Context string or None
        """
        try:
            repo = EntityRepository(session)
            device_repo = DeviceRepository(session)
            area_repo = AreaRepository(session)
            service_repo = ServiceRepository(session)

            # Get counts by domain
            counts = await repo.get_domain_counts()
            if not counts:
                return None

            context_parts = ["Available entities in this Home Assistant instance:"]

            # Key domains to list in detail (most useful for automations)
            detailed_domains = ["light", "switch", "climate", "cover", "fan", "lock", "alarm_control_panel"]

            # Batch-fetch entities for all detailed domains in a single query (T190)
            domains_to_detail = [
                d for d, c in counts.items()
                if d in detailed_domains and c <= 50
            ]
            entities_by_domain = await repo.list_by_domains(
                domains_to_detail, limit_per_domain=50,
            )

            for domain, count in sorted(counts.items()):
                if domain in entities_by_domain:
                    entities = entities_by_domain[domain]
                    entity_list = []
                    for e in entities:
                        name = e.name or e.entity_id.split(".")[-1].replace("_", " ").title()
                        state_str = f" ({e.state})" if e.state else ""
                        area_str = f" in {e.area.name}" if e.area else ""
                        entity_list.append(f"  - {e.entity_id}: {name}{state_str}{area_str}")
                    context_parts.append(f"- {domain} ({count}):")
                    context_parts.extend(entity_list)
                else:
                    context_parts.append(f"- {domain}: {count} entities")

            # Areas summary
            areas = await area_repo.list_all(limit=20)
            if areas:
                context_parts.append("\nAreas (up to 20):")
                for area in areas:
                    context_parts.append(f"- {area.name} (id: {area.ha_area_id})")

            # Devices summary
            devices = await device_repo.list_all(limit=20)
            if devices:
                context_parts.append("\nDevices (up to 20):")
                for device in devices:
                    area_name = device.area.name if device.area else "unknown area"
                    context_parts.append(
                        f"- {device.name} (area: {area_name}, id: {device.ha_device_id})"
                    )

            # Services summary
            services = await service_repo.list_all(limit=30)
            if services:
                context_parts.append("\nServices (sample of 30):")
                for svc in services:
                    context_parts.append(f"- {svc.domain}.{svc.service}")

            # If specific entities mentioned, get their details
            if state.entities_mentioned:
                context_parts.append("\nEntities mentioned by user:")
                for entity_id in state.entities_mentioned[:10]:  # Limit to 10
                    entity = await repo.get_by_entity_id(entity_id)
                    if entity:
                        context_parts.append(
                            f"- {entity.entity_id}: {entity.name or 'unnamed'} "
                            f"(state: {entity.state})"
                        )

            return "\n".join(context_parts)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get entity context: {e}")
            return None

    def _extract_proposal(self, response: str) -> dict | None:
        """Extract proposal JSON from response if present.

        Args:
            response: LLM response text

        Returns:
            Proposal dict or None
        """
        import json
        import re

        # Look for JSON block in response
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        if not json_match:
            return None

        try:
            data = json.loads(json_match.group(1))
            if "proposal" in data:
                return data["proposal"]
            return None
        except json.JSONDecodeError:
            return None

    async def _create_proposal(
        self,
        session: Any,
        conversation_id: str,
        proposal_data: dict,
    ) -> AutomationProposal:
        """Create an automation proposal from parsed data.

        Args:
            session: Database session
            conversation_id: Source conversation
            proposal_data: Parsed proposal data

        Returns:
            Created proposal
        """
        repo = ProposalRepository(session)

        proposal = await repo.create(
            name=proposal_data.get("name", "Untitled Automation"),
            trigger=proposal_data.get("trigger", []),
            actions=proposal_data.get("actions", []),
            conversation_id=conversation_id,
            description=proposal_data.get("description"),
            conditions=proposal_data.get("conditions"),
            mode=proposal_data.get("mode", "single"),
        )

        # Submit for approval
        await repo.propose(proposal.id)

        return proposal

    def _proposal_to_yaml(self, proposal_data: dict) -> str:
        """Convert proposal to YAML string for display.

        Args:
            proposal_data: Proposal data dict

        Returns:
            YAML string
        """
        import yaml

        automation = {
            "alias": proposal_data.get("name"),
            "description": proposal_data.get("description", ""),
            "trigger": proposal_data.get("trigger", []),
            "action": proposal_data.get("actions", []),
            "mode": proposal_data.get("mode", "single"),
        }

        if proposal_data.get("conditions"):
            automation["condition"] = proposal_data["conditions"]

        return yaml.dump(automation, default_flow_style=False, sort_keys=False)

    async def refine_proposal(
        self,
        state: ConversationState,
        feedback: str,
        proposal_id: str,
        session: Any,
    ) -> dict[str, Any]:
        """Refine a proposal based on user feedback.

        Args:
            state: Current conversation state
            feedback: User's feedback
            proposal_id: ID of proposal to refine
            session: Database session

        Returns:
            State updates
        """
        # Get existing proposal
        proposal_repo = ProposalRepository(session)
        proposal = await proposal_repo.get_by_id(proposal_id)
        if not proposal:
            return {"messages": [AIMessage(content="I couldn't find that proposal to refine.")]}

        # Build context with current proposal
        current_yaml = proposal.to_ha_yaml_dict()

        messages = self._build_messages(state)
        messages.append(
            SystemMessage(
                content=f"The user wants to refine this proposal:\n```yaml\n"
                f"{self._proposal_to_yaml(current_yaml)}\n```\n"
                f"User feedback: {feedback}"
            )
        )

        # Generate refined response
        response = await self.llm.ainvoke(messages)
        response_text = response.content

        # Check for new proposal
        proposal_data = self._extract_proposal(response_text)
        updates: dict[str, Any] = {
            "messages": [
                HumanMessage(content=feedback),
                AIMessage(content=response_text),
            ]
        }

        if proposal_data:
            # Archive old proposal and create new one
            await proposal_repo.reject(proposal_id, "Replaced with refined version")

            new_proposal = await self._create_proposal(
                session,
                state.conversation_id,
                proposal_data,
            )
            updates["pending_approvals"] = [
                HITLApproval(
                    id=new_proposal.id,
                    request_type="automation",
                    description=new_proposal.description or new_proposal.name,
                    yaml_content=self._proposal_to_yaml(proposal_data),
                )
            ]
            updates["architect_design"] = proposal_data

        return updates


    async def receive_suggestion(
        self,
        suggestion: Any,
        session: Any,
    ) -> dict[str, Any]:
        """Receive an AutomationSuggestion from the Data Scientist and create a proposal.

        Converts the DS suggestion into a structured prompt, generates a full
        automation proposal, and returns it for HITL approval.

        Feature 03: Intelligent Optimization — DS-to-Architect suggestion flow.

        Args:
            suggestion: AutomationSuggestion model from the Data Scientist
            session: Database session for proposal persistence

        Returns:
            Dict with proposal data and formatted response
        """
        # Build a structured prompt from the suggestion
        prompt = (
            f"The Data Scientist has identified a pattern that could be automated:\n\n"
            f"**Pattern:** {suggestion.pattern}\n"
            f"**Entities:** {', '.join(suggestion.entities[:10])}\n"
            f"**Proposed Trigger:** {suggestion.proposed_trigger}\n"
            f"**Proposed Action:** {suggestion.proposed_action}\n"
            f"**Confidence:** {suggestion.confidence:.0%}\n"
            f"**Source Analysis:** {suggestion.source_insight_type}\n"
        )

        if suggestion.evidence:
            import json
            evidence_str = json.dumps(suggestion.evidence, indent=2, default=str)[:500]
            prompt += f"\n**Evidence:**\n```json\n{evidence_str}\n```\n"

        prompt += (
            "\nPlease design a complete Home Assistant automation based on this suggestion. "
            "Include the full trigger, conditions (if needed), and actions in a JSON proposal block."
        )

        messages = [
            SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        async with self.trace_span("receive_suggestion", None) as span:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            span["outputs"] = {"response_length": len(response_text)}

            # Try to extract a proposal
            proposal_data = self._extract_proposal(response_text)

            result: dict[str, Any] = {
                "response": response_text,
                "proposal_data": proposal_data,
            }

            if proposal_data and session:
                try:
                    proposal = await self._create_proposal(
                        session,
                        conversation_id="ds_suggestion",
                        proposal_data=proposal_data,
                    )
                    result["proposal_id"] = proposal.id
                    result["proposal_name"] = proposal.name
                    result["proposal_yaml"] = self._proposal_to_yaml(proposal_data)
                except Exception as e:
                    logger.warning(f"Failed to create proposal from suggestion: {e}")
                    result["error"] = str(e)

            return result


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
        self.agent = ArchitectAgent(model_name=model_name, temperature=temperature)

    async def start_conversation(
        self,
        user_message: str,
        user_id: str = "default_user",
        session: Any = None,
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

        # Create MLflow trace with proper span hierarchy
        # This shows as a tree in MLflow UI with timing for each span
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
        async def _traced_invoke():
            # Set session for grouping multiple turns
            mlflow.update_current_trace(
                metadata={"mlflow.trace.session": state.conversation_id}
            )
            return await self.agent.invoke(state, session=session)

        updates = await _traced_invoke()
        state = state.model_copy(update=updates)

        return state

    async def continue_conversation(
        self,
        state: ConversationState,
        user_message: str,
        session: Any = None,
    ) -> ConversationState:
        """Continue an existing conversation.

        Creates an MLflow trace with span hierarchy.
        Shows as a tree in MLflow UI with timing visible.

        Args:
            state: Current conversation state
            user_message: New user message
            session: Database session

        Returns:
            Updated conversation state
        """
        import mlflow

        # Add user message
        state.messages.append(HumanMessage(content=user_message))
        turn_number = (len(state.messages) + 1) // 2  # Count conversation turns

        # Create MLflow trace with proper span hierarchy.
        # _traced_invoke accepts key context as parameters so MLflow
        # auto-captures them as trace inputs (visible in the UI).
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
        ):
            # Set session for grouping multiple turns
            mlflow.update_current_trace(
                metadata={"mlflow.trace.session": conversation_id}
            )

            # Capture the trace request_id so the SSE stream can include it
            # for the frontend Agent Activity panel.
            try:
                span = mlflow.get_current_active_span()
                if span:
                    request_id = getattr(span, "request_id", None)
                    if request_id:
                        state.last_trace_id = str(request_id)
            except Exception:
                pass  # trace capture is best-effort

            return await self.agent.invoke(state, session=session)

        updates = await _traced_invoke(
            user_message=user_message,
            conversation_id=state.conversation_id,
            turn=turn_number,
        )
        state = state.model_copy(update=updates)

        return state


# Exports
__all__ = [
    "ArchitectAgent",
    "ArchitectWorkflow",
    "ARCHITECT_SYSTEM_PROMPT",
]
