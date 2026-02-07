"""Response parsers for MCP tool outputs.

Transforms raw MCP responses into typed Pydantic models
for use in the application.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DomainInfo(BaseModel):
    """Information about a single domain."""

    domain: str
    count: int
    states: dict[str, int] = Field(default_factory=dict)


class SystemOverview(BaseModel):
    """Parsed system overview."""

    total_entities: int
    domains: dict[str, DomainInfo]
    domain_samples: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class ParsedEntity(BaseModel):
    """Parsed entity from MCP response."""

    entity_id: str
    domain: str
    name: str
    state: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    area_id: str | None = None
    device_id: str | None = None
    device_class: str | None = None
    unit_of_measurement: str | None = None
    supported_features: int = 0
    last_changed: datetime | None = None
    last_updated: datetime | None = None


class ParsedAutomation(BaseModel):
    """Parsed automation from MCP response."""

    id: str
    entity_id: str
    alias: str
    state: str
    mode: str = "single"
    last_triggered: str | None = None


class DomainSummary(BaseModel):
    """Parsed domain summary."""

    domain: str
    total_count: int
    state_distribution: dict[str, int]
    examples: dict[str, list[dict[str, str]]]
    common_attributes: list[str]


def parse_system_overview(data: dict[str, Any]) -> SystemOverview:
    """Parse system_overview response.

    Args:
        data: Raw response from system_overview tool

    Returns:
        SystemOverview model
    """
    domains = {}
    for domain_name, domain_data in data.get("domains", {}).items():
        domains[domain_name] = DomainInfo(
            domain=domain_name,
            count=domain_data.get("count", 0),
            states=domain_data.get("states", {}),
        )

    return SystemOverview(
        total_entities=data.get("total_entities", 0),
        domains=domains,
        domain_samples=data.get("domain_samples", {}),
    )


def parse_entity_list(data: list[dict[str, Any]]) -> list[ParsedEntity]:
    """Parse list_entities response.

    Args:
        data: Raw response from list_entities tool

    Returns:
        List of ParsedEntity models
    """
    entities = []
    for item in data:
        entity_id = item.get("entity_id", "")
        domain = entity_id.split(".")[0] if "." in entity_id else ""

        attrs = item.get("attributes", {})

        # Parse timestamps
        last_changed = None
        last_updated = None
        if "last_changed" in item:
            try:
                last_changed = datetime.fromisoformat(item["last_changed"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        if "last_updated" in item:
            try:
                last_updated = datetime.fromisoformat(item["last_updated"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        entities.append(
            ParsedEntity(
                entity_id=entity_id,
                domain=domain,
                name=item.get("name", attrs.get("friendly_name", entity_id)),
                state=item.get("state"),
                attributes=attrs,
                area_id=item.get("area_id") or attrs.get("area_id"),
                device_id=item.get("device_id") or attrs.get("device_id"),
                device_class=attrs.get("device_class"),
                unit_of_measurement=attrs.get("unit_of_measurement"),
                supported_features=attrs.get("supported_features", 0),
                last_changed=last_changed,
                last_updated=last_updated,
            )
        )

    return entities


def parse_entity(data: dict[str, Any]) -> ParsedEntity | None:
    """Parse get_entity response.

    Args:
        data: Raw response from get_entity tool

    Returns:
        ParsedEntity model or None
    """
    if not data:
        return None

    entities = parse_entity_list([data])
    return entities[0] if entities else None


def parse_domain_summary(domain: str, data: dict[str, Any]) -> DomainSummary:
    """Parse domain_summary_tool response.

    Args:
        domain: Domain name
        data: Raw response from domain_summary_tool

    Returns:
        DomainSummary model
    """
    return DomainSummary(
        domain=domain,
        total_count=data.get("total_count", 0),
        state_distribution=data.get("state_distribution", {}),
        examples=data.get("examples", {}),
        common_attributes=data.get("common_attributes", []),
    )


def parse_automation_list(data: list[dict[str, Any]]) -> list[ParsedAutomation]:
    """Parse list_automations response.

    Args:
        data: Raw response from list_automations tool

    Returns:
        List of ParsedAutomation models
    """
    automations = []
    for item in data:
        automations.append(
            ParsedAutomation(
                id=item.get("id", item.get("entity_id", "")),
                entity_id=item.get("entity_id", ""),
                alias=item.get("alias", ""),
                state=item.get("state", "off"),
                mode=item.get("mode", "single"),
                last_triggered=item.get("last_triggered"),
            )
        )
    return automations


class ParsedLogbookEntry(BaseModel):
    """Parsed logbook entry from HA REST API."""

    entity_id: str | None = None
    domain: str | None = None
    name: str | None = None
    message: str | None = None
    state: str | None = None
    when: str | None = None
    context_user_id: str | None = None
    context_id: str | None = None
    icon: str | None = None
    source: str | None = None


def parse_logbook_entry(data: dict[str, Any]) -> ParsedLogbookEntry:
    """Parse a single logbook entry.

    Args:
        data: Raw logbook entry dict from HA

    Returns:
        ParsedLogbookEntry model
    """
    entity_id = data.get("entity_id", "")
    domain = entity_id.split(".")[0] if entity_id and "." in entity_id else None

    return ParsedLogbookEntry(
        entity_id=entity_id or None,
        domain=domain,
        name=data.get("name"),
        message=data.get("message"),
        state=data.get("state"),
        when=data.get("when"),
        context_user_id=data.get("context_user_id"),
        context_id=data.get("context_id"),
        icon=data.get("icon"),
        source=data.get("source"),
    )


def parse_logbook_list(data: list[dict[str, Any]]) -> list[ParsedLogbookEntry]:
    """Parse a list of logbook entries.

    Args:
        data: Raw logbook response from HA

    Returns:
        List of ParsedLogbookEntry models
    """
    return [parse_logbook_entry(item) for item in data]


__all__ = [
    "SystemOverview",
    "DomainInfo",
    "ParsedEntity",
    "ParsedAutomation",
    "DomainSummary",
    "ParsedLogbookEntry",
    "parse_system_overview",
    "parse_entity_list",
    "parse_entity",
    "parse_domain_summary",
    "parse_automation_list",
    "parse_logbook_entry",
    "parse_logbook_list",
]
