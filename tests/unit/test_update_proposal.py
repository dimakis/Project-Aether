"""Unit tests for the update_proposal tool and ProposalRepository.update().

Tests in-place updating of proposals: field mutation, status guards,
re-proposal of rejected proposals, and validation.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dal.conversations import ProposalRepository
from src.storage.entities import ProposalStatus

# ═══════════════════════════════════════════════════════════════════════════════
# ProposalRepository.update()
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def proposal_repo(mock_session):
    """Create ProposalRepository with mock session."""
    return ProposalRepository(mock_session)


def _make_proposal(**overrides):
    """Create a mock proposal entity with sensible defaults."""
    proposal = MagicMock()
    proposal.id = overrides.get("id", str(uuid4()))
    proposal.name = overrides.get("name", "Test Automation")
    proposal.description = overrides.get("description", "A test proposal")
    proposal.trigger = overrides.get("trigger", {"platform": "sun", "event": "sunset"})
    proposal.actions = overrides.get("actions", [{"service": "light.turn_on"}])
    proposal.conditions = overrides.get("conditions")
    proposal.mode = overrides.get("mode", "single")
    proposal.status = overrides.get("status", ProposalStatus.PROPOSED)
    proposal.proposal_type = overrides.get("proposal_type", "automation")
    proposal.service_call = overrides.get("service_call")
    proposal.dashboard_config = overrides.get("dashboard_config")
    return proposal


class TestProposalRepositoryUpdate:
    """Tests for ProposalRepository.update()."""

    @pytest.mark.asyncio
    async def test_update_name_and_description(self, proposal_repo):
        """update() sets name and description on the entity."""
        proposal = _make_proposal()
        proposal_repo.get_by_id = AsyncMock(return_value=proposal)

        result = await proposal_repo.update(
            proposal.id,
            name="New Name",
            description="New description",
        )

        assert result is not None
        assert result.name == "New Name"
        assert result.description == "New description"

    @pytest.mark.asyncio
    async def test_update_trigger(self, proposal_repo):
        """update() sets trigger on the entity."""
        proposal = _make_proposal()
        proposal_repo.get_by_id = AsyncMock(return_value=proposal)

        new_trigger = {"platform": "state", "entity_id": "binary_sensor.motion"}
        result = await proposal_repo.update(proposal.id, trigger=new_trigger)

        assert result.trigger == new_trigger

    @pytest.mark.asyncio
    async def test_update_ignores_none_values(self, proposal_repo):
        """update() does not overwrite fields when value is None."""
        proposal = _make_proposal(name="Original", description="Original desc")
        proposal_repo.get_by_id = AsyncMock(return_value=proposal)

        result = await proposal_repo.update(proposal.id, name="Changed")

        assert result.name == "Changed"
        assert result.description == "Original desc"

    @pytest.mark.asyncio
    async def test_update_returns_none_for_missing_proposal(self, proposal_repo):
        """update() returns None if proposal doesn't exist."""
        proposal_repo.get_by_id = AsyncMock(return_value=None)

        result = await proposal_repo.update("nonexistent-id", name="X")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_flushes_session(self, proposal_repo, mock_session):
        """update() flushes the session after mutation."""
        proposal = _make_proposal()
        proposal_repo.get_by_id = AsyncMock(return_value=proposal)

        await proposal_repo.update(proposal.id, name="X")

        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_service_call(self, proposal_repo):
        """update() sets service_call on the entity."""
        proposal = _make_proposal(proposal_type="entity_command")
        proposal_repo.get_by_id = AsyncMock(return_value=proposal)

        new_sc = {"domain": "light", "service": "turn_off", "entity_id": "light.kitchen"}
        result = await proposal_repo.update(proposal.id, service_call=new_sc)

        assert result.service_call == new_sc

    @pytest.mark.asyncio
    async def test_update_dashboard_config(self, proposal_repo):
        """update() sets dashboard_config on the entity."""
        proposal = _make_proposal(proposal_type="dashboard")
        proposal_repo.get_by_id = AsyncMock(return_value=proposal)

        new_config = {"views": [{"title": "New"}]}
        result = await proposal_repo.update(proposal.id, dashboard_config=new_config)

        assert result.dashboard_config == new_config


# ═══════════════════════════════════════════════════════════════════════════════
# update_proposal tool
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_proposal():
    """Create a mock proposal for tool tests."""
    return _make_proposal()


@pytest.fixture
def mock_repo(mock_proposal):
    """Create a mock ProposalRepository."""
    repo = AsyncMock()
    repo.get_by_id.return_value = mock_proposal
    repo.update.return_value = mock_proposal
    repo.propose.return_value = mock_proposal
    return repo


