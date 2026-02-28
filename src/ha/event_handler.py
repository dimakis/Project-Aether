"""Event handler for HA state_changed events.

Feature 35: Real-Time HA Event Stream.

Receives state_changed events, debounces per entity_id, and batch-upserts
to the database on a configurable interval.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_BATCH_INTERVAL = 1.5  # seconds
_DEFAULT_QUEUE_SIZE = 1000


class EventHandler:
    """Debounced batch handler for HA state_changed events.

    Collects events into a per-entity buffer, then flushes to the DB
    at a configurable interval. Only the latest state per entity is kept.
    """

    def __init__(
        self,
        batch_interval: float = _DEFAULT_BATCH_INTERVAL,
        queue_size: int = _DEFAULT_QUEUE_SIZE,
    ) -> None:
        self._batch_interval = batch_interval
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=queue_size)
        self._pending: dict[str, dict[str, Any]] = {}
        self._running = False
        self._flush_task: asyncio.Task[None] | None = None
        self._events_received = 0
        self._events_flushed = 0

    async def handle_event(self, event: dict[str, Any]) -> None:
        """Receive a state_changed event and queue it for processing."""
        try:
            self._queue.put_nowait(event)
            self._events_received += 1
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping oldest event")
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
                self._events_received += 1
            except asyncio.QueueEmpty:
                pass

    async def start(self) -> None:
        """Start the flush loop."""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Stop the flush loop and flush remaining events."""
        self._running = False
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task
        self._drain_queue()
        if self._pending:
            await self._flush_to_db()

    async def _flush_loop(self) -> None:
        """Periodically drain the queue and flush to DB."""
        while self._running:
            await asyncio.sleep(self._batch_interval)
            self._drain_queue()
            if self._pending:
                await self._flush_to_db()

    def _drain_queue(self) -> None:
        """Drain the queue into the pending buffer, keeping only latest state per entity."""
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                data = event.get("data", {})
                entity_id = data.get("entity_id")
                new_state = data.get("new_state")
                if entity_id and new_state:
                    self._pending[entity_id] = new_state
            except asyncio.QueueEmpty:
                break

    async def _flush_to_db(self) -> None:
        """Batch-upsert pending entity states to the database."""
        if not self._pending:
            return

        batch = dict(self._pending)
        self._pending.clear()

        try:
            from src.dal.entities import EntityRepository
            from src.storage import get_session

            now = datetime.now(UTC)
            upsert_data = []
            for entity_id, state in batch.items():
                domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
                upsert_data.append(
                    {
                        "entity_id": entity_id,
                        "domain": domain,
                        "state": state.get("state", "unknown"),
                        "attributes": state.get("attributes", {}),
                        "name": state.get("attributes", {}).get("friendly_name", entity_id),
                        "last_synced_at": now,
                    }
                )

            async with get_session() as session:
                repo = EntityRepository(session)
                _, stats = await repo.upsert_many(upsert_data)
                await session.commit()

            self._events_flushed += len(batch)
            if stats.get("created", 0) > 0:
                logger.info(
                    "Event stream flush: %d entities (%d created, %d updated)",
                    len(batch),
                    stats["created"],
                    stats["updated"],
                )

        except Exception:
            logger.exception("Failed to flush %d entity updates to DB", len(batch))
            for entity_id, state in batch.items():
                if entity_id not in self._pending:
                    self._pending[entity_id] = state

    @property
    def stats(self) -> dict[str, int]:
        return {
            "events_received": self._events_received,
            "events_flushed": self._events_flushed,
            "pending": len(self._pending),
            "queue_size": self._queue.qsize(),
        }


__all__ = ["EventHandler"]
