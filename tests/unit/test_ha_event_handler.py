"""Tests for EventHandler debounced batch upsert logic.

Feature 35: Real-Time HA Event Stream.
Covers event queuing, per-entity debounce, batch DB writes,
queue overflow handling, stats tracking, and flush-on-stop.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from src.ha.event_handler import EventHandler


def _state_event(entity_id: str, state: str, **attrs: object) -> dict[str, object]:
    """Build a minimal state_changed event payload."""
    return {
        "event_type": "state_changed",
        "data": {
            "entity_id": entity_id,
            "new_state": {
                "state": state,
                "attributes": {"friendly_name": entity_id, **attrs},
            },
        },
    }


class TestHandleEvent:
    """Tests for handle_event() queuing."""

    @pytest.mark.asyncio
    async def test_event_queued(self) -> None:
        """Events are placed on the internal queue."""
        handler = EventHandler(queue_size=10)
        event = _state_event("light.kitchen", "on")
        await handler.handle_event(event)

        assert handler._queue.qsize() == 1
        assert handler.stats["events_received"] == 1

    @pytest.mark.asyncio
    async def test_multiple_events_queued(self) -> None:
        """Multiple events accumulate in the queue."""
        handler = EventHandler(queue_size=10)
        for i in range(5):
            await handler.handle_event(_state_event(f"sensor.t{i}", str(i)))

        assert handler._queue.qsize() == 5
        assert handler.stats["events_received"] == 5

    @pytest.mark.asyncio
    async def test_queue_overflow_drops_oldest(self) -> None:
        """When queue is full, oldest event is dropped to make room."""
        handler = EventHandler(queue_size=2)
        await handler.handle_event(_state_event("a", "1"))
        await handler.handle_event(_state_event("b", "2"))
        assert handler._queue.qsize() == 2

        await handler.handle_event(_state_event("c", "3"))
        assert handler._queue.qsize() == 2
        assert handler.stats["events_received"] == 3


class TestDrainQueue:
    """Tests for _drain_queue() debounce logic."""

    @pytest.mark.asyncio
    async def test_debounce_keeps_latest(self) -> None:
        """Same entity_id updated multiple times: only latest state kept."""
        handler = EventHandler()
        await handler.handle_event(_state_event("light.living", "off"))
        await handler.handle_event(_state_event("light.living", "on"))
        await handler.handle_event(_state_event("light.living", "on", brightness=200))

        handler._drain_queue()
        assert len(handler._pending) == 1
        assert handler._pending["light.living"]["state"] == "on"
        assert handler._pending["light.living"]["attributes"]["brightness"] == 200

    @pytest.mark.asyncio
    async def test_multiple_entities_kept(self) -> None:
        """Different entity_ids each get their own pending entry."""
        handler = EventHandler()
        await handler.handle_event(_state_event("light.a", "on"))
        await handler.handle_event(_state_event("light.b", "off"))

        handler._drain_queue()
        assert len(handler._pending) == 2
        assert "light.a" in handler._pending
        assert "light.b" in handler._pending

    @pytest.mark.asyncio
    async def test_events_without_entity_id_skipped(self) -> None:
        """Events missing entity_id or new_state are silently skipped."""
        handler = EventHandler()
        await handler.handle_event({"data": {}})
        await handler.handle_event({"data": {"entity_id": "x"}})

        handler._drain_queue()
        assert len(handler._pending) == 0


class TestFlushToDb:
    """Tests for _flush_to_db() batch upsert logic."""

    @pytest.mark.asyncio
    async def test_upsert_called_with_correct_data(self) -> None:
        """_flush_to_db should call EntityRepository.upsert_many with correct shape."""
        handler = EventHandler()
        handler._pending = {
            "light.kitchen": {
                "state": "on",
                "attributes": {"friendly_name": "Kitchen Light"},
            },
        }

        mock_repo = MagicMock()
        mock_repo.upsert_many = AsyncMock(return_value=([], {"created": 0, "updated": 1}))

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        @asynccontextmanager
        async def _fake_session() -> AsyncIterator[MagicMock]:
            yield mock_session

        with (
            patch("src.storage.get_session", _fake_session),
            patch("src.dal.entities.EntityRepository", return_value=mock_repo),
        ):
            await handler._flush_to_db()

        mock_repo.upsert_many.assert_called_once()
        upsert_data = mock_repo.upsert_many.call_args[0][0]
        assert len(upsert_data) == 1
        assert upsert_data[0]["entity_id"] == "light.kitchen"
        assert upsert_data[0]["domain"] == "light"
        assert upsert_data[0]["state"] == "on"
        assert upsert_data[0]["name"] == "Kitchen Light"
        assert handler.stats["events_flushed"] == 1

    @pytest.mark.asyncio
    async def test_flush_restores_pending_on_error(self) -> None:
        """On DB error, unflushed entities are restored to pending."""
        handler = EventHandler()
        handler._pending = {
            "sensor.temp": {"state": "22", "attributes": {}},
        }

        @asynccontextmanager
        async def _failing_session() -> AsyncIterator[MagicMock]:
            raise RuntimeError("DB down")
            yield MagicMock()  # pragma: no cover

        with patch("src.storage.get_session", _failing_session):
            await handler._flush_to_db()

        assert "sensor.temp" in handler._pending
        assert handler.stats["events_flushed"] == 0

    @pytest.mark.asyncio
    async def test_automation_state_triggers_proposal_sync(self) -> None:
        """Automation entity updates should trigger _sync_proposal_statuses."""
        handler = EventHandler()
        handler._pending = {
            "automation.evening_lights": {"state": "off", "attributes": {}},
        }

        mock_repo = MagicMock()
        mock_repo.upsert_many = AsyncMock(return_value=([], {"created": 0, "updated": 1}))

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        @asynccontextmanager
        async def _fake_session() -> AsyncIterator[MagicMock]:
            yield mock_session

        with (
            patch("src.storage.get_session", _fake_session),
            patch("src.dal.entities.EntityRepository", return_value=mock_repo),
            patch.object(handler, "_sync_proposal_statuses", new_callable=AsyncMock) as mock_sync,
        ):
            await handler._flush_to_db()

        mock_sync.assert_called_once_with({"automation.evening_lights": "off"})

    @pytest.mark.asyncio
    async def test_non_automation_skips_proposal_sync(self) -> None:
        """Non-automation entities should not trigger proposal sync."""
        handler = EventHandler()
        handler._pending = {
            "light.kitchen": {"state": "on", "attributes": {}},
        }

        mock_repo = MagicMock()
        mock_repo.upsert_many = AsyncMock(return_value=([], {"created": 0, "updated": 1}))

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        @asynccontextmanager
        async def _fake_session() -> AsyncIterator[MagicMock]:
            yield mock_session

        with (
            patch("src.storage.get_session", _fake_session),
            patch("src.dal.entities.EntityRepository", return_value=mock_repo),
            patch.object(handler, "_sync_proposal_statuses", new_callable=AsyncMock) as mock_sync,
        ):
            await handler._flush_to_db()

        mock_sync.assert_not_called()


class TestStats:
    """Tests for stats property."""

    @pytest.mark.asyncio
    async def test_initial_stats(self) -> None:
        """Fresh handler has zero stats."""
        handler = EventHandler()
        stats = handler.stats
        assert stats["events_received"] == 0
        assert stats["events_flushed"] == 0
        assert stats["pending"] == 0
        assert stats["queue_size"] == 0

    @pytest.mark.asyncio
    async def test_stats_after_events(self) -> None:
        """Stats reflect received events and queue size."""
        handler = EventHandler()
        await handler.handle_event(_state_event("a", "1"))
        await handler.handle_event(_state_event("b", "2"))

        stats = handler.stats
        assert stats["events_received"] == 2
        assert stats["queue_size"] == 2


class TestLifecycle:
    """Tests for start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_stop_flushes_remaining(self) -> None:
        """stop() should drain queue and flush remaining pending events."""
        handler = EventHandler(batch_interval=999)
        await handler.handle_event(_state_event("light.a", "on"))

        mock_repo = MagicMock()
        mock_repo.upsert_many = AsyncMock(return_value=([], {"created": 0, "updated": 1}))
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        @asynccontextmanager
        async def _fake_session() -> AsyncIterator[MagicMock]:
            yield mock_session

        with (
            patch("src.storage.get_session", _fake_session),
            patch("src.dal.entities.EntityRepository", return_value=mock_repo),
        ):
            await handler.start()
            await asyncio.sleep(0.01)
            await handler.stop()

        mock_repo.upsert_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_creates_flush_task(self) -> None:
        """start() creates the flush background task."""
        handler = EventHandler(batch_interval=999)
        await handler.start()
        assert handler._flush_task is not None
        assert handler._running is True
        handler._running = False
        handler._flush_task.cancel()
        with suppress(asyncio.CancelledError):
            await handler._flush_task
