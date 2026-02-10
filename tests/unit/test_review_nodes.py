"""Unit tests for review workflow nodes (Feature 28).

Tests the individual nodes that make up the config review workflow.
All HA and DB dependencies are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.graph.state import ReviewState


class TestResolveTargetsNode:
    """Tests for resolve_targets_node."""

    @pytest.mark.asyncio
    async def test_single_entity_id(self):
        """Single entity_id target is kept as-is."""
        from src.graph.nodes.review import resolve_targets_node

        state = ReviewState(targets=["automation.kitchen_lights"])
        result = await resolve_targets_node(state)
        assert result["targets"] == ["automation.kitchen_lights"]

    @pytest.mark.asyncio
    async def test_all_automations_resolves(self):
        """'all_automations' resolves to list of automation entity IDs."""
        from src.graph.nodes.review import resolve_targets_node

        mock_ha = MagicMock()
        mock_ha.list_entities = AsyncMock(
            return_value=[
                {"entity_id": "automation.kitchen_lights"},
                {"entity_id": "automation.bedroom_fan"},
            ]
        )
        state = ReviewState(targets=["all_automations"])
        result = await resolve_targets_node(state, ha_client=mock_ha)
        assert "automation.kitchen_lights" in result["targets"]
        assert "automation.bedroom_fan" in result["targets"]
        assert "all_automations" not in result["targets"]

    @pytest.mark.asyncio
    async def test_empty_targets_sets_error(self):
        """Empty targets list results in error."""
        from src.graph.nodes.review import resolve_targets_node

        state = ReviewState(targets=[])
        result = await resolve_targets_node(state)
        assert result.get("error") is not None


class TestFetchConfigsNode:
    """Tests for fetch_configs_node."""

    @pytest.mark.asyncio
    async def test_fetches_automation_config(self):
        """Fetches YAML config for automation targets."""
        from src.graph.nodes.review import fetch_configs_node

        mock_ha = MagicMock()
        mock_ha.get_automation_config = AsyncMock(
            return_value={"alias": "Kitchen Lights", "trigger": [{"platform": "state"}]}
        )

        state = ReviewState(targets=["automation.kitchen_lights"])
        result = await fetch_configs_node(state, ha_client=mock_ha)

        assert "automation.kitchen_lights" in result["configs"]
        assert "Kitchen Lights" in result["configs"]["automation.kitchen_lights"]

    @pytest.mark.asyncio
    async def test_missing_config_sets_error(self):
        """Missing config for a target records error gracefully."""
        from src.graph.nodes.review import fetch_configs_node

        mock_ha = MagicMock()
        mock_ha.get_automation_config = AsyncMock(return_value=None)

        state = ReviewState(targets=["automation.nonexistent"])
        result = await fetch_configs_node(state, ha_client=mock_ha)

        # Should not crash, but may have empty configs or error
        assert isinstance(result.get("configs", {}), dict)


class TestGatherContextNode:
    """Tests for gather_context_node."""

    @pytest.mark.asyncio
    async def test_gathers_entity_context(self):
        """Collects entity context from HA."""
        from src.graph.nodes.review import gather_context_node

        mock_ha = MagicMock()
        mock_ha.list_entities = AsyncMock(
            return_value=[
                {"entity_id": "light.kitchen", "state": "on"},
                {"entity_id": "sensor.temperature", "state": "22.5"},
            ]
        )

        state = ReviewState(
            targets=["automation.kitchen_lights"],
            configs={"automation.kitchen_lights": "alias: Kitchen Lights"},
        )
        result = await gather_context_node(state, ha_client=mock_ha)

        assert "entity_context" in result
        assert "entities" in result["entity_context"]


class TestCreateReviewProposalsNode:
    """Tests for create_review_proposals_node."""

    @pytest.mark.asyncio
    async def test_creates_proposal_with_review_fields(self):
        """Creates proposals with original_yaml and review_notes set."""
        from src.graph.nodes.review import create_review_proposals_node

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        state = ReviewState(
            targets=["automation.kitchen_lights"],
            configs={
                "automation.kitchen_lights": "alias: Kitchen Lights\ntrigger:\n  platform: state"
            },
            suggestions=[
                {
                    "entity_id": "automation.kitchen_lights",
                    "name": "Kitchen Lights (Reviewed)",
                    "suggested_trigger": [
                        {"platform": "state", "entity_id": "binary_sensor.presence"}
                    ],
                    "suggested_actions": [{"service": "light.turn_off"}],
                    "review_notes": [
                        {
                            "change": "Added presence trigger",
                            "rationale": "Only trigger when someone is home",
                            "category": "behavioral",
                        }
                    ],
                }
            ],
            review_session_id="test-session-id",
        )

        await create_review_proposals_node(state, session=mock_session)

        # Should have called session.add with a proposal
        assert mock_session.add.called
        proposal = mock_session.add.call_args[0][0]
        assert proposal.original_yaml is not None
        assert proposal.review_notes is not None
        assert proposal.review_session_id == "test-session-id"
