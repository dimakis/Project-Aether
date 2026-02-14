"""Entity context building for the Architect conversation."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.graph.state import ConversationState

from src.dal import AreaRepository, DeviceRepository, EntityRepository, ServiceRepository

logger = logging.getLogger(__name__)


async def get_entity_context(
    session: AsyncSession,
    state: ConversationState,
) -> str | None:
    """Get relevant entity context for the conversation.

    Args:
        session: Database session
        state: Current conversation state

    Returns:
        Context string or None
    """
    try:
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

        # Batch-fetch entities for all detailed domains in a single query (T190)
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

        # Areas summary (already fetched in parallel)
        if areas:
            context_parts.append("\nAreas (up to 20):")
            for area in areas:
                context_parts.append(f"- {area.name} (id: {area.ha_area_id})")

        # Devices summary (already fetched in parallel)
        if devices:
            context_parts.append("\nDevices (up to 20):")
            for device in devices:
                area_name = device.area.name if device.area else "unknown area"
                context_parts.append(
                    f"- {device.name} (area: {area_name}, id: {device.ha_device_id})"
                )

        # Services summary (already fetched in parallel)
        if services:
            context_parts.append("\nServices (sample of 30):")
            for svc in services:
                context_parts.append(f"- {svc.domain}.{svc.service}")

        # Fetch mentioned entities in parallel
        if state.entities_mentioned:
            mentioned_results = await asyncio.gather(
                *(repo.get_by_entity_id(eid) for eid in state.entities_mentioned[:10])
            )
            found = [e for e in mentioned_results if e is not None]
            if found:
                context_parts.append("\nEntities mentioned by user:")
                for entity in found:
                    context_parts.append(
                        f"- {entity.entity_id}: {entity.name or 'unnamed'} (state: {entity.state})"
                    )

        return "\n".join(context_parts)
    except Exception as e:
        logger.warning(f"Failed to get entity context: {e}")
        return None
