"""Unit tests for semantic pre-creation validation in seek_approval.

Verifies that _validate_before_create runs semantic validation
(entity/service existence) when an HA client is available, and
degrades gracefully when it is not.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schema.core import ValidationError as VError
from src.schema.core import ValidationResult

_HA_CLIENT_PATH = "src.ha.get_ha_client_async"
_SEMANTIC_PATH = "src.tools.approval_tools.validate_yaml_semantic"


@pytest.mark.asyncio
class TestSemanticBeforeCreate:
    """Semantic validation runs inside _validate_before_create when HA is reachable."""

    @pytest.fixture
    def mock_ha(self):
        ha = MagicMock()
        return AsyncMock(return_value=ha)

    async def test_semantic_errors_returned_for_entity_command(self, mock_ha):
        """Non-existent entity_id produces a semantic error returned to the LLM."""
        from src.tools.approval_tools import _validate_before_create

        config = {
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.nonexistent",
        }

        mock_semantic = AsyncMock(
            return_value=ValidationResult(
                valid=False,
                errors=[VError(path="entity_id", message="Entity 'light.nonexistent' not found")],
                schema_name="ha.entity_command",
            )
        )

        with (
            patch(_HA_CLIENT_PATH, mock_ha),
            patch(_SEMANTIC_PATH, new=mock_semantic),
        ):
            result = await _validate_before_create("entity_command", config, "Test cmd")

        assert result is not None
        assert "nonexistent" in result
        assert "seek_approval" in result

    async def test_semantic_valid_returns_none(self, mock_ha):
        """When both structural and semantic pass, returns None."""
        from src.tools.approval_tools import _validate_before_create

        config = {
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.living_room",
        }

        mock_semantic = AsyncMock(
            return_value=ValidationResult(
                valid=True,
                schema_name="ha.entity_command",
            )
        )

        with (
            patch(_HA_CLIENT_PATH, mock_ha),
            patch(_SEMANTIC_PATH, new=mock_semantic),
        ):
            result = await _validate_before_create("entity_command", config, "Test cmd")

        assert result is None

    async def test_semantic_skipped_when_ha_unavailable(self):
        """When HA client is unreachable, semantic validation is skipped gracefully."""
        from src.tools.approval_tools import _validate_before_create

        config = {
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.living_room",
        }

        mock_ha_fail = AsyncMock(side_effect=Exception("HA connection refused"))

        with patch(_HA_CLIENT_PATH, mock_ha_fail):
            result = await _validate_before_create("entity_command", config, "Test cmd")

        assert result is None

    async def test_semantic_runs_for_helper(self, mock_ha):
        """Semantic validation also runs for helper proposals."""
        from src.tools.approval_tools import _validate_before_create

        config = {
            "helper_type": "input_boolean",
            "input_id": "guest_mode",
            "name": "Guest Mode",
        }

        mock_semantic = AsyncMock(
            return_value=ValidationResult(
                valid=False,
                errors=[
                    VError(
                        path="input_id",
                        message="Helper 'input_boolean.guest_mode' already exists",
                    )
                ],
                schema_name="ha.helper",
            )
        )

        with (
            patch(_HA_CLIENT_PATH, mock_ha),
            patch(_SEMANTIC_PATH, new=mock_semantic),
        ):
            result = await _validate_before_create("helper", config, "Guest toggle")

        assert result is not None
        assert "already exists" in result

    async def test_structural_failure_skips_semantic(self):
        """When structural validation fails, semantic is never called."""
        from src.tools.approval_tools import _validate_before_create

        config = {"entity_id": "light.kitchen"}

        mock_semantic = AsyncMock()

        with patch(_SEMANTIC_PATH, new=mock_semantic):
            result = await _validate_before_create("entity_command", config, "Bad cmd")

        assert result is not None
        assert "Errors" in result
        mock_semantic.assert_not_called()

    async def test_unknown_type_skips_all_validation(self):
        """Unknown proposal types skip both structural and semantic."""
        from src.tools.approval_tools import _validate_before_create

        result = await _validate_before_create("nonexistent", {}, "test")
        assert result is None

    async def test_validate_before_create_is_async(self):
        """_validate_before_create must be a coroutine (async)."""
        import asyncio

        from src.tools.approval_tools import _validate_before_create

        assert asyncio.iscoroutinefunction(_validate_before_create)
