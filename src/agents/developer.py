"""Developer agent for automation deployment.

The Developer takes approved automation proposals and deploys them
to Home Assistant, handling YAML generation and service calls.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

import yaml

from src.agents import BaseAgent
from src.dal import ProposalRepository
from src.graph.state import AgentRole, ConversationState, ConversationStatus
from src.mcp import MCPClient, get_mcp_client
from src.settings import get_settings
from src.storage.entities import ProposalStatus


class DeveloperAgent(BaseAgent):
    """The Developer agent for automation deployment.

    Responsibilities:
    - Convert approved proposals to HA automation format
    - Deploy automations via MCP (call_service)
    - Handle rollbacks when requested
    - Track deployment status
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize Developer agent.

        Args:
            mcp_client: Optional MCP client (creates one if not provided)
        """
        super().__init__(
            role=AgentRole.DEVELOPER,
            name="Developer",
        )
        self._mcp = mcp_client

    @property
    def mcp(self) -> MCPClient:
        """Get MCP client, creating if needed."""
        if self._mcp is None:
            self._mcp = get_mcp_client()
        return self._mcp

    async def invoke(
        self,
        state: ConversationState,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Deploy approved automations.

        Args:
            state: Current conversation state
            **kwargs: Additional arguments (session, proposal_id)

        Returns:
            State updates with deployment results
        """
        async with self.trace_span("invoke", state) as span:
            session = kwargs.get("session")
            proposal_id = kwargs.get("proposal_id")

            if not session or not proposal_id:
                return {"error": "Session and proposal_id required for deployment"}

            # Get proposal
            repo = ProposalRepository(session)
            proposal = await repo.get_by_id(proposal_id)

            if not proposal:
                return {"error": f"Proposal {proposal_id} not found"}

            if proposal.status != ProposalStatus.APPROVED:
                return {"error": f"Proposal must be approved before deployment (status: {proposal.status.value})"}

            # Deploy
            try:
                result = await self.deploy_automation(proposal, session)
                span["deployment_success"] = True
                span["ha_automation_id"] = result.get("ha_automation_id")

                return {
                    "status": ConversationStatus.COMPLETED,
                    "developer_code": result.get("yaml_content"),
                    "deployment_result": result,
                }
            except Exception as e:
                span["deployment_success"] = False
                span["deployment_error"] = str(e)

                return {
                    "error": f"Deployment failed: {e}",
                }

    async def deploy_automation(
        self,
        proposal: Any,
        session: Any,
    ) -> dict[str, Any]:
        """Deploy an automation proposal to Home Assistant.

        Constitution: This should only be called after HITL approval.

        Args:
            proposal: Approved AutomationProposal
            session: Database session

        Returns:
            Deployment result dict
        """
        # Generate automation YAML
        automation_yaml = self._generate_automation_yaml(proposal)

        # Generate unique automation ID
        ha_automation_id = f"aether_{proposal.id.replace('-', '_')[:8]}"

        # Deploy via MCP
        # Note: Direct automation creation is a known MCP gap
        # Workaround: Generate YAML for manual import or use REST API
        result = await self._deploy_via_mcp(ha_automation_id, automation_yaml)

        # Update proposal status
        repo = ProposalRepository(session)
        await repo.deploy(proposal.id, ha_automation_id)

        return {
            "ha_automation_id": ha_automation_id,
            "yaml_content": automation_yaml,
            "deployment_method": result.get("method", "manual"),
            "deployed_at": datetime.utcnow().isoformat(),
        }

    def _generate_automation_yaml(self, proposal: Any) -> str:
        """Generate Home Assistant automation YAML.

        Args:
            proposal: AutomationProposal instance

        Returns:
            YAML string for automation
        """
        automation = proposal.to_ha_yaml_dict()

        # Add Aether metadata as comments
        yaml_str = yaml.dump(automation, default_flow_style=False, sort_keys=False)

        header = f"""# Automation created by Project Aether
# Proposal ID: {proposal.id}
# Created: {proposal.created_at.isoformat() if proposal.created_at else 'unknown'}
# Approved by: {proposal.approved_by or 'unknown'}
# ---
"""
        return header + yaml_str

    async def _deploy_via_mcp(
        self,
        automation_id: str,
        yaml_content: str,
    ) -> dict[str, Any]:
        """Attempt to deploy automation via MCP.

        Note: MCP Gap - No direct automation creation tool exists.
        This uses workarounds documented in the spec.

        Args:
            automation_id: Unique automation ID
            yaml_content: Automation YAML

        Returns:
            Deployment result
        """
        # Known MCP gap: No create_automation tool
        # Options:
        # 1. Generate YAML for manual import (safest)
        # 2. Use HA REST API if configured
        # 3. Write to HA config directory if accessible

        settings = get_settings()

        # For now, return manual method
        # Future: Add REST API or file-based deployment

        return {
            "method": "manual",
            "yaml_file": f"automations/{automation_id}.yaml",
            "instructions": (
                "Automation YAML generated. To deploy:\n"
                "1. Copy the YAML below to your HA automations.yaml\n"
                "2. Call Developer Settings > YAML > Reload Automations\n"
                "3. Or use 'automation.reload' service"
            ),
        }

    async def rollback_automation(
        self,
        proposal_id: str,
        session: Any,
    ) -> dict[str, Any]:
        """Rollback a deployed automation.

        Args:
            proposal_id: ID of proposal to rollback
            session: Database session

        Returns:
            Rollback result
        """
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            return {"error": f"Proposal {proposal_id} not found"}

        if proposal.status != ProposalStatus.DEPLOYED:
            return {"error": f"Can only rollback deployed proposals (status: {proposal.status.value})"}

        ha_automation_id = proposal.ha_automation_id

        # Attempt to disable/remove via MCP
        if ha_automation_id:
            try:
                # Try to turn off the automation
                await self.mcp.call_service(
                    domain="automation",
                    service="turn_off",
                    data={"entity_id": f"automation.{ha_automation_id}"},
                )
            except Exception:
                # Best effort - might not exist
                pass

        # Update status
        await repo.rollback(proposal_id)

        return {
            "rolled_back": True,
            "ha_automation_id": ha_automation_id,
            "rolled_back_at": datetime.utcnow().isoformat(),
            "note": "Automation disabled. Manual removal from automations.yaml may be needed.",
        }

    async def enable_automation(self, ha_automation_id: str) -> dict[str, Any]:
        """Enable a deployed automation.

        Args:
            ha_automation_id: Home Assistant automation ID (full entity_id)

        Returns:
            Result dict
        """
        await self.mcp.call_service(
            domain="automation",
            service="turn_on",
            data={"entity_id": ha_automation_id},
        )
        return {"enabled": True, "automation_id": ha_automation_id}

    async def disable_automation(self, ha_automation_id: str) -> dict[str, Any]:
        """Disable a deployed automation.

        Args:
            ha_automation_id: Home Assistant automation ID (full entity_id)

        Returns:
            Result dict
        """
        await self.mcp.call_service(
            domain="automation",
            service="turn_off",
            data={"entity_id": ha_automation_id},
        )
        return {"disabled": True, "automation_id": ha_automation_id}

    async def trigger_automation(self, ha_automation_id: str) -> dict[str, Any]:
        """Manually trigger an automation.

        Args:
            ha_automation_id: Home Assistant automation ID (full entity_id)

        Returns:
            Result dict
        """
        await self.mcp.call_service(
            domain="automation",
            service="trigger",
            data={"entity_id": ha_automation_id},
        )
        return {"triggered": True, "automation_id": ha_automation_id}


