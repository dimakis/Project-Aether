"""Entity context building for the Architect conversation.

The base entity context (domain counts, areas, devices, services)
changes infrequently — only when a discovery sync runs (~30 min).
We cache this base context with a short TTL so that subsequent
requests within the same time window skip 5-6 DB queries entirely.

Each DB query runs in its own short-lived session so that
``asyncio.gather`` can execute them truly in parallel without
hitting SQLAlchemy's "concurrent operations not permitted" error.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.graph.state import ConversationState

from src.dal import AreaRepository, DeviceRepository, EntityRepository, ServiceRepository
from src.storage import get_session_factory

logger = logging.getLogger(__name__)

# ─── Base Context Cache ──────────────────────────────────────────────────────

_base_context_cache: tuple[float, str] | None = None
_BASE_CONTEXT_TTL = 60  # seconds


def _invalidate_entity_context_cache() -> None:
    """Clear the cache (useful after discovery sync or in tests)."""
    global _base_context_cache
    _base_context_cache = None


async def get_entity_context(
    state: ConversationState,
) -> tuple[str | None, str | None]:
    """Get relevant entity context for the conversation.

    Uses a short-TTL cache for the base context (domain counts, areas,
    devices, services) to avoid 5-6 DB queries on every request.
    Mentioned entities are always fetched fresh since they're per-message.

    Each query manages its own session — the caller does NOT need to
    pass a session.

    Args:
        state: Current conversation state

    Returns:
        Tuple of (context_string, warning_string).
        - On success: (context, None)
        - On failure: (None, human-readable warning explaining what went wrong)
    """
    try:
        global _base_context_cache

        # ── Check cache for the base context ──────────────────────
        now = time.monotonic()
        base_context: str | None = None
        if _base_context_cache and now - _base_context_cache[0] < _BASE_CONTEXT_TTL:
            base_context = _base_context_cache[1]

        # ── Build base context if not cached ──────────────────────
        if base_context is None:
            base_context = await _build_base_context()
            if base_context:
                _base_context_cache = (now, base_context)
            else:
                return None, None  # No entities in DB at all

        # ── Always-fresh: mentioned entities (per-message) ────────
        mentioned_section = ""
        if state.entities_mentioned:
            factory = get_session_factory()
            session = factory()
            try:
                repo = EntityRepository(session)
                found = await repo.get_by_entity_ids(list(state.entities_mentioned[:10]))
            finally:
                await session.close()

            if found:
                lines = ["\nEntities mentioned by user:"]
                for entity in found:
                    lines.append(
                        f"- {entity.entity_id}: {entity.name or 'unnamed'} (state: {entity.state})"
                    )
                mentioned_section = "\n".join(lines)

        context = base_context + mentioned_section if mentioned_section else base_context
        return context, None
    except Exception as e:
        warning = f"Entity context unavailable: {e}"
        logger.warning(warning)
        return None, warning


async def _build_base_context() -> str | None:
    """Build the base entity context from DB queries.

    Each query runs in its own short-lived session obtained from the
    session factory so that ``asyncio.gather`` can execute them in
    true parallel without concurrent-operation errors on a single
    ``AsyncSession``.
    """
    factory = get_session_factory()

    from typing import Any

    async def _query(coro_fn: Any) -> Any:
        """Run *coro_fn(session)* in a dedicated session."""
        session = factory()
        try:
            return await coro_fn(session)
        finally:
            await session.close()

    # Phase 1: fetch domain counts + independent summaries in parallel
    counts_result, areas, devices, services = await asyncio.gather(
        _query(lambda s: EntityRepository(s).get_domain_counts()),
        _query(lambda s: AreaRepository(s).list_all(limit=20)),
        _query(lambda s: DeviceRepository(s).list_all(limit=20)),
        _query(lambda s: ServiceRepository(s).list_all(limit=30)),
    )
    counts: dict[str, int] = counts_result or {}
    if not counts:
        return None

    context_parts = ["Available entities in this Home Assistant instance:"]

    # Key domains to list in detail (most useful for automations)
    detailed_domains = [
        "light",
        "switch",
        "climate",
        "cover",
        "fan",
        "lock",
        "alarm_control_panel",
    ]

    # Batch-fetch entities for all detailed domains in a single query
    domains_to_detail = [d for d, c in counts.items() if d in detailed_domains and c <= 50]
    entities_by_domain = await _query(
        lambda s: EntityRepository(s).list_by_domains(
            domains_to_detail,
            limit_per_domain=50,
        )
    )

    for domain, count in sorted(counts.items()):
        if domain in entities_by_domain:
            entities = entities_by_domain[domain]
            entity_list = []
            for e in entities:
                name = e.name or e.entity_id.split(".")[-1].replace("_", " ").title()
                state_str = f" ({e.state})" if e.state else ""
                area_str = f" in {e.area.name}" if e.area else ""
                entity_list.append(f"  - {e.entity_id}: {name}{state_str}{area_str}")
            context_parts.append(f"- {domain} ({count}):")
            context_parts.extend(entity_list)
        else:
            context_parts.append(f"- {domain}: {count} entities")

    # Areas summary
    if areas:
        context_parts.append("\nAreas (up to 20):")
        for area in areas:
            context_parts.append(f"- {area.name} (id: {area.ha_area_id})")

    # Devices summary
    if devices:
        context_parts.append("\nDevices (up to 20):")
        for device in devices:
            area_name = device.area.name if device.area else "unknown area"
            context_parts.append(f"- {device.name} (area: {area_name}, id: {device.ha_device_id})")

    # Services summary
    if services:
        context_parts.append("\nServices (sample of 30):")
        for svc in services:
            context_parts.append(f"- {svc.domain}.{svc.service}")

    return "\n".join(context_parts)
