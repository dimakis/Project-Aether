"""E2E tests for automation rollback workflow.

T100: Deploy and rollback flow tests.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestAutomationDeployment:
    """Test automation deployment flow."""

    @pytest.mark.asyncio
    async def test_proposal_deployment_state_transitions(self):
        """Test state transitions during deployment."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Deploy Test",
            trigger={"platform": "time", "at": "12:00"},
            actions=[{"service": "light.turn_on"}],
            mode="single",
            status=ProposalStatus.DRAFT,
        )

        # Proposal flow: DRAFT → PROPOSED → APPROVED → DEPLOYED
        proposal.propose()
        assert proposal.status == ProposalStatus.PROPOSED

        proposal.approve(approved_by="admin")
        assert proposal.status == ProposalStatus.APPROVED

        proposal.deploy(ha_automation_id="automation.aether_deploy_test")
        assert proposal.status == ProposalStatus.DEPLOYED
        assert proposal.ha_automation_id == "automation.aether_deploy_test"
        assert proposal.deployed_at is not None

    @pytest.mark.asyncio
    async def test_deployment_yaml_generation(self):
        """Test YAML generation for deployment."""
        from src.ha.automation_deploy import AutomationDeployer

        deployer = AutomationDeployer()
        yaml_content = deployer.generate_automation_yaml(
            name="YAML Test",
            description="Test automation",
            trigger={"platform": "sun", "event": "sunrise"},
            actions=[
                {
                    "service": "light.turn_off",
                    "target": {"entity_id": "light.bedroom"},
                }
            ],
            mode="single",
        )

        assert "alias: YAML Test" in yaml_content
        assert "platform: sun" in yaml_content
        assert "event: sunrise" in yaml_content
        assert "service: light.turn_off" in yaml_content
        assert "mode: single" in yaml_content


class TestAutomationRollback:
    """Test automation rollback flow."""

    @pytest.mark.asyncio
    async def test_rollback_state_transition(self):
        """Test rollback state transition."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Rollback Test",
            trigger={"platform": "time"},
            actions=[{}],
            mode="single",
            status=ProposalStatus.DEPLOYED,
            ha_automation_id="automation.test",
            deployed_at=datetime.now(timezone.utc),
        )

        # Rollback deployed automation
        proposal.rollback()

        assert proposal.status == ProposalStatus.ROLLED_BACK
        assert proposal.rolled_back_at is not None

    @pytest.mark.asyncio
    async def test_rollback_requires_deployed_state(self):
        """Test rollback only works from DEPLOYED state."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        # Try to rollback from DRAFT - should fail
        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Bad Rollback",
            trigger={"platform": "time"},
            actions=[{}],
            mode="single",
            status=ProposalStatus.DRAFT,
        )

        # Rollback from DRAFT should raise error
        with pytest.raises((ValueError, Exception)):
            proposal.rollback()

    @pytest.mark.asyncio
    async def test_cannot_rollback_rejected_proposal(self):
        """Test cannot rollback rejected proposal."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Rejected Proposal",
            trigger={"platform": "time"},
            actions=[{}],
            mode="single",
            status=ProposalStatus.REJECTED,
            rejection_reason="Test",
        )

        # Cannot rollback rejected proposal
        with pytest.raises((ValueError, Exception)):
            proposal.rollback()


class TestDeploymentAgent:
    """Test developer agent deployment operations."""

    @pytest.mark.asyncio
    async def test_developer_agent_init(self):
        """Test developer agent initialization."""
        from src.agents.developer import DeveloperAgent

        mock_mcp = MagicMock()

        with patch("src.agents.developer.get_ha_client", return_value=mock_mcp):
            agent = DeveloperAgent(ha_client=mock_mcp)
            assert agent is not None

    @pytest.mark.asyncio
    async def test_developer_agent_enable_disable(self):
        """Test enabling/disabling deployed automation."""
        from src.agents.developer import DeveloperAgent

        mock_mcp = MagicMock()
        mock_mcp.call_service = AsyncMock(return_value={"success": True})

        with patch("src.agents.developer.get_ha_client", return_value=mock_mcp):
            agent = DeveloperAgent(ha_client=mock_mcp)

            # Enable
            await agent.enable_automation("automation.test")
            mock_mcp.call_service.assert_called_with(
                domain="automation",
                service="turn_on",
                data={"entity_id": "automation.test"},
            )

            # Disable
            await agent.disable_automation("automation.test")
            mock_mcp.call_service.assert_called_with(
                domain="automation",
                service="turn_off",
                data={"entity_id": "automation.test"},
            )


class TestRollbackEndToEnd:
    """E2E rollback scenarios."""

    @pytest.mark.asyncio
    async def test_full_deploy_and_rollback_cycle(self):
        """Test complete deploy → rollback cycle."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Full Cycle Test",
            description="Testing full deployment cycle",
            trigger={"platform": "state", "entity_id": "binary_sensor.motion"},
            conditions=[{"condition": "time", "after": "18:00"}],
            actions=[{"service": "light.turn_on", "target": {"area_id": "living_room"}}],
            mode="single",
            status=ProposalStatus.DRAFT,
        )

        # Full lifecycle
        proposal.propose()
        proposal.approve(approved_by="admin")
        proposal.deploy(ha_automation_id="automation.aether_test")

        # Verify deployed state
        assert proposal.status == ProposalStatus.DEPLOYED
        assert proposal.ha_automation_id == "automation.aether_test"

        # Rollback
        proposal.rollback()

        # Verify rolled back
        assert proposal.status == ProposalStatus.ROLLED_BACK
        assert proposal.rolled_back_at is not None

    @pytest.mark.asyncio
    async def test_archive_after_rollback(self):
        """Test archiving after rollback."""
        from src.storage.entities import AutomationProposal, ProposalStatus

        proposal = AutomationProposal(
            id=str(uuid4()),
            name="Archive Test",
            trigger={"platform": "time"},
            actions=[{}],
            mode="single",
            status=ProposalStatus.ROLLED_BACK,
            rolled_back_at=datetime.now(timezone.utc),
        )

        # Archive the rolled-back proposal
        proposal.archive()

        assert proposal.status == ProposalStatus.ARCHIVED
