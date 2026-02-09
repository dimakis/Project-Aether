"""Tests for delta sync — skip unchanged entities.

Verifies that run_delta_sync only upserts entities whose HA last_updated
timestamp is newer than the DB last_synced_at, or whose config is NULL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@dataclass
class FakeEntity:
    """Minimal entity stub matching ParsedEntity."""

    entity_id: str
    domain: str
    name: str
    state: str = "on"
    attributes: dict[str, Any] = field(default_factory=dict)
    area_id: str | None = None
    device_id: str | None = None
    last_updated: datetime | None = None
    last_changed: datetime | None = None
    device_class: str | None = None
    unit_of_measurement: str | None = None
    supported_features: int = 0


def _ts(minutes_ago: int = 0) -> datetime:
    return datetime.now(UTC) - timedelta(minutes=minutes_ago)


@pytest.mark.asyncio
class TestDeltaSync:
    """Verify delta sync skips unchanged entities."""

    async def test_skips_unchanged_entity(self):
        """Entity with last_updated older than last_synced_at should be skipped."""
        from src.dal.sync import DiscoverySyncService

        # Entity was updated 60 min ago, last synced 30 min ago -> skip
        entity = FakeEntity(
            entity_id="light.living_room",
            domain="light",
            name="Living Room",
            last_updated=_ts(minutes_ago=60),
        )

        # Mock DB record: synced more recently than HA updated
        db_entity = MagicMock()
        db_entity.last_synced_at = _ts(minutes_ago=30)

        ha_client = AsyncMock()
        ha_client.list_entities = AsyncMock(return_value=[])

        session = AsyncMock()
        service = DiscoverySyncService(session, ha_client)
        service.entity_repo = AsyncMock()
        service.entity_repo.get_by_entity_id = AsyncMock(return_value=db_entity)
        service.entity_repo.upsert = AsyncMock()
        service.entity_repo.get_all_entity_ids = AsyncMock(return_value={"light.living_room"})

        stats = await service._sync_entities_delta([entity], {}, {})

        # Should be skipped, not upserted
        assert stats["skipped"] == 1
        assert stats["updated"] == 0
        service.entity_repo.upsert.assert_not_called()

    async def test_syncs_changed_entity(self):
        """Entity with last_updated newer than last_synced_at should be synced."""
        from src.dal.sync import DiscoverySyncService

        # Entity was updated 5 min ago, last synced 30 min ago -> sync
        entity = FakeEntity(
            entity_id="light.living_room",
            domain="light",
            name="Living Room",
            last_updated=_ts(minutes_ago=5),
        )

        db_entity = MagicMock()
        db_entity.last_synced_at = _ts(minutes_ago=30)

        ha_client = AsyncMock()
        session = AsyncMock()
        service = DiscoverySyncService(session, ha_client)
        service.entity_repo = AsyncMock()
        service.entity_repo.get_by_entity_id = AsyncMock(return_value=db_entity)
        service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), False))
        service.entity_repo.get_all_entity_ids = AsyncMock(return_value={"light.living_room"})

        stats = await service._sync_entities_delta([entity], {}, {})

        assert stats["updated"] == 1
        assert stats["skipped"] == 0
        service.entity_repo.upsert.assert_called_once()

    async def test_syncs_new_entity(self):
        """Entity not in DB should always be synced."""
        from src.dal.sync import DiscoverySyncService

        entity = FakeEntity(
            entity_id="light.new_bulb",
            domain="light",
            name="New Bulb",
            last_updated=_ts(minutes_ago=5),
        )

        ha_client = AsyncMock()
        session = AsyncMock()
        service = DiscoverySyncService(session, ha_client)
        service.entity_repo = AsyncMock()
        service.entity_repo.get_by_entity_id = AsyncMock(return_value=None)
        service.entity_repo.upsert = AsyncMock(return_value=(MagicMock(), True))
        service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())

        stats = await service._sync_entities_delta([entity], {}, {})

        assert stats["added"] == 1
        service.entity_repo.upsert.assert_called_once()

    async def test_run_delta_sync_returns_stats(self):
        """run_delta_sync should return combined stats."""
        from src.dal.sync import DiscoverySyncService

        ha_client = AsyncMock()
        ha_client.list_entities = AsyncMock(return_value=[])

        session = AsyncMock()
        service = DiscoverySyncService(session, ha_client)

        with patch.object(service, "_sync_entities_delta", new_callable=AsyncMock) as mock_delta:
            mock_delta.return_value = {"added": 1, "updated": 2, "skipped": 10, "removed": 0}
            with patch.object(
                service, "_sync_automation_entities", new_callable=AsyncMock
            ) as mock_auto:
                mock_auto.return_value = {
                    "automations_synced": 1,
                    "scripts_synced": 0,
                    "scenes_synced": 0,
                }
                with patch("src.dal.sync.parse_entity_list", return_value=[]):
                    stats = await service.run_delta_sync()

        assert stats["added"] == 1
        assert stats["updated"] == 2
        assert stats["skipped"] == 10
