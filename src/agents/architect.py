"""Architect agent for conversational automation design.

The Architect helps users design Home Assistant automations through
natural language conversation, translating their desires into
structured automation proposals.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage
    from langchain_core.tools import BaseTool
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.graph.state import AutomationSuggestion
    from src.storage.entities import AutomationProposal

import asyncio
import contextlib

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agents import BaseAgent
from src.agents.execution_context import (
    ProgressEvent,
    execution_context,
)
from src.agents.prompts import load_prompt
from src.dal import (
    AreaRepository,
    DeviceRepository,
    EntityRepository,
    ProposalRepository,
    ServiceRepository,
)
from src.graph.state import AgentRole, ConversationState, ConversationStatus, HITLApproval
from src.llm import get_llm
from src.settings import ANALYSIS_TOOLS, get_settings


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
            for msg in reversed(state.messages):
                if hasattr(msg, "content") and type(msg).__name__ in (
                    "HumanMessage",
                    "UserMessage",
                ):
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
            updates: dict[str, object] = {
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

    def _build_messages(self, state: ConversationState) -> list[BaseMessage]:
        """Build message list for LLM from state.

        Args:
            state: Current conversation state

        Returns:
            List of messages for LLM
        """
        from langchain_core.messages import ToolMessage

        messages: list[BaseMessage] = [SystemMessage(content=load_prompt("architect_system"))]

        for msg in state.messages:
            if isinstance(msg, (HumanMessage, AIMessage)):
                messages.append(msg)
            elif isinstance(msg, ToolMessage):
                # Must include tool responses after AI messages with tool_calls
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
            serialized.append(
                {
                    "role": str(role),
                    "content": str(content)[:max_chars],
                }
            )
        return serialized

    def _get_ha_tools(self) -> list[BaseTool]:
        """Get the curated Architect tool set (12 tools).

        The Architect is a lean router — it delegates analysis to the
        DS team via ``consult_data_science_team`` and mutations via
        ``seek_approval``.  Mutation tools and individual specialist
        tools are NOT bound here.
        """
        try:
            from src.tools import get_architect_tools

            return get_architect_tools()
        except Exception:
            import logging

            logging.getLogger(__name__).error(
                "Failed to load tools -- agent will operate without tools. "
                "This may affect HITL enforcement.",
                exc_info=True,
            )
            return []

    # Read-only tools that can execute without HITL approval.
    # Every tool in get_architect_tools() is read-only except seek_approval,
    # which is the approval mechanism itself (creating proposals, not mutations).
    _READ_ONLY_TOOLS: frozenset[str] = frozenset(
        {
            # HA query tools (10)
            "get_entity_state",
            "list_entities_by_domain",
            "search_entities",
            "get_domain_summary",
            "list_automations",
            "get_automation_config",
            "get_script_config",
            "render_template",
            "get_ha_logs",
            "check_ha_config",
            # Discovery (1)
            "discover_entities",
            # Specialist delegation (2) — read-only analysis
            "consult_data_science_team",
            "consult_dashboard_designer",
            # Scheduling (1) — creates config, no HA mutation
            "create_insight_schedule",
            # Approval (1) — creating proposals IS the approval mechanism
            "seek_approval",
            # Review (1) — creates review proposals for HITL approval
            "review_config",
        }
    )

    def _is_mutating_tool(self, tool_name: str) -> bool:
        """Check if a tool call can mutate Home Assistant state.

        Uses a whitelist of known read-only tools. Any tool not in the
        whitelist is treated as mutating and requires HITL approval.
        This fail-safe approach ensures newly registered tools default
        to requiring approval rather than silently bypassing it.
        """
        return tool_name not in self._READ_ONLY_TOOLS

    async def _handle_tool_calls(
        self,
        response: AIMessage,
        messages: list[BaseMessage],
        tools: list[BaseTool],
        state: ConversationState,
    ) -> dict[str, object] | None:
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

        # Execute read-only tools in parallel and continue the conversation
        async def _invoke_tool(
            call: dict[str, object],
        ) -> ToolMessage | None:
            tool = tool_lookup.get(call["name"])  # type: ignore[arg-type]
            if not tool:
                return None
            result = await tool.ainvoke(call.get("args", {}))
            return ToolMessage(
                content=str(result),
                tool_call_id=call.get("id", ""),  # type: ignore[arg-type]
            )

        raw_results = await asyncio.gather(*(_invoke_tool(call) for call in tool_calls))
        tool_messages: list[ToolMessage] = [m for m in raw_results if m is not None]

        # Ask LLM to produce a final response with tool results
        follow_up = await self.llm.ainvoke([*messages, response, *tool_messages])

        return {
            "messages": [response, *tool_messages, AIMessage(content=follow_up.content)],
        }

    async def _get_entity_context(
        self,
        session: AsyncSession,
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

            # Phase 1: fetch domain counts + independent summaries in parallel
            counts_result, areas, devices, services = await asyncio.gather(
                repo.get_domain_counts(),
                area_repo.list_all(limit=20),
                device_repo.list_all(limit=20),
                service_repo.list_all(limit=30),
            )
            counts: dict[str, int] = counts_result or {}
            if not counts:
                return None

            context_parts = ["Available entities in this Home Assistant instance:"]

            # Key domains to list in detail (most useful for automations)
            detailed_domains = [
                "light",
                "switch",
                "climate",
                "cover",
                "fan",
                "lock",
                "alarm_control_panel",
            ]

            # Batch-fetch entities for all detailed domains in a single query (T190)
            domains_to_detail = [d for d, c in counts.items() if d in detailed_domains and c <= 50]
            entities_by_domain = await repo.list_by_domains(
                domains_to_detail,
                limit_per_domain=50,
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

            # Areas summary (already fetched in parallel)
            if areas:
                context_parts.append("\nAreas (up to 20):")
                for area in areas:
                    context_parts.append(f"- {area.name} (id: {area.ha_area_id})")

            # Devices summary (already fetched in parallel)
            if devices:
                context_parts.append("\nDevices (up to 20):")
                for device in devices:
                    area_name = device.area.name if device.area else "unknown area"
                    context_parts.append(
                        f"- {device.name} (area: {area_name}, id: {device.ha_device_id})"
                    )

            # Services summary (already fetched in parallel)
            if services:
                context_parts.append("\nServices (sample of 30):")
                for svc in services:
                    context_parts.append(f"- {svc.domain}.{svc.service}")

            # Fetch mentioned entities in parallel
            if state.entities_mentioned:
                mentioned_results = await asyncio.gather(
                    *(repo.get_by_entity_id(eid) for eid in state.entities_mentioned[:10])
                )
                found = [e for e in mentioned_results if e is not None]
                if found:
                    context_parts.append("\nEntities mentioned by user:")
                    for entity in found:
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
        """Extract the first proposal JSON from response if present.

        Args:
            response: LLM response text

        Returns:
            Proposal dict or None
        """
        proposals = self._extract_proposals(response)
        return proposals[0] if proposals else None

    def _extract_proposals(self, response: str) -> list[dict]:
        """Extract all proposal JSON blocks from response.

        Uses ``re.finditer`` to find ALL ```json code blocks, then
        attempts to parse each as JSON containing a ``"proposal"`` key.

        The regex uses ``(.*?)`` (not ``\\{.*?\\}``) to prevent a
        truncated JSON block from consuming the *next* block when
        ``re.DOTALL`` causes ``.*?`` to cross ````` boundaries.

        Args:
            response: LLM response text

        Returns:
            List of proposal dicts (may be empty)
        """
        import json
        import re

        proposals: list[dict] = []
        for block_match in re.finditer(r"```json\s*(.*?)\s*```", response, re.DOTALL):
            raw = block_match.group(1).strip()
            if not raw.startswith("{"):
                continue
            try:
                data = json.loads(raw)
                if "proposal" in data and isinstance(data["proposal"], dict):
                    proposals.append(data["proposal"])
            except json.JSONDecodeError:
                continue
        return proposals

    async def _create_proposal(
        self,
        session: AsyncSession,
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
            proposal_type=proposal_data.get("proposal_type", "automation"),
        )

        # Submit for approval
        await repo.propose(proposal.id)

        return proposal

    def _proposal_to_yaml(self, proposal_data: dict) -> str:
        """Convert proposal to YAML string for display.

        Supports automation, script, and scene proposal types.

        Args:
            proposal_data: Proposal data dict

        Returns:
            YAML string
        """
        import yaml

        proposal_type = proposal_data.get("proposal_type", "automation")

        if proposal_type == "script":
            # HA script format: alias, sequence, mode
            script = {
                "alias": proposal_data.get("name"),
                "description": proposal_data.get("description", ""),
                "sequence": proposal_data.get("actions", []),
                "mode": proposal_data.get("mode", "single"),
            }
            return yaml.dump(script, default_flow_style=False, sort_keys=False)

        if proposal_type == "scene":
            # HA scene format: name, entities
            entities = {}
            for action in proposal_data.get("actions", []):
                entity_id = action.get("entity_id")
                if entity_id:
                    entity_state = {k: v for k, v in action.items() if k != "entity_id"}
                    entities[entity_id] = entity_state
            scene = {
                "name": proposal_data.get("name"),
                "entities": entities,
            }
            return yaml.dump(scene, default_flow_style=False, sort_keys=False)

        # Default: automation format
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

    # -----------------------------------------------------------------
    # Config review synthesis (used by review workflow)
    # -----------------------------------------------------------------

    async def synthesize_review(
        self,
        configs: dict[str, str],
        ds_findings: list[dict[str, Any]],
        entity_context: dict[str, Any] | None = None,
        focus: str | None = None,
    ) -> list[dict[str, Any]]:
        """Synthesize DS team findings into concrete YAML improvement suggestions.

        Called by the config review workflow after the DS team has analyzed
        the configs. The Architect combines findings with its understanding
        of HA best practices to produce actionable YAML suggestions.

        Args:
            configs: Mapping of entity_id -> original YAML config.
            ds_findings: Findings from DS team specialists.
            entity_context: Optional context (areas, entities, etc.).
            focus: Optional focus area (energy, behavioral, efficiency, security).

        Returns:
            List of suggestion dicts with entity_id, suggested_yaml, review_notes.
        """
        import json

        from langchain_core.messages import HumanMessage, SystemMessage

        configs_block = "\n---\n".join(f"# {eid}\n{yaml_str}" for eid, yaml_str in configs.items())
        findings_block = json.dumps(ds_findings, indent=2, default=str)
        context_block = json.dumps(entity_context or {}, default=str)[:2000]

        focus_instruction = ""
        if focus:
            focus_instruction = (
                f"\nFocus area: {focus}. Prioritize improvements related to {focus}.\n"
            )

        system_prompt = (
            "You are the Architect agent. Synthesize the Data Science team's "
            "findings into concrete YAML improvement suggestions for Home "
            "Assistant configurations.\n\n"
            "For each entity that needs changes, produce a suggestion with:\n"
            '  "entity_id": the HA entity ID,\n'
            '  "suggested_yaml": the improved YAML configuration,\n'
            '  "review_notes": explanation of what changed and why\n\n'
            "Return ONLY a JSON array of suggestion objects. "
            "No markdown fencing."
            f"{focus_instruction}"
        )

        user_prompt = (
            f"Original configurations:\n```yaml\n{configs_block}\n```\n\n"
            f"DS team findings:\n{findings_block}\n\n"
            f"Entity context:\n{context_block}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            # Strip markdown fencing if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            suggestions = json.loads(content.strip())
            if not isinstance(suggestions, list):
                suggestions = []
        except json.JSONDecodeError:
            logger.warning(
                "Architect: failed to parse synthesize_review response (JSON decode error)"
            )
            suggestions = []
        except Exception:
            logger.warning("Architect: failed to parse synthesize_review response")
            suggestions = []

        return suggestions

    async def refine_proposal(
        self,
        state: ConversationState,
        feedback: str,
        proposal_id: str,
        session: AsyncSession,
    ) -> dict[str, object]:
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
        response_text = str(response.content)

        # Check for new proposal
        proposal_data = self._extract_proposal(response_text)
        updates: dict[str, object] = {
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
        suggestion: AutomationSuggestion,
        session: AsyncSession,
    ) -> dict[str, object]:
        """Receive an AutomationSuggestion from the DS Team and create a proposal.

        Converts the DS Team suggestion into a structured prompt, generates a full
        automation proposal, and returns it for HITL approval.

        Feature 03: Intelligent Optimization — DS Team-to-Architect suggestion flow.

        Args:
            suggestion: AutomationSuggestion model from the DS Team
            session: Database session for proposal persistence

        Returns:
            Dict with proposal data and formatted response
        """
        # Build a structured prompt from the suggestion
        prompt = (
            f"The Data Science team has identified a pattern that could be automated:\n\n"
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
            SystemMessage(content=load_prompt("architect_system")),
            HumanMessage(content=prompt),
        ]

        async with self.trace_span("receive_suggestion", None) as span:
            response = await self.llm.ainvoke(messages)
            response_text = str(response.content)

            span["outputs"] = {"response_length": len(response_text)}

            # Try to extract a proposal
            proposal_data = self._extract_proposal(response_text)

            result: dict[str, object] = {
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
        async def _traced_invoke() -> ConversationState:
            # Set session for grouping multiple turns
            mlflow.update_current_trace(tags={"mlflow.trace.session": state.conversation_id})
            updates = await self.agent.invoke(state, session=session)
            return state.model_copy(update=updates)

        state = await _traced_invoke()

        return state

    async def continue_conversation(
        self,
        state: ConversationState,
        user_message: str,
        session: AsyncSession | None = None,
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
        ) -> ConversationState:
            # Set session for grouping multiple turns
            mlflow.update_current_trace(tags={"mlflow.trace.session": conversation_id})

            # Capture the trace request_id so the SSE stream can include it
            # for the frontend Agent Activity panel.
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

        state.messages.append(HumanMessage(content=user_message))
        (len(state.messages) + 1) // 2

        # Capture trace ID and emit it early so the frontend can start polling
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

        # Build messages for LLM
        messages = self.agent._build_messages(state)

        # Add entity context if session available
        if session:
            entity_context = await self.agent._get_entity_context(session, state)
            if entity_context:
                messages.insert(1, SystemMessage(content=entity_context))

        # Get tools and bind them
        tools = self.agent._get_ha_tools()
        tool_lookup = {tool.name: tool for tool in tools}
        llm = self.agent.llm
        tool_llm = llm.bind_tools(tools) if tools else llm

        # Stream tokens from the LLM
        collected_content = ""
        tool_calls_buffer: list[dict] = []
        full_tool_calls: list[dict] = []

        async for chunk in tool_llm.astream(messages):
            has_tool_chunks = hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks

            # Token content — skip when tool call chunks are present in the
            # same chunk to avoid leaking partial JSON from some models
            if chunk.content and not has_tool_chunks:
                token = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                collected_content += token
                yield StreamEvent(type="token", content=token)

            # Tool call chunks (accumulated across multiple stream chunks)
            if has_tool_chunks:
                tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []
                for tc_chunk in tool_call_chunks:
                    # Merge into buffer by index
                    idx = tc_chunk.get("index", 0)
                    while len(tool_calls_buffer) <= idx:
                        tool_calls_buffer.append({"name": "", "args": "", "id": ""})
                    buf = tool_calls_buffer[idx]
                    if tc_chunk.get("name"):
                        buf["name"] = tc_chunk["name"]
                    if tc_chunk.get("args"):
                        buf["args"] += tc_chunk["args"]
                    if tc_chunk.get("id"):
                        buf["id"] = tc_chunk["id"]

        # Multi-turn tool loop: allow the LLM to chain tool calls
        MAX_TOOL_ITERATIONS = 10
        iteration = 0
        all_new_messages: list[BaseMessage] = []
        proposal_summaries: list[str] = []  # Track successful seek_approval results

        while tool_calls_buffer and iteration < MAX_TOOL_ITERATIONS:
            iteration += 1
            import json as _json

            tool_results: dict[str, str] = {}  # tool_call_id -> result
            full_tool_calls = []

            for tc_buf in tool_calls_buffer:
                tool_name = tc_buf["name"]
                tool_call_id = tc_buf["id"]

                # Skip truncated tool calls (empty name = output token limit hit)
                if not tool_name:
                    logger.warning(
                        "Skipping tool call with empty name "
                        "(likely truncated LLM output due to max_tokens)"
                    )
                    continue

                try:
                    args = _json.loads(tc_buf["args"]) if tc_buf["args"] else {}
                except _json.JSONDecodeError:
                    logger.warning(
                        "Skipping tool call '%s': args JSON could not be parsed "
                        "(likely truncated LLM output). Raw args: %s",
                        tool_name,
                        tc_buf["args"][:200] if tc_buf["args"] else "(empty)",
                    )
                    continue

                full_tool_calls.append(
                    {
                        "name": tool_name,
                        "args": args,
                        "id": tool_call_id,
                    }
                )

                # Check mutating
                if self.agent._is_mutating_tool(tool_name):
                    yield StreamEvent(
                        type="approval_required",
                        tool=tool_name,
                        content=f"Approval needed: {tool_name}({args})",
                    )
                    tool_results[tool_call_id] = "Requires user approval"
                    continue

                yield StreamEvent(type="tool_start", tool=tool_name, agent="architect")

                tool = tool_lookup.get(tool_name)
                if tool:
                    # Determine timeout based on tool type
                    settings = get_settings()
                    timeout = (
                        settings.analysis_tool_timeout_seconds
                        if tool_name in ANALYSIS_TOOLS
                        else settings.tool_timeout_seconds
                    )

                    # Create progress queue and execution context
                    progress_queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()
                    async with execution_context(
                        progress_queue=progress_queue,
                        conversation_id=state.conversation_id,
                        tool_timeout=float(settings.tool_timeout_seconds),
                        analysis_timeout=float(settings.analysis_tool_timeout_seconds),
                    ):
                        # Run tool in background task
                        tool_task = asyncio.create_task(tool.ainvoke(args))

                        # Track deadline for timeout
                        import time as _time

                        deadline = _time.monotonic() + float(timeout)
                        timed_out = False

                        # Drain progress events while tool runs
                        try:
                            while not tool_task.done():
                                remaining = deadline - _time.monotonic()
                                if remaining <= 0:
                                    timed_out = True
                                    break
                                queue_get = asyncio.ensure_future(progress_queue.get())
                                done_set, _ = await asyncio.wait(
                                    {tool_task, queue_get},
                                    timeout=min(0.5, remaining),
                                    return_when=asyncio.FIRST_COMPLETED,
                                )
                                if queue_get in done_set:
                                    event = queue_get.result()
                                    yield StreamEvent(
                                        type=event.type,
                                        agent=event.agent,
                                        content=event.message,
                                        **({"target": event.target} if event.target else {}),  # type: ignore[arg-type]
                                    )
                                else:
                                    queue_get.cancel()

                            if timed_out:
                                tool_task.cancel()
                                with contextlib.suppress(asyncio.CancelledError, Exception):
                                    await tool_task
                                result_str = f"Error: Tool {tool_name} timed out after {timeout}s"
                                tool_results[tool_call_id] = result_str
                                yield StreamEvent(
                                    type="tool_end",
                                    tool=tool_name,
                                    result=result_str,
                                )
                            else:
                                # Drain any remaining events after tool completes
                                while not progress_queue.empty():
                                    event = progress_queue.get_nowait()
                                    yield StreamEvent(
                                        type=event.type,
                                        agent=event.agent,
                                        content=event.message,
                                        **({"target": event.target} if event.target else {}),  # type: ignore[arg-type]
                                    )

                                # Collect result (tool is already done)
                                result = tool_task.result()
                                result_str = str(result)
                                tool_results[tool_call_id] = result_str
                                yield StreamEvent(
                                    type="tool_end",
                                    tool=tool_name,
                                    result=result_str[:500],
                                )

                                # Track successful proposal creations
                                if tool_name == "seek_approval" and (
                                    "submitted" in result_str.lower()
                                    or "proposal" in result_str.lower()
                                ):
                                    proposal_summaries.append(result_str)

                        except Exception as e:
                            if not tool_task.done():
                                tool_task.cancel()
                            result_str = f"Error: {e}"
                            tool_results[tool_call_id] = result_str
                            yield StreamEvent(
                                type="tool_end",
                                tool=tool_name,
                                result=result_str,
                            )
                else:
                    tool_results[tool_call_id] = f"Tool {tool_name} not found"

            # Build AI message with tool_calls + ToolMessages from cached results
            ai_msg = AIMessage(
                content=collected_content,
                tool_calls=full_tool_calls,
            )
            tool_messages_list = [
                ToolMessage(
                    content=tool_results.get(tc["id"], ""),
                    tool_call_id=tc.get("id", ""),
                )
                for tc in full_tool_calls
                if not self.agent._is_mutating_tool(tc["name"])
            ]

            all_new_messages.extend([ai_msg, *tool_messages_list])

            # Follow-up: stream using tool_llm (with tools bound) to allow chaining
            follow_up_messages = messages + all_new_messages
            collected_content = ""
            tool_calls_buffer = []

            async for chunk in tool_llm.astream(follow_up_messages):
                has_tool_chunks = hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks

                if chunk.content and not has_tool_chunks:
                    token = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    collected_content += token
                    yield StreamEvent(type="token", content=token)

                if has_tool_chunks:
                    tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []
                    for tc_chunk in tool_call_chunks:
                        idx = tc_chunk.get("index", 0)
                        while len(tool_calls_buffer) <= idx:
                            tool_calls_buffer.append({"name": "", "args": "", "id": ""})
                        buf = tool_calls_buffer[idx]
                        if tc_chunk.get("name"):
                            buf["name"] = tc_chunk["name"]
                        if tc_chunk.get("args"):
                            buf["args"] += tc_chunk["args"]
                        if tc_chunk.get("id"):
                            buf["id"] = tc_chunk["id"]

            # If no more tool calls, this was the final response — append & exit
            if not tool_calls_buffer:
                if collected_content:
                    all_new_messages.append(AIMessage(content=collected_content))
                break

        # If the while loop never ran (no initial tool calls)
        if iteration == 0 and collected_content:
            all_new_messages.append(AIMessage(content=collected_content))

        # Fallback: if no visible text was streamed but proposals were created,
        # emit the seek_approval results so the user sees something in the chat.
        # This handles the case where the LLM only generated tool calls and the
        # follow-up response was empty or truncated.
        if not collected_content and proposal_summaries:
            fallback = "\n\n---\n\n".join(proposal_summaries)
            collected_content = fallback
            yield StreamEvent(type="token", content=fallback)
            all_new_messages.append(AIMessage(content=fallback))
        elif not collected_content and iteration > 0:
            # Tool calls were made but produced no proposals and no text.
            # Emit a minimal fallback so the user isn't left with an empty chat.
            fallback = (
                "I processed your request using several tools but wasn't able to "
                "generate a complete response. Please try rephrasing or breaking "
                "your request into smaller steps."
            )
            collected_content = fallback
            yield StreamEvent(type="token", content=fallback)
            all_new_messages.append(AIMessage(content=fallback))

        # Fallback proposal extraction: if the LLM wrote proposals inline
        # (as ```json blocks) instead of using seek_approval, and no proposals
        # were created via tools, extract and persist them now.
        if session and collected_content and not proposal_summaries:
            inline_proposals = self.agent._extract_proposals(collected_content)
            for prop_data in inline_proposals:
                try:
                    proposal = await self.agent._create_proposal(
                        session,
                        state.conversation_id,
                        prop_data,
                    )
                    logger.info(
                        "Created inline proposal %s from streamed content",
                        proposal.id,
                    )
                except Exception as e:
                    logger.warning("Failed to create inline proposal: %s", e)

        state.messages.extend(all_new_messages)  # type: ignore[arg-type]

        # Yield final state
        yield StreamEvent(type="state", state=state)


class StreamEvent(dict[str, Any]):
    """A typed dict for streaming events from the workflow.

    Attributes:
        type: Event type (token, tool_start, tool_end, state, approval_required)
        content: Text content (for token events)
        tool: Tool name (for tool events)
        agent: Agent name (for tool events)
        result: Tool result (for tool_end events)
        state: Final conversation state (for state events)
    """

    def __init__(
        self,
        type: str,
        content: str | None = None,
        tool: str | None = None,
        agent: str | None = None,
        result: str | None = None,
        state: ConversationState | None = None,
        **kwargs: object,
    ):
        super().__init__(
            type=type,
            content=content,
            tool=tool,
            agent=agent,
            result=result,
            state=state,
            **kwargs,
        )


# Exports
__all__ = [
    "ArchitectAgent",
    "ArchitectWorkflow",
    "StreamEvent",
]
