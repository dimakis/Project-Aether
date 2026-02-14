"""Discovery state for Librarian agent."""

from typing import Any

from pydantic import BaseModel, Field

from .base import MessageState
from .enums import DiscoveryStatus


class EntitySummary(BaseModel):
    """Summary of a discovered entity."""

    entity_id: str
    domain: str
    name: str
    state: str
    area_id: str | None = None
    device_id: str | None = None


class DiscoveryState(MessageState):
    """State for entity discovery workflow.

    Used by the Librarian agent during HA entity discovery.
    """

    status: DiscoveryStatus = DiscoveryStatus.RUNNING
    mlflow_run_id: str | None = None

    # Discovery progress
    domains_to_scan: list[str] = Field(default_factory=list)
    domains_scanned: list[str] = Field(default_factory=list)

    # Results
    entities_found: list[EntitySummary] = Field(default_factory=list)
    entities_added: int = 0
    entities_updated: int = 0
    entities_removed: int = 0
    devices_found: int = 0
    areas_found: int = 0
    services_found: int = 0

    # Errors
    errors: list[str] = Field(default_factory=list)

    # Self-healing: detected changes since last discovery
    entity_changes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Changes detected since last sync",
    )
