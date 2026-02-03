"""Architect agent for conversational automation design.

The Architect helps users design Home Assistant automations through
natural language conversation, translating their desires into
structured automation proposals.
"""

from datetime import datetime
from typing import Any

import mlflow
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agents import BaseAgent
from src.dal import (
    AreaRepository,
    DeviceRepository,
    EntityRepository,
    ProposalRepository,
    ServiceRepository,
)
from src.graph.state import AgentRole, ConversationState, ConversationStatus, HITLApproval
from src.llm import get_llm
from src.settings import get_settings
from src.storage.entities import AutomationProposal, ProposalStatus
from src.tracing import start_run

# System prompt for the Architect agent
ARCHITECT_SYSTEM_PROMPT = """You are the Architect agent for Project Aether, a Home Assistant automation assistant.

Your role is to help users design home automations through conversation. You:
1. Understand what the user wants to automate
2. Ask clarifying questions when needed
3. Design automations using Home Assistant's trigger/condition/action model
4. Present proposals for human approval before any deployment

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

Always confirm your understanding before proposing an automation."""


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
        async with self.trace_span("invoke", state) as span:
            session = kwargs.get("session")

            # Build messages for LLM
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
                    return tool_call_updates

            response_text = response.content

            # Track metrics
            span["response_length"] = len(response_text)
            self.log_metric("response_tokens", response.response_metadata.get("token_usage", {}).get("total_tokens", 0))

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

            return updates

    def _build_messages(self, state: ConversationState) -> list:
        """Build message list for LLM from state.

        Args:
            state: Current conversation state

        Returns:
            List of messages for LLM
        """
        messages = [SystemMessage(content=ARCHITECT_SYSTEM_PROMPT)]

        for msg in state.messages:
            if isinstance(msg, HumanMessage):
                messages.append(msg)
            elif isinstance(msg, AIMessage):
                messages.append(msg)

        return messages

    def _get_ha_tools(self) -> list[Any]:
        """Get Home Assistant tools for the Architect agent."""
        try:
            from src.tools.ha_tools import get_ha_tools
            return get_ha_tools()
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

            for domain, count in sorted(counts.items()):
                if domain in detailed_domains and count <= 50:
                    # List actual entities for key domains
                    entities = await repo.list_all(domain=domain, limit=50)
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


class ArchitectWorkflow:
    """Workflow implementation for the Architect agent.

    Orchestrates the conversation flow:
    1. Receive user message
    2. Process with Architect agent
    3. Handle approvals/rejections
    4. Hand off to Developer for deployment
    """

    def __init__(self):
        """Initialize the Architect workflow."""
        self.agent = ArchitectAgent()

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
        state = ConversationState(
            current_agent=AgentRole.ARCHITECT,
            messages=[HumanMessage(content=user_message)],
        )

        # Process with agent
        updates = await self.agent.invoke(state, session=session)
        state = state.model_copy(update=updates)

        return state

    async def continue_conversation(
        self,
        state: ConversationState,
        user_message: str,
        session: Any = None,
    ) -> ConversationState:
        """Continue an existing conversation.

        Args:
            state: Current conversation state
            user_message: New user message
            session: Database session

        Returns:
            Updated conversation state
        """
        # Add user message
        state.messages.append(HumanMessage(content=user_message))

        # Process with agent
        updates = await self.agent.invoke(state, session=session)
        state = state.model_copy(update=updates)

        return state


# Exports
__all__ = [
    "ArchitectAgent",
    "ArchitectWorkflow",
    "ARCHITECT_SYSTEM_PROMPT",
]
