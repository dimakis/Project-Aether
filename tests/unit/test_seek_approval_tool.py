"""Unit tests for the seek_approval tool.

Tests creation of proposals for entity commands, automations,
scripts, and scenes via the seek_approval tool.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


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

            result = await seek_approval.ainvoke(
                {
                    "action_type": "entity_command",
                    "name": "Turn on living room lights",
                    "description": "Turn on the living room lights",
                    "entity_id": "light.living_room",
                    "service_domain": "light",
                    "service_action": "turn_on",
                }
            )

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

            result = await seek_approval.ainvoke(
                {
                    "action_type": "entity_command",
                    "name": "Toggle switch",
                    "description": "Toggle the kitchen switch",
                    "entity_id": "switch.kitchen",
                    "service_action": "toggle",
                }
            )

            assert "submitted a proposal" in result
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["service_call"]["domain"] == "switch"

    async def test_entity_command_requires_entity_id(self):
        """seek_approval with entity_command fails without entity_id."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "entity_command",
                "name": "Bad command",
                "description": "No entity",
            }
        )

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

            result = await seek_approval.ainvoke(
                {
                    "action_type": "automation",
                    "name": "Sunset lights",
                    "description": "Turn on lights at sunset",
                    "trigger": {"platform": "sun", "event": "sunset"},
                    "actions": [{"service": "light.turn_on", "target": {"area_id": "living_room"}}],
                }
            )

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

            result = await seek_approval.ainvoke(
                {
                    "action_type": "script",
                    "name": "Movie mode",
                    "description": "Dim lights and turn on TV",
                    "actions": [
                        {"service": "light.turn_on", "data": {"brightness": 50}},
                        {"service": "media_player.turn_on"},
                    ],
                }
            )

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

            result = await seek_approval.ainvoke(
                {
                    "action_type": "scene",
                    "name": "Cozy evening",
                    "description": "Warm lighting for the evening",
                    "actions": {
                        "light.living_room": {"state": "on", "brightness": 128, "color_temp": 400},
                    },
                }
            )

            assert "submitted a scene proposal" in result
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["proposal_type"] == "scene"

    async def test_invalid_action_type_returns_error(self):
        """seek_approval with invalid action_type returns helpful error."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "invalid_type",
                "name": "Bad",
                "description": "Bad",
            }
        )

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

            result = await seek_approval.ainvoke(
                {
                    "action_type": "entity_command",
                    "name": "Set brightness",
                    "description": "Set living room to 50%",
                    "entity_id": "light.living_room",
                    "service_domain": "light",
                    "service_action": "turn_on",
                    "service_data": {"brightness": 128},
                }
            )

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

            await seek_approval.ainvoke(
                {
                    "action_type": "entity_command",
                    "name": "Test",
                    "description": "Test",
                    "entity_id": "switch.test",
                }
            )

            mock_repo.propose.assert_called_once_with(mock_proposal.id)
            mock_session.commit.assert_called_once()

    # ── Review proposals: original_yaml passthrough ────────────────────

    async def test_automation_passes_original_yaml_to_repo(
        self, mock_repo, mock_session, mock_proposal
    ):
        """seek_approval forwards original_yaml so the proposal stores the baseline config."""
        original = "alias: Old\ntrigger:\n  platform: sun\n  event: sunset\n"

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke(
                {
                    "action_type": "automation",
                    "name": "Improved: Sunset Lights",
                    "description": "Better sunset automation",
                    "trigger": {"platform": "sun", "event": "sunset", "offset": "-00:30:00"},
                    "actions": [{"service": "light.turn_on"}],
                    "original_yaml": original,
                }
            )

            assert "submitted an automation proposal" in result
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["original_yaml"] == original

    async def test_script_passes_original_yaml_to_repo(
        self, mock_repo, mock_session, mock_proposal
    ):
        """seek_approval forwards original_yaml for script proposals."""
        original = "sequence:\n  - service: light.turn_on\n"

        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke(
                {
                    "action_type": "script",
                    "name": "Improved: Movie Mode",
                    "description": "Better movie mode",
                    "actions": [
                        {"service": "light.turn_on", "data": {"brightness": 50}},
                        {"service": "media_player.turn_on"},
                    ],
                    "original_yaml": original,
                }
            )

            assert "submitted a script proposal" in result
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["original_yaml"] == original

    async def test_omitted_original_yaml_defaults_to_none(
        self, mock_repo, mock_session, mock_proposal
    ):
        """When original_yaml is not passed, repo.create receives None."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            await seek_approval.ainvoke(
                {
                    "action_type": "automation",
                    "name": "Fresh automation",
                    "description": "No original",
                    "trigger": {"platform": "state", "entity_id": "light.test"},
                    "actions": [{"service": "light.turn_on"}],
                }
            )

            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs.get("original_yaml") is None

    # ── Validation: reject incomplete proposals ──────────────────────────

    async def test_automation_rejects_missing_trigger(self):
        """seek_approval rejects automation without trigger."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "automation",
                "name": "Sunset lights",
                "description": "Turn on lights at sunset",
                "actions": [{"service": "light.turn_on"}],
                # trigger intentionally omitted
            }
        )

        assert "trigger" in result.lower()
        assert "required" in result.lower()

    async def test_automation_rejects_missing_actions(self):
        """seek_approval rejects automation without actions."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "automation",
                "name": "Sunset lights",
                "description": "Turn on lights at sunset",
                "trigger": {"platform": "sun", "event": "sunset"},
                # actions intentionally omitted
            }
        )

        assert "actions" in result.lower()
        assert "required" in result.lower()

    async def test_automation_rejects_empty_trigger(self):
        """seek_approval rejects automation with empty trigger list."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "automation",
                "name": "Sunset lights",
                "description": "Turn on lights at sunset",
                "trigger": [],
                "actions": [{"service": "light.turn_on"}],
            }
        )

        assert "trigger" in result.lower()
        assert "required" in result.lower()

    async def test_automation_rejects_empty_actions(self):
        """seek_approval rejects automation with empty actions list."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "automation",
                "name": "Sunset lights",
                "description": "Turn on lights at sunset",
                "trigger": {"platform": "sun", "event": "sunset"},
                "actions": [],
            }
        )

        assert "actions" in result.lower()
        assert "required" in result.lower()

    async def test_script_rejects_missing_actions(self):
        """seek_approval rejects script without actions."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "script",
                "name": "Movie mode",
                "description": "Dim lights and turn on TV",
                # actions intentionally omitted
            }
        )

        assert "actions" in result.lower()
        assert "required" in result.lower()

    async def test_script_rejects_empty_actions(self):
        """seek_approval rejects script with empty actions list."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "script",
                "name": "Movie mode",
                "description": "Dim lights and turn on TV",
                "actions": [],
            }
        )

        assert "actions" in result.lower()
        assert "required" in result.lower()

    async def test_dashboard_creates_proposal(self, mock_repo, mock_session, mock_proposal):
        """seek_approval with dashboard creates a dashboard proposal."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            config = {"views": [{"title": "Home", "cards": []}]}

            result = await seek_approval.ainvoke(
                {
                    "action_type": "dashboard",
                    "name": "Modern Home Dashboard",
                    "description": "Redesigned overview dashboard",
                    "dashboard_config": config,
                    "dashboard_url_path": "default",
                }
            )

        assert "proposal" in result.lower() or "submitted" in result.lower()
        mock_repo.create.assert_called_once()
        create_kwargs = mock_repo.create.call_args
        assert create_kwargs.kwargs.get("proposal_type") == "dashboard"
        assert create_kwargs.kwargs.get("dashboard_config") == config

    async def test_dashboard_rejects_missing_config(self):
        """seek_approval rejects dashboard without config."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "dashboard",
                "name": "Empty Dashboard",
                "description": "No config provided",
            }
        )

        assert "dashboard_config" in result.lower() or "required" in result.lower()

    # ── Helper proposals ─────────────────────────────────────────────────

    async def test_helper_creates_proposal(self, mock_repo, mock_session, mock_proposal):
        """seek_approval with helper creates a helper proposal."""
        with (
            patch("src.tools.approval_tools.get_session") as mock_get_session,
            patch("src.tools.approval_tools.ProposalRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tools.approval_tools import seek_approval

            result = await seek_approval.ainvoke(
                {
                    "action_type": "helper",
                    "name": "Create Vacation Mode toggle",
                    "description": "Input boolean for vacation mode",
                    "helper_config": {
                        "helper_type": "input_boolean",
                        "input_id": "vacation_mode",
                        "name": "Vacation Mode",
                        "initial": False,
                    },
                }
            )

            assert "proposal" in result.lower() or "submitted" in result.lower()
            mock_repo.create.assert_called_once()
            call_kwargs = mock_repo.create.call_args.kwargs
            assert call_kwargs["proposal_type"] == "helper"
            assert call_kwargs["service_call"]["helper_type"] == "input_boolean"
            assert call_kwargs["service_call"]["input_id"] == "vacation_mode"

    async def test_helper_rejects_missing_config(self):
        """seek_approval rejects helper without helper_config."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "helper",
                "name": "Bad helper",
                "description": "No config",
            }
        )

        assert "helper_config" in result.lower() or "required" in result.lower()

    async def test_helper_rejects_missing_helper_type(self):
        """seek_approval rejects helper_config without helper_type key."""
        from src.tools.approval_tools import seek_approval

        result = await seek_approval.ainvoke(
            {
                "action_type": "helper",
                "name": "Bad helper",
                "description": "No type",
                "helper_config": {"input_id": "test", "name": "Test"},
            }
        )

        assert "helper_type" in result.lower()


@pytest.mark.asyncio
class TestAutomationProposalValidation:
    """Automation proposals run structural validation before creation.

    Tests call _create_automation_proposal directly, loaded via
    importlib.util to bypass the pre-existing circular import in
    src.tools.__init__ (src.tools <-> src.agents.architect.workflow).
    """

    @pytest.fixture
    def approval_mod(self):
        """Load approval_tools module, bypassing src/tools/__init__.py circular import."""
        import importlib.util
        import sys

        key = "src.tools.approval_tools"
        if key in sys.modules:
            return sys.modules[key]

        spec = importlib.util.spec_from_file_location(key, "src/tools/approval_tools.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
        return mod

    @pytest.fixture
    def mock_proposal(self):
        proposal = MagicMock()
        proposal.id = str(uuid4())
        proposal.name = "Test"
        return proposal

    @pytest.fixture
    def mock_repo(self, mock_proposal):
        repo = AsyncMock()
        repo.create.return_value = mock_proposal
        repo.propose.return_value = mock_proposal
        return repo

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    async def test_valid_yaml_creates_proposal(
        self, approval_mod, mock_repo, mock_session, mock_proposal
    ):
        """When YAML passes structural validation, proposal is created."""
        valid_yaml = (
            "trigger:\n"
            "  - platform: sun\n"
            "    event: sunset\n"
            "action:\n"
            "  - service: light.turn_on\n"
            "    target:\n"
            "      entity_id: light.living_room\n"
        )
        parsed_data = {
            "trigger": [{"platform": "sun", "event": "sunset"}],
            "action": [{"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}],
        }

        with (
            patch.object(approval_mod, "get_session") as mock_get_session,
            patch.object(approval_mod, "ProposalRepository", return_value=mock_repo),
            patch("src.schema.validate_yaml") as mock_validate,
            patch("src.schema.parse_ha_yaml", return_value=(parsed_data, [])),
        ):
            from src.schema.core import ValidationResult

            mock_validate.return_value = ValidationResult(valid=True, schema_name="ha.automation")
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await approval_mod._create_automation_proposal(
                name="Sunset lights",
                description="Turn on lights at sunset",
                yaml_content=valid_yaml,
                trigger=None,
                actions=None,
                conditions=None,
                mode="single",
            )

        assert "submitted an automation proposal" in result
        mock_repo.create.assert_called_once()

    async def test_invalid_yaml_returns_validation_errors(self, approval_mod):
        """When YAML fails structural validation, errors are returned to the agent."""
        with patch.object(approval_mod, "validate_yaml") as mock_validate:
            from src.schema.core import ValidationError as VError
            from src.schema.core import ValidationResult

            mock_validate.return_value = ValidationResult(
                valid=False,
                errors=[VError(path="trigger[0]", message="Invalid trigger platform")],
                schema_name="ha.automation",
            )

            result = await approval_mod._create_automation_proposal(
                name="Bad automation",
                description="Has bad trigger",
                yaml_content="trigger:\n  - platform: bad\n",
                trigger=None,
                actions=None,
                conditions=None,
                mode="single",
            )

        assert "validation" in result.lower()
        assert "trigger[0]" in result or "Invalid trigger" in result

    async def test_validation_skipped_when_no_yaml_content(
        self, approval_mod, mock_repo, mock_session, mock_proposal
    ):
        """When trigger/actions provided directly (no yaml_content), structural validation
        is not run — there's no YAML string to validate."""
        with (
            patch.object(approval_mod, "get_session") as mock_get_session,
            patch.object(approval_mod, "ProposalRepository", return_value=mock_repo),
            patch("src.schema.validate_yaml") as mock_validate,
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await approval_mod._create_automation_proposal(
                name="Direct params",
                description="No YAML",
                yaml_content=None,
                trigger={"platform": "sun", "event": "sunset"},
                actions=[{"service": "light.turn_on"}],
                conditions=None,
                mode="single",
            )

        assert "submitted an automation proposal" in result
        mock_validate.assert_not_called()

    async def test_validation_error_does_not_create_proposal(self, approval_mod):
        """When YAML fails validation, no proposal is persisted."""
        with (
            patch("src.schema.validate_yaml") as mock_validate,
            patch.object(approval_mod, "ProposalRepository") as mock_repo_cls,
        ):
            from src.schema.core import ValidationError as VError
            from src.schema.core import ValidationResult

            mock_validate.return_value = ValidationResult(
                valid=False,
                errors=[VError(path="action[0].service", message="Unknown service")],
                schema_name="ha.automation",
            )

            await approval_mod._create_automation_proposal(
                name="Bad",
                description="Bad",
                yaml_content="trigger:\n  - platform: state\n",
                trigger=None,
                actions=None,
                conditions=None,
                mode="single",
            )

        mock_repo_cls.return_value.create.assert_not_called()