class DeveloperWorkflow:
    """Workflow implementation for the Developer agent.

    Handles the deployment lifecycle:
    1. Validate approved proposal
    2. Generate automation YAML
    3. Deploy to Home Assistant
    4. Handle rollbacks
    """

    def __init__(self, mcp_client: MCPClient | None = None):
        """Initialize the Developer workflow.

        Args:
            mcp_client: Optional MCP client
        """
        self.agent = DeveloperAgent(mcp_client)

    async def deploy(
        self,
        proposal_id: str,
        session: Any,
    ) -> dict[str, Any]:
        """Deploy an approved proposal.

        Args:
            proposal_id: ID of approved proposal
            session: Database session

        Returns:
            Deployment result
        """
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        if proposal.status != ProposalStatus.APPROVED:
            raise ValueError(
                f"Cannot deploy proposal in status {proposal.status.value}. "
                "Must be approved first."
            )

        return await self.agent.deploy_automation(proposal, session)

    async def rollback(
        self,
        proposal_id: str,
        session: Any,
    ) -> dict[str, Any]:
        """Rollback a deployed proposal.

        Args:
            proposal_id: ID of deployed proposal
            session: Database session

        Returns:
            Rollback result
        """
        return await self.agent.rollback_automation(proposal_id, session)


# Exports
__all__ = [
    "DeveloperAgent",
    "DeveloperWorkflow",
]
