"""Entity context building for the Architect conversation.

The base entity context (domain counts, areas, devices, services)
changes infrequently — only when a discovery sync runs (~30 min).
We cache this base context with a short TTL so that subsequent
requests within the same time window skip 5-6 DB queries entirely.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.graph.state import ConversationState

from src.dal import AreaRepository, DeviceRepository, EntityRepository, ServiceRepository

logger = logging.getLogger(__name__)

# ─── Base Context Cache ──────────────────────────────────────────────────────

_base_context_cache: tuple[float, str] | None = None
_BASE_CONTEXT_TTL = 60  # seconds


def _invalidate_entity_context_cache() -> None:
    """Clear the cache (useful after discovery sync or in tests)."""
    global _base_context_cache
    _base_context_cache = None


async def get_entity_context(
    session: AsyncSession,
    state: ConversationState,
) -> str | None:
    """Get relevant entity context for the conversation.

    Uses a short-TTL cache for the base context (domain counts, areas,
    devices, services) to avoid 5-6 DB queries on every request.
    Mentioned entities are always fetched fresh since they're per-message.

    Args:
        session: Database session
        state: Current conversation state

    Returns:
        Context string or None
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
            base_context = await _build_base_context(session)
            if base_context:
                _base_context_cache = (now, base_context)
            else:
                return None

        # ── Always-fresh: mentioned entities (per-message) ────────
        mentioned_section = ""
        if state.entities_mentioned:
            repo = EntityRepository(session)
            mentioned_results = await asyncio.gather(
                *(repo.get_by_entity_id(eid) for eid in state.entities_mentioned[:10])
            )
            found = [e for e in mentioned_results if e is not None]
            if found:
                lines = ["\nEntities mentioned by user:"]
                for entity in found:
                    lines.append(
                        f"- {entity.entity_id}: {entity.name or 'unnamed'} (state: {entity.state})"
                    )
                mentioned_section = "\n".join(lines)

        return base_context + mentioned_section if mentioned_section else base_context
    except Exception as e:
        logger.warning(f"Failed to get entity context: {e}")
        return None


async def _build_base_context(session: AsyncSession) -> str | None:
    """Build the base entity context from DB queries.

    This is the expensive part: 5-6 DB queries for domain counts,
    areas, devices, services, and detailed entity listings.
    """
    repo = EntityRepository(session)
    device_repo = DeviceRepository(session)
    area_repo = AreaRepository(session)
    service_repo = ServiceRepository(session)

    # Phase 1: fetch domain counts + independent summaries in parallel
    counts_result, areas, devices, services = await asyncio.gather(
        repo.get_domain_counts(),
        area_repo.list_all(limit=20),
        device_repo.list_all(limit=20),
        service_repo.list_all(limit=30),
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
    entities_by_domain = await repo.list_by_domains(
        domains_to_detail,
        limit_per_domain=50,
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
