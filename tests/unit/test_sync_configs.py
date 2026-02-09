"""Tests for config enrichment during discovery sync.

Verifies that _sync_automation_entities fetches full configs from HA
and stores them in the automation.config and script.sequence fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@dataclass
class FakeEntity:
    """Minimal entity stub matching what parse_entity_list returns."""

    entity_id: str
    domain: str
    name: str
    state: str = "on"
    attributes: dict[str, Any] = field(default_factory=dict)
    area_id: str | None = None
    device_id: str | None = None


def _make_automation(entity_id: str, ha_id: str, alias: str) -> FakeEntity:
    return FakeEntity(
        entity_id=entity_id,
        domain="automation",
        name=alias,
        attributes={"id": ha_id, "friendly_name": alias, "mode": "single"},
    )


def _make_script(entity_id: str, alias: str) -> FakeEntity:
    return FakeEntity(
        entity_id=entity_id,
        domain="script",
        name=alias,
        attributes={"friendly_name": alias, "mode": "single"},
    )


@pytest.mark.asyncio
class TestSyncConfigEnrichment:
    """Verify configs are fetched and stored during sync."""

    async def test_automation_config_stored_after_upsert(self):
        """Automation config should be fetched from HA and included in upsert."""
        from src.dal.sync import DiscoverySyncService

        auto_config = {
            "id": "sunset_lights",
            "alias": "Sunset Lights",
            "trigger": [{"platform": "sun", "event": "sunset"}],
            "action": [{"service": "light.turn_on"}],
            "mode": "single",
        }

        ha_client = AsyncMock()
        ha_client.get_automation_config = AsyncMock(return_value=auto_config)
        ha_client.get_script_config = AsyncMock(return_value=None)

        mock_auto_repo = AsyncMock()
        mock_auto_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        mock_auto_repo.get_all_ha_ids = AsyncMock(return_value=set())

        mock_script_repo = AsyncMock()
        mock_script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        mock_scene_repo = AsyncMock()
        mock_scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        session = AsyncMock()
        service = DiscoverySyncService(session, ha_client)
        service.automation_repo = mock_auto_repo
        service.script_repo = mock_script_repo
        service.scene_repo = mock_scene_repo

        entities = [_make_automation("automation.sunset_lights", "sunset_lights", "Sunset Lights")]
        stats = await service._sync_automation_entities(entities)

        assert stats["automations_synced"] == 1

        # Config should be included in the upsert data
        upsert_data = mock_auto_repo.upsert.call_args[0][0]
        assert upsert_data["config"] == auto_config

        # HA client should have been called with the automation ID
        ha_client.get_automation_config.assert_called_once_with("sunset_lights")

    async def test_script_sequence_stored_after_upsert(self):
        """Script sequence should be fetched from HA and included in upsert."""
        from src.dal.sync import DiscoverySyncService

        script_config = {
            "alias": "Movie Mode",
            "sequence": [
                {"service": "light.turn_on", "data": {"brightness": 50}},
                {"service": "media_player.turn_on"},
            ],
            "mode": "single",
            "fields": {"target_room": {"description": "Room to set up"}},
        }

        ha_client = AsyncMock()
        ha_client.get_automation_config = AsyncMock(return_value=None)
        ha_client.get_script_config = AsyncMock(return_value=script_config)

        mock_auto_repo = AsyncMock()
        mock_auto_repo.get_all_ha_ids = AsyncMock(return_value=set())
        mock_script_repo = AsyncMock()
        mock_script_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        mock_script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        mock_scene_repo = AsyncMock()
        mock_scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        session = AsyncMock()
        service = DiscoverySyncService(session, ha_client)
        service.automation_repo = mock_auto_repo
        service.script_repo = mock_script_repo
        service.scene_repo = mock_scene_repo

        entities = [_make_script("script.movie_mode", "Movie Mode")]
        stats = await service._sync_automation_entities(entities)

        assert stats["scripts_synced"] == 1

        upsert_data = mock_script_repo.upsert.call_args[0][0]
        assert upsert_data["sequence"] == script_config["sequence"]
        assert upsert_data["fields"] == script_config["fields"]

        ha_client.get_script_config.assert_called_once_with("movie_mode")

    async def test_config_fetch_failure_does_not_break_sync(self):
        """A failed config fetch should not prevent the entity from being synced."""
        from src.dal.sync import DiscoverySyncService

        ha_client = AsyncMock()
        ha_client.get_automation_config = AsyncMock(side_effect=Exception("HA 404"))
        ha_client.get_script_config = AsyncMock(side_effect=Exception("HA 404"))

        mock_auto_repo = AsyncMock()
        mock_auto_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        mock_auto_repo.get_all_ha_ids = AsyncMock(return_value=set())
        mock_script_repo = AsyncMock()
        mock_script_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        mock_script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        mock_scene_repo = AsyncMock()
        mock_scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        session = AsyncMock()
        service = DiscoverySyncService(session, ha_client)
        service.automation_repo = mock_auto_repo
        service.script_repo = mock_script_repo
        service.scene_repo = mock_scene_repo

        entities = [
            _make_automation("automation.broken", "broken", "Broken Auto"),
            _make_script("script.broken", "Broken Script"),
        ]
        stats = await service._sync_automation_entities(entities)

        # Both should still be synced (without config)
        assert stats["automations_synced"] == 1
        assert stats["scripts_synced"] == 1

        # Upsert should have been called, config will be None
        auto_data = mock_auto_repo.upsert.call_args[0][0]
        assert auto_data.get("config") is None

        script_data = mock_script_repo.upsert.call_args[0][0]
        assert script_data.get("sequence") is None
