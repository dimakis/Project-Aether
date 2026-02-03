"""Unit tests for the Developer agent.

T093: Tests for DeveloperAgent deployment logic.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDeveloperAgent:
    """Test DeveloperAgent functionality."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = MagicMock()
        client.call_service = AsyncMock(return_value={})
        return client

    @pytest.fixture
    def mock_proposal(self):
        """Create mock proposal."""
        from src.storage.entities import ProposalStatus

        proposal = MagicMock()
        proposal.id = "test-proposal-id"
        proposal.name = "Test Automation"
        proposal.description = "Test description"
        proposal.trigger = {"platform": "time", "at": "08:00"}
        proposal.conditions = None
        proposal.actions = {"service": "light.turn_on"}
        proposal.mode = "single"
        proposal.status = ProposalStatus.APPROVED
        proposal.ha_automation_id = None
        proposal.created_at = datetime.utcnow()
        proposal.approved_by = "user"
        proposal.to_ha_yaml_dict = MagicMock(return_value={
            "alias": "Test Automation",
            "trigger": [{"platform": "time", "at": "08:00"}],
            "action": [{"service": "light.turn_on"}],
            "mode": "single",
        })
        return proposal

    @pytest.mark.asyncio
    async def test_generate_automation_yaml(self, mock_proposal):
        """Test YAML generation from proposal."""
        from src.agents.developer import DeveloperAgent

        agent = DeveloperAgent()
        yaml_content = agent._generate_automation_yaml(mock_proposal)

        assert "# Automation created by Project Aether" in yaml_content
        assert "Proposal ID:" in yaml_content
        assert "alias: Test Automation" in yaml_content

    @pytest.mark.asyncio
    async def test_deploy_automation(self, mock_mcp_client, mock_proposal):
        """Test automation deployment."""
        from src.agents.developer import DeveloperAgent

        with patch.object(DeveloperAgent, "mcp", mock_mcp_client):
            agent = DeveloperAgent(mcp_client=mock_mcp_client)

            # Mock session and repo
            mock_session = MagicMock()
            mock_repo = MagicMock()
            mock_repo.deploy = AsyncMock()

            with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
                result = await agent.deploy_automation(mock_proposal, mock_session)

            assert result is not None
            assert "ha_automation_id" in result
            assert result["ha_automation_id"].startswith("aether_")
            assert "yaml_content" in result

    @pytest.mark.asyncio
    async def test_enable_automation(self, mock_mcp_client):
        """Test enabling an automation."""
        from src.agents.developer import DeveloperAgent

        agent = DeveloperAgent(mcp_client=mock_mcp_client)
        result = await agent.enable_automation("automation.test_auto")

        assert result["enabled"] is True
        mock_mcp_client.call_service.assert_called_once_with(
            domain="automation",
            service="turn_on",
            data={"entity_id": "automation.test_auto"},
        )

    @pytest.mark.asyncio
    async def test_disable_automation(self, mock_mcp_client):
        """Test disabling an automation."""
        from src.agents.developer import DeveloperAgent

        agent = DeveloperAgent(mcp_client=mock_mcp_client)
        result = await agent.disable_automation("automation.test_auto")

        assert result["disabled"] is True
        mock_mcp_client.call_service.assert_called_once_with(
            domain="automation",
            service="turn_off",
            data={"entity_id": "automation.test_auto"},
        )

    @pytest.mark.asyncio
    async def test_trigger_automation(self, mock_mcp_client):
        """Test triggering an automation."""
        from src.agents.developer import DeveloperAgent

        agent = DeveloperAgent(mcp_client=mock_mcp_client)
        result = await agent.trigger_automation("automation.test_auto")

        assert result["triggered"] is True
        mock_mcp_client.call_service.assert_called_once_with(
            domain="automation",
            service="trigger",
            data={"entity_id": "automation.test_auto"},
        )

    @pytest.mark.asyncio
    async def test_rollback_automation(self, mock_mcp_client):
        """Test rolling back an automation."""
        from src.agents.developer import DeveloperAgent
        from src.storage.entities import ProposalStatus

        mock_proposal = MagicMock()
        mock_proposal.id = "test-id"
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal.ha_automation_id = "test_auto"

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_repo.rollback = AsyncMock()

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            agent = DeveloperAgent(mcp_client=mock_mcp_client)
            result = await agent.rollback_automation("test-id", mock_session)

        assert result["rolled_back"] is True
        mock_repo.rollback.assert_called_once_with("test-id")


class TestDeveloperWorkflow:
    """Test DeveloperWorkflow functionality."""

    @pytest.mark.asyncio
    async def test_deploy_requires_approved_status(self):
        """Test that deployment requires approved status."""
        from src.agents.developer import DeveloperWorkflow
        from src.storage.entities import ProposalStatus

        mock_proposal = MagicMock()
        mock_proposal.id = "test-id"
        mock_proposal.status = ProposalStatus.PROPOSED

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_proposal)

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            workflow = DeveloperWorkflow()

            with pytest.raises(ValueError, match="approved"):
                await workflow.deploy("test-id", mock_session)

    @pytest.mark.asyncio
    async def test_deploy_proposal_not_found(self):
        """Test deployment with non-existent proposal."""
        from src.agents.developer import DeveloperWorkflow

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            workflow = DeveloperWorkflow()

            with pytest.raises(ValueError, match="not found"):
                await workflow.deploy("non-existent", mock_session)