@pytest.mark.asyncio
class TestUpdateProposalTool:
    """Tests for the update_proposal tool."""

    async def test_update_name_of_proposed_automation(self, mock_repo, mock_session, mock_proposal):
        """update_proposal updates name on a PROPOSED automation."""
        mock_proposal.status = ProposalStatus.PROPOSED

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            result = await update_proposal.ainvoke(
                {"proposal_id": mock_proposal.id, "name": "New Name"}
            )

        assert "updated" in result.lower()
        mock_repo.update.assert_called_once()
        call_kwargs = mock_repo.update.call_args.kwargs
        assert call_kwargs["name"] == "New Name"

    async def test_update_trigger_of_proposed_automation(
        self, mock_repo, mock_session, mock_proposal
    ):
        """update_proposal updates trigger on a PROPOSED automation."""
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal.proposal_type = "automation"
        new_trigger = {"platform": "sun", "event": "sunset"}

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            result = await update_proposal.ainvoke(
                {"proposal_id": mock_proposal.id, "trigger": new_trigger}
            )

        assert "updated" in result.lower()
        call_kwargs = mock_repo.update.call_args.kwargs
        assert call_kwargs["trigger"] == new_trigger

    async def test_rejected_proposal_is_reproposed(self, mock_repo, mock_session, mock_proposal):
        """Updating a REJECTED proposal re-submits it as PROPOSED."""
        mock_proposal.status = ProposalStatus.REJECTED

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            result = await update_proposal.ainvoke(
                {"proposal_id": mock_proposal.id, "name": "Fixed Name"}
            )

        assert "updated" in result.lower()
        mock_repo.propose.assert_called_once_with(mock_proposal.id)

    async def test_proposed_proposal_not_reproposed(self, mock_repo, mock_session, mock_proposal):
        """Updating a PROPOSED proposal does NOT call propose() again."""
        mock_proposal.status = ProposalStatus.PROPOSED

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            await update_proposal.ainvoke({"proposal_id": mock_proposal.id, "name": "Updated"})

        mock_repo.propose.assert_not_called()

    async def test_refuses_to_update_deployed_proposal(
        self, mock_repo, mock_session, mock_proposal
    ):
        """update_proposal refuses to update a DEPLOYED proposal."""
        mock_proposal.status = ProposalStatus.DEPLOYED

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            result = await update_proposal.ainvoke(
                {"proposal_id": mock_proposal.id, "name": "Nope"}
            )

        assert "cannot update" in result.lower() or "cannot edit" in result.lower()
        mock_repo.update.assert_not_called()

    async def test_refuses_to_update_nonexistent_proposal(self, mock_repo, mock_session):
        """update_proposal returns error for missing proposal."""
        mock_repo.get_by_id.return_value = None

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            result = await update_proposal.ainvoke({"proposal_id": "nonexistent", "name": "X"})

        assert "not found" in result.lower()

    async def test_partial_update_preserves_other_fields(
        self, mock_repo, mock_session, mock_proposal
    ):
        """Updating only name does not pass trigger/actions to repo.update()."""
        mock_proposal.status = ProposalStatus.PROPOSED

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            await update_proposal.ainvoke({"proposal_id": mock_proposal.id, "name": "Only Name"})

        call_kwargs = mock_repo.update.call_args.kwargs
        assert call_kwargs["name"] == "Only Name"
        assert "trigger" not in call_kwargs
        assert "actions" not in call_kwargs

    async def test_update_helper_merges_into_service_call(
        self, mock_repo, mock_session, mock_proposal
    ):
        """Updating a helper proposal with helper_config merges into service_call."""
        mock_proposal.status = ProposalStatus.PROPOSED
        mock_proposal.proposal_type = "helper"
        mock_proposal.service_call = {
            "helper_type": "input_number",
            "input_id": "brightness",
            "name": "Brightness",
            "min": 0,
            "max": 100,
        }

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            await update_proposal.ainvoke(
                {
                    "proposal_id": mock_proposal.id,
                    "helper_config": {"max": 255, "step": 5},
                }
            )

        call_kwargs = mock_repo.update.call_args.kwargs
        merged = call_kwargs["service_call"]
        assert merged["max"] == 255
        assert merged["step"] == 5
        assert merged["helper_type"] == "input_number"
        assert merged["min"] == 0

    async def test_update_commits_session(self, mock_repo, mock_session, mock_proposal):
        """update_proposal commits the session after mutation."""
        mock_proposal.status = ProposalStatus.PROPOSED

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import update_proposal

            await update_proposal.ainvoke(
                {"proposal_id": mock_proposal.id, "description": "New desc"}
            )

        mock_session.commit.assert_called_once()
