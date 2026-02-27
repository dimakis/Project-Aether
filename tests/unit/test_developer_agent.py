"""Unit tests for the Developer agent.

T093: Tests for DeveloperAgent deployment logic.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDeveloperAgent:
    """Test DeveloperAgent functionality."""

    @pytest.fixture
    def mock_ha_client(self):
        """Create mock HA client."""
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
        proposal.created_at = datetime.now(UTC)
        proposal.approved_by = "user"
        proposal.to_ha_yaml_dict = MagicMock(
            return_value={
                "alias": "Test Automation",
                "trigger": [{"platform": "time", "at": "08:00"}],
                "action": [{"service": "light.turn_on"}],
                "mode": "single",
            }
        )
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
    async def test_deploy_automation(self, mock_ha_client, mock_proposal):
        """Test automation deployment."""
        from src.agents.developer import DeveloperAgent

        mock_deployer = AsyncMock()
        mock_deployer.deploy_automation = AsyncMock(
            return_value={"success": True, "method": "rest_api"}
        )

        with (
            patch.object(DeveloperAgent, "ha", mock_ha_client),
            patch("src.agents.developer.AutomationDeployer", return_value=mock_deployer),
        ):
            agent = DeveloperAgent(ha_client=mock_ha_client)

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
    async def test_enable_automation(self, mock_ha_client):
        """Test enabling an automation."""
        from src.agents.developer import DeveloperAgent

        agent = DeveloperAgent(ha_client=mock_ha_client)
        result = await agent.enable_automation("automation.test_auto")

        assert result["enabled"] is True
        mock_ha_client.call_service.assert_called_once_with(
            domain="automation",
            service="turn_on",
            data={"entity_id": "automation.test_auto"},
        )

    @pytest.mark.asyncio
    async def test_disable_automation(self, mock_ha_client):
        """Test disabling an automation."""
        from src.agents.developer import DeveloperAgent

        agent = DeveloperAgent(ha_client=mock_ha_client)
        result = await agent.disable_automation("automation.test_auto")

        assert result["disabled"] is True
        mock_ha_client.call_service.assert_called_once_with(
            domain="automation",
            service="turn_off",
            data={"entity_id": "automation.test_auto"},
        )

    @pytest.mark.asyncio
    async def test_trigger_automation(self, mock_ha_client):
        """Test triggering an automation."""
        from src.agents.developer import DeveloperAgent

        agent = DeveloperAgent(ha_client=mock_ha_client)
        result = await agent.trigger_automation("automation.test_auto")

        assert result["triggered"] is True
        mock_ha_client.call_service.assert_called_once_with(
            domain="automation",
            service="trigger",
            data={"entity_id": "automation.test_auto"},
        )

    @pytest.mark.asyncio
    async def test_rollback_automation(self, mock_ha_client):
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
            agent = DeveloperAgent(ha_client=mock_ha_client)
            result = await agent.rollback_automation("test-id", mock_session)

        assert result["rolled_back"] is True
        assert result["ha_disabled"] is True
        mock_repo.rollback.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_rollback_reports_ha_disable_failure(self, mock_ha_client):
        """Test that rollback reports when HA disable fails instead of silently swallowing."""
        from src.agents.developer import DeveloperAgent
        from src.storage.entities import ProposalStatus

        mock_ha_client.call_service = AsyncMock(side_effect=Exception("HA connection refused"))

        mock_proposal = MagicMock()
        mock_proposal.id = "test-id"
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal.ha_automation_id = "test_auto"
        mock_proposal.previous_config = None
        mock_proposal.proposal_type = "automation"

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_repo.rollback = AsyncMock()

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            agent = DeveloperAgent(ha_client=mock_ha_client)
            result = await agent.rollback_automation("test-id", mock_session)

        # Should still mark as rolled back in DB but report HA failure
        assert result["rolled_back"] is True
        assert result["ha_disabled"] is False
        assert "ha_error" in result
        assert "HA connection refused" in result["ha_error"]
        mock_repo.rollback.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_rollback_uses_correct_entity_id_format(self, mock_ha_client):
        """Test that rollback uses automation.{id} entity_id format correctly."""
        from src.agents.developer import DeveloperAgent
        from src.storage.entities import ProposalStatus

        mock_proposal = MagicMock()
        mock_proposal.id = "test-id"
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal.ha_automation_id = "aether_abc12345"
        mock_proposal.previous_config = None
        mock_proposal.proposal_type = "automation"

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_repo.rollback = AsyncMock()

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            agent = DeveloperAgent(ha_client=mock_ha_client)
            await agent.rollback_automation("test-id", mock_session)

        # Should call with automation.{ha_automation_id}
        mock_ha_client.call_service.assert_called_once_with(
            domain="automation",
            service="turn_off",
            data={"entity_id": "automation.aether_abc12345"},
        )

    @pytest.mark.asyncio
    async def test_rollback_without_ha_automation_id(self, mock_ha_client):
        """Test rollback when no HA automation ID exists (never deployed to HA)."""
        from src.agents.developer import DeveloperAgent
        from src.storage.entities import ProposalStatus

        mock_proposal = MagicMock()
        mock_proposal.id = "test-id"
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal.ha_automation_id = None
        mock_proposal.previous_config = None
        mock_proposal.proposal_type = "automation"

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_repo.rollback = AsyncMock()

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            agent = DeveloperAgent(ha_client=mock_ha_client)
            result = await agent.rollback_automation("test-id", mock_session)

        assert result["rolled_back"] is True
        assert result["ha_disabled"] is False
        assert "ha_error" not in result
        # Should NOT have called HA
        mock_ha_client.call_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_rollback_dashboard_restores_previous_config(self, mock_ha_client):
        """Rollback of a dashboard proposal should restore previous_dashboard_config via HA."""
        from src.agents.developer import DeveloperAgent
        from src.storage.entities import ProposalStatus, ProposalType

        previous_config = {"views": [{"title": "Original Home", "cards": [{"type": "entities"}]}]}
        mock_proposal = MagicMock()
        mock_proposal.id = "dash-rollback-id"
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal.proposal_type = ProposalType.DASHBOARD.value
        mock_proposal.previous_dashboard_config = previous_config
        mock_proposal.service_call = {"url_path": "my-dash"}
        mock_proposal.ha_automation_id = "dash_abc12345_my-dash"

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_repo.rollback = AsyncMock()

        mock_ha_client.save_dashboard_config = AsyncMock()

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            agent = DeveloperAgent(ha_client=mock_ha_client)
            result = await agent.rollback_automation("dash-rollback-id", mock_session)

        assert result["rolled_back"] is True
        assert result["ha_disabled"] is True
        mock_ha_client.save_dashboard_config.assert_called_once_with("my-dash", previous_config)
        # Should NOT try to disable an automation
        mock_ha_client.call_service.assert_not_called()
        mock_repo.rollback.assert_called_once_with("dash-rollback-id")

    @pytest.mark.asyncio
    async def test_rollback_dashboard_no_previous_config(self, mock_ha_client):
        """Rollback of a dashboard with no previous config should mark rolled back but report no restore."""
        from src.agents.developer import DeveloperAgent
        from src.storage.entities import ProposalStatus, ProposalType

        mock_proposal = MagicMock()
        mock_proposal.id = "dash-no-prev"
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal.proposal_type = ProposalType.DASHBOARD.value
        mock_proposal.previous_dashboard_config = None
        mock_proposal.service_call = {"url_path": None}
        mock_proposal.ha_automation_id = "dash_abc12345_default"

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_repo.rollback = AsyncMock()

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            agent = DeveloperAgent(ha_client=mock_ha_client)
            result = await agent.rollback_automation("dash-no-prev", mock_session)

        assert result["rolled_back"] is True
        assert result["ha_disabled"] is False
        assert "no previous" in result.get("note", "").lower()
        mock_ha_client.save_dashboard_config.assert_not_called()
        mock_repo.rollback.assert_called_once_with("dash-no-prev")

    @pytest.mark.asyncio
    async def test_rollback_dashboard_default_url_path(self, mock_ha_client):
        """Rollback dashboard with url_path=None (default dashboard) should pass None to HA."""
        from src.agents.developer import DeveloperAgent
        from src.storage.entities import ProposalStatus, ProposalType

        previous_config = {"views": [{"title": "Default Home"}]}
        mock_proposal = MagicMock()
        mock_proposal.id = "dash-default"
        mock_proposal.status = ProposalStatus.DEPLOYED
        mock_proposal.proposal_type = ProposalType.DASHBOARD.value
        mock_proposal.previous_dashboard_config = previous_config
        mock_proposal.service_call = {"url_path": None}
        mock_proposal.ha_automation_id = "dash_abc12345_default"

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_proposal)
        mock_repo.rollback = AsyncMock()

        mock_ha_client.save_dashboard_config = AsyncMock()

        with patch("src.agents.developer.ProposalRepository", return_value=mock_repo):
            agent = DeveloperAgent(ha_client=mock_ha_client)
            result = await agent.rollback_automation("dash-default", mock_session)

        assert result["rolled_back"] is True
        mock_ha_client.save_dashboard_config.assert_called_once_with(None, previous_config)


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
