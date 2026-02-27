"""Developer agent for automation deployment.

The Developer takes approved automation proposals and deploys them
to Home Assistant, handling YAML generation and service calls.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import yaml

from src.agents.base import BaseAgent
from src.dal import ProposalRepository
from src.graph.state import AgentRole, ConversationState, ConversationStatus
from src.ha import HAClient, get_ha_client
from src.ha.automation_deploy import AutomationDeployer
from src.storage.entities import AutomationProposal, ProposalStatus, ProposalType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DeveloperAgent(BaseAgent):
    """The Developer agent for automation deployment.

    Responsibilities:
    - Convert approved proposals to HA automation format
    - Deploy automations via HA REST API (call_service)
    - Handle rollbacks when requested
    - Track deployment status
    """

    def __init__(
        self,
        ha_client: HAClient | None = None,
    ):
        """Initialize Developer agent.

        Args:
            ha_client: Optional HA client (creates one if not provided)
        """
        super().__init__(
            role=AgentRole.DEVELOPER,
            name="Developer",
        )
        self._ha_client = ha_client

    @property
    def ha(self) -> HAClient:
        """Get HA client, creating if needed."""
        if self._ha_client is None:
            self._ha_client = get_ha_client()
        return self._ha_client

    async def invoke(
        self,
        state: ConversationState,
        **kwargs: object,
    ) -> dict[str, object]:
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
            repo = ProposalRepository(cast("AsyncSession", session))
            proposal = await repo.get_by_id(cast("str", proposal_id))

            if not proposal:
                return {"error": f"Proposal {proposal_id} not found"}

            if proposal.status != ProposalStatus.APPROVED:
                return {
                    "error": f"Proposal must be approved before deployment (status: {proposal.status.value})"
                }

            try:
                result = await self.deploy_automation(proposal, cast("AsyncSession", session))
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
        proposal: AutomationProposal,
        session: AsyncSession,
    ) -> dict[str, object]:
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

        # Snapshot existing config before overwriting (for rollback)
        await self._snapshot_existing_config(proposal, ha_automation_id)

        # Deploy via HA REST API (with fallback to manual instructions)
        result = await self._deploy_via_ha(ha_automation_id, automation_yaml)

        # Only mark as deployed if the REST API call succeeded
        if result.get("success"):
            repo = ProposalRepository(session)
            await repo.deploy(proposal.id, ha_automation_id)

            return {
                "ha_automation_id": ha_automation_id,
                "yaml_content": automation_yaml,
                "deployment_method": result.get("method", "rest_api"),
                "deployed_at": datetime.now(UTC).isoformat(),
            }

        # Deployment failed -- return error info without changing proposal status
        errors_list = cast("list[str]", result.get("errors", []))
        error_msg = cast("str | None", result.get("error")) or ", ".join(errors_list)
        return {
            "ha_automation_id": None,
            "yaml_content": automation_yaml,
            "deployment_method": result.get("method", "failed"),
            "instructions": result.get("instructions"),
            "error": error_msg,
        }

    def _generate_automation_yaml(self, proposal: AutomationProposal) -> str:
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
# Created: {proposal.created_at.isoformat() if proposal.created_at else "unknown"}
# Approved by: {proposal.approved_by or "unknown"}
# ---
"""
        return header + yaml_str

    async def _snapshot_existing_config(
        self,
        proposal: AutomationProposal,
        ha_automation_id: str,
    ) -> None:
        """Snapshot the existing HA automation config before overwriting.

        If the automation already exists in HA, its current config is
        stored in ``proposal.previous_config`` so rollback can restore
        it instead of just disabling.
        """
        try:
            config = await self.ha._request(
                "GET", f"/api/config/automation/config/{ha_automation_id}"
            )
            if config and isinstance(config, dict):
                proposal.previous_config = config
                logger.info(
                    "Snapshot: saved existing config for automation.%s",
                    ha_automation_id,
                )
        except Exception:
            logger.debug(
                "No existing config to snapshot for automation.%s (new automation)",
                ha_automation_id,
            )

    async def _deploy_via_ha(
        self,
        automation_id: str,
        yaml_content: str,
    ) -> dict[str, object]:
        """Deploy automation via HA REST API.

        Uses AutomationDeployer which calls the HA config API
        (POST /api/config/automation/config/{id}) to create
        automations directly. Falls back to manual instructions
        if the REST API call fails.

        Args:
            automation_id: Unique automation ID
            yaml_content: Automation YAML

        Returns:
            Deployment result
        """
        deployer = AutomationDeployer(self.ha)
        return await deployer.deploy_automation(yaml_content, automation_id)

    async def rollback_automation(
        self,
        proposal_id: str,
        session: AsyncSession,
    ) -> dict[str, object]:
        """Rollback a deployed proposal.

        For automation proposals: disables the automation in Home Assistant.
        For dashboard proposals: restores the previous Lovelace config if available.

        Updates the proposal status to ROLLED_BACK in all cases.

        Args:
            proposal_id: ID of proposal to rollback
            session: Database session

        Returns:
            Rollback result with ha_disabled flag and optional ha_error
        """
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            return {"error": f"Proposal {proposal_id} not found"}

        if proposal.status != ProposalStatus.DEPLOYED:
            return {
                "error": f"Can only rollback deployed proposals (status: {proposal.status.value})"
            }

        # Dashboard proposals: restore previous config
        if proposal.proposal_type == ProposalType.DASHBOARD.value:
            return await self._rollback_dashboard(proposal, proposal_id, repo)

        # Automation / other proposals: disable via HA service call
        return await self._rollback_automation_entity(proposal, proposal_id, repo)

    async def _rollback_dashboard(
        self,
        proposal: AutomationProposal,
        proposal_id: str,
        repo: ProposalRepository,
    ) -> dict[str, object]:
        """Restore the previous dashboard config from the pre-deploy snapshot."""
        ha_disabled = False
        ha_error: str | None = None

        previous = proposal.previous_dashboard_config
        if previous is not None:
            url_path = (proposal.service_call or {}).get("url_path")
            try:
                await self.ha.save_dashboard_config(url_path, previous)
                ha_disabled = True
                logger.info(
                    "Rollback: restored previous dashboard config for '%s' (proposal %s)",
                    url_path or "default",
                    proposal_id,
                )
            except Exception as exc:
                ha_error = str(exc)
                logger.warning(
                    "Rollback: failed to restore dashboard '%s' for proposal %s: %s",
                    url_path or "default",
                    proposal_id,
                    exc,
                )

        await repo.rollback(proposal_id)

        note = (
            "Previous dashboard config restored."
            if ha_disabled
            else "Dashboard rolled back in DB. No previous config available to restore."
        )
        result: dict[str, object] = {
            "rolled_back": True,
            "ha_disabled": ha_disabled,
            "ha_automation_id": proposal.ha_automation_id,
            "rolled_back_at": datetime.now(UTC).isoformat(),
            "note": note,
        }
        if ha_error:
            result["ha_error"] = ha_error
        return result

    async def _rollback_automation_entity(
        self,
        proposal: AutomationProposal,
        proposal_id: str,
        repo: ProposalRepository,
    ) -> dict[str, object]:
        """Rollback an automation/script/scene in Home Assistant.

        If ``previous_config`` was snapshotted before deployment, restores
        the original config.  Otherwise falls back to disabling the entity.
        """
        ha_automation_id = proposal.ha_automation_id
        ha_restored = False
        ha_disabled = False
        ha_error: str | None = None

        if ha_automation_id:
            # Try to restore previous config first (full rollback)
            if proposal.previous_config:
                try:
                    deployer = AutomationDeployer(self.ha)
                    yaml_str = yaml.dump(
                        proposal.previous_config,
                        default_flow_style=False,
                        sort_keys=False,
                    )
                    result = await deployer.deploy_automation(yaml_str, ha_automation_id)
                    if result.get("success"):
                        ha_restored = True
                        logger.info(
                            "Rollback: restored previous config for automation.%s (proposal %s)",
                            ha_automation_id,
                            proposal_id,
                        )
                except Exception as exc:
                    ha_error = f"Restore failed: {exc}"
                    logger.warning(
                        "Rollback: failed to restore config for automation.%s, "
                        "falling back to disable: %s",
                        ha_automation_id,
                        exc,
                    )

            # Fallback: disable if restore failed or no snapshot available
            if not ha_restored:
                entity_id = f"automation.{ha_automation_id}"
                try:
                    await self.ha.call_service(
                        domain="automation",
                        service="turn_off",
                        data={"entity_id": entity_id},
                    )
                    ha_disabled = True
                    logger.info(
                        "Rollback: disabled HA automation %s for proposal %s",
                        entity_id,
                        proposal_id,
                    )
                except Exception as exc:
                    if not ha_error:
                        ha_error = str(exc)
                    logger.warning(
                        "Rollback: failed to disable HA automation %s: %s",
                        entity_id,
                        exc,
                    )

        await repo.rollback(proposal_id)

        if ha_restored:
            note = "Previous automation config restored."
        elif ha_disabled:
            note = "Automation disabled (no previous config available to restore)."
        else:
            note = "Rolled back in DB. HA entity may need manual cleanup."

        result_dict: dict[str, object] = {
            "rolled_back": True,
            "ha_restored": ha_restored,
            "ha_disabled": ha_disabled,
            "ha_automation_id": ha_automation_id,
            "rolled_back_at": datetime.now(UTC).isoformat(),
            "note": note,
        }
        if ha_error:
            result_dict["ha_error"] = ha_error
        return result_dict

    async def enable_automation(self, ha_automation_id: str) -> dict[str, Any]:
        """Enable a deployed automation.

        Args:
            ha_automation_id: Home Assistant automation ID (full entity_id)

        Returns:
            Result dict
        """
        await self.ha.call_service(
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
        await self.ha.call_service(
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
        await self.ha.call_service(
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

    def __init__(self, ha_client: HAClient | None = None):
        """Initialize the Developer workflow.

        Args:
            ha_client: Optional HA client
        """
        self.agent = DeveloperAgent(ha_client)

    async def deploy(
        self,
        proposal_id: str,
        session: AsyncSession,
    ) -> dict[str, object]:
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
                f"Cannot deploy proposal in status {proposal.status.value}. Must be approved first."
            )

        return await self.agent.deploy_automation(proposal, session)

    async def rollback(
        self,
        proposal_id: str,
        session: AsyncSession,
    ) -> dict[str, object]:
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
