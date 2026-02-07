"""Unit tests for the seek_approval tool.

Tests creation of proposals for entity commands, automations,
scripts, and scenes via the seek_approval tool.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
class TestSeekApprovalTool:
    """Tests for the seek_approval tool."""

    @pytest.fixture
    def mock_proposal(self):
        """Create a mock proposal."""
        proposal = MagicMock()
        proposal.id = str(uuid4())
        proposal.name = "Test Proposal"
        return proposal

    @pytest.fixture
    def mock_repo(self, mock_proposal):
        """Create a mock ProposalRepository."""
        repo = AsyncMock()
        repo.create.return_value = mock_proposal
        repo.propose.return_value = mock_proposal
        return repo

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    async def test_entity_command_creates_proposal(self, mock_repo, mock_session, mock_proposal):
        """seek_approval with entity_command creates correct proposal."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke({
                "action_type": "entity_command",
                "name": "Turn on living room lights",
                "description": "Turn on the living room lights",
                "entity_id": "light.living_room",
                "service_domain": "light",
                "service_action": "turn_on",
            })

            assert "submitted a proposal" in result
            assert "Entity Command" in result
            assert "light.turn_on" in result
            assert "light.living_room" in result

            mock_repo.create.assert_called_once()
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["proposal_type"] == "entity_command"
            assert call_kwargs["service_call"]["domain"] == "light"
            assert call_kwargs["service_call"]["service"] == "turn_on"
            assert call_kwargs["service_call"]["entity_id"] == "light.living_room"

    async def test_entity_command_infers_domain(self, mock_repo, mock_session, mock_proposal):
        """seek_approval infers domain from entity_id when not provided."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke({
                "action_type": "entity_command",
                "name": "Toggle switch",
                "description": "Toggle the kitchen switch",
                "entity_id": "switch.kitchen",
                "service_action": "toggle",
            })

            assert "submitted a proposal" in result
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["service_call"]["domain"] == "switch"

    async def test_entity_command_requires_entity_id(self):
        """seek_approval with entity_command fails without entity_id."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke({
            "action_type": "entity_command",
            "name": "Bad command",
            "description": "No entity",
        })

        assert "entity_id is required" in result

    async def test_automation_creates_proposal(self, mock_repo, mock_session, mock_proposal):
        """seek_approval with automation creates correct proposal."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke({
                "action_type": "automation",
                "name": "Sunset lights",
                "description": "Turn on lights at sunset",
                "trigger": {"platform": "sun", "event": "sunset"},
                "actions": [{"service": "light.turn_on", "target": {"area_id": "living_room"}}],
            })

            assert "submitted an automation proposal" in result
            assert "Sunset lights" in result

            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["proposal_type"] == "automation"
            assert call_kwargs["name"] == "Sunset lights"

    async def test_script_creates_proposal(self, mock_repo, mock_session, mock_proposal):
        """seek_approval with script creates correct proposal."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke({
                "action_type": "script",
                "name": "Movie mode",
                "description": "Dim lights and turn on TV",
                "actions": [
                    {"service": "light.turn_on", "data": {"brightness": 50}},
                    {"service": "media_player.turn_on"},
                ],
            })

            assert "submitted a script proposal" in result
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["proposal_type"] == "script"

    async def test_scene_creates_proposal(self, mock_repo, mock_session, mock_proposal):
        """seek_approval with scene creates correct proposal."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke({
                "action_type": "scene",
                "name": "Cozy evening",
                "description": "Warm lighting for the evening",
                "actions": {
                    "light.living_room": {"state": "on", "brightness": 128, "color_temp": 400},
                },
            })

            assert "submitted a scene proposal" in result
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["proposal_type"] == "scene"

    async def test_invalid_action_type_returns_error(self):
        """seek_approval with invalid action_type returns helpful error."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke({
            "action_type": "invalid_type",
            "name": "Bad",
            "description": "Bad",
        })

        assert "Invalid action_type" in result
        assert "entity_command" in result
        assert "automation" in result

    async def test_entity_command_with_service_data(self, mock_repo, mock_session, mock_proposal):
        """seek_approval passes service_data through for entity commands."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke({
                "action_type": "entity_command",
                "name": "Set brightness",
                "description": "Set living room to 50%",
                "entity_id": "light.living_room",
                "service_domain": "light",
                "service_action": "turn_on",
                "service_data": {"brightness": 128},
            })

            assert "submitted a proposal" in result
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["service_call"]["data"] == {"brightness": 128}

    async def test_proposal_is_submitted_for_approval(self, mock_repo, mock_session, mock_proposal):
        """seek_approval calls repo.propose() to move to PROPOSED status."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            await seek_approval.ainvoke({
                "action_type": "entity_command",
                "name": "Test",
                "description": "Test",
                "entity_id": "switch.test",
            })

            mock_repo.propose.assert_called_once_with(mock_proposal.id)
            mock_session.commit.assert_called_once()
