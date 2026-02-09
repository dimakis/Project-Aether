"""Unit tests for entity health diagnostics.

TDD: Tests written FIRST to define the API contract for
EntityDiagnostic, find_unavailable_entities, find_stale_entities,
and correlate_unavailability.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.diagnostics.entity_health import (
    EntityDiagnostic,
    correlate_unavailability,
    find_stale_entities,
    find_unavailable_entities,
)


def _mock_mcp_with_entities(entities: list[dict]) -> MagicMock:
    """Create a mock HA client that returns given entities."""
    ha = MagicMock()
    ha.list_entities = AsyncMock(return_value=entities)
    return ha


class TestFindUnavailableEntities:
    """Tests for find_unavailable_entities."""

    @pytest.mark.asyncio
    async def test_finds_unavailable_entities(self):
        """Test filtering entities with 'unavailable' state."""
        ha = _mock_mcp_with_entities(
            [
                {
                    "entity_id": "sensor.temp",
                    "state": "22.5",
                    "last_changed": "2026-02-06T10:00:00Z",
                    "attributes": {"device_class": "temperature"},
                },
                {
                    "entity_id": "sensor.motion",
                    "state": "unavailable",
                    "last_changed": "2026-02-06T08:00:00Z",
                    "attributes": {},
                },
                {
                    "entity_id": "light.kitchen",
                    "state": "on",
                    "last_changed": "2026-02-06T10:00:00Z",
                    "attributes": {},
                },
                {
                    "entity_id": "sensor.humidity",
                    "state": "unknown",
                    "last_changed": "2026-02-06T09:00:00Z",
                    "attributes": {},
                },
            ]
        )

        result = await find_unavailable_entities(ha)

        assert len(result) == 2
        assert all(isinstance(r, EntityDiagnostic) for r in result)
        entity_ids = {r.entity_id for r in result}
        assert "sensor.motion" in entity_ids
        assert "sensor.humidity" in entity_ids

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_healthy(self):
        """Test returns empty list when no entities are unavailable."""
        ha = _mock_mcp_with_entities(
            [
                {
                    "entity_id": "light.test",
                    "state": "on",
                    "last_changed": "2026-02-06T10:00:00Z",
                    "attributes": {},
                },
            ]
        )

        result = await find_unavailable_entities(ha)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_entities(self):
        """Test returns empty list when no entities exist."""
        ha = _mock_mcp_with_entities([])

        result = await find_unavailable_entities(ha)

        assert result == []

    @pytest.mark.asyncio
    async def test_diagnostic_has_required_fields(self):
        """Test EntityDiagnostic has all expected fields."""
        ha = _mock_mcp_with_entities(
            [
                {
                    "entity_id": "sensor.broken",
                    "state": "unavailable",
                    "last_changed": "2026-02-06T08:00:00Z",
                    "attributes": {},
                },
            ]
        )

        result = await find_unavailable_entities(ha)

        diag = result[0]
        assert diag.entity_id == "sensor.broken"
        assert diag.state == "unavailable"
        assert diag.available is False
        assert diag.last_changed is not None


class TestFindStaleEntities:
    """Tests for find_stale_entities."""

    @pytest.mark.asyncio
    async def test_finds_entities_not_updated_recently(self):
        """Test identifying entities that haven't been updated in N hours."""
        ha = _mock_mcp_with_entities(
            [
                {
                    "entity_id": "sensor.temp",
                    "state": "22.5",
                    "last_changed": "2026-02-01T10:00:00Z",  # 5+ days ago
                    "attributes": {},
                },
                {
                    "entity_id": "sensor.recent",
                    "state": "on",
                    "last_changed": "2099-12-31T23:59:59Z",  # Future = definitely recent
                    "attributes": {},
                },
            ]
        )

        result = await find_stale_entities(ha, hours=24)

        assert len(result) == 1
        assert result[0].entity_id == "sensor.temp"

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_recent(self):
        """Test returns empty when all entities updated recently."""
        ha = _mock_mcp_with_entities(
            [
                {
                    "entity_id": "sensor.a",
                    "state": "on",
                    "last_changed": "2099-12-31T23:59:59Z",
                    "attributes": {},
                },
            ]
        )

        result = await find_stale_entities(ha, hours=24)

        assert result == []


class TestCorrelateUnavailability:
    """Tests for correlate_unavailability."""

    def test_groups_by_integration(self):
        """Test grouping unavailable entities by integration domain."""
        diagnostics = [
            EntityDiagnostic(
                entity_id="sensor.zha_temp",
                state="unavailable",
                available=False,
                last_changed="2026-02-06T08:00:00Z",
                integration="zha",
                issues=[],
            ),
            EntityDiagnostic(
                entity_id="binary_sensor.zha_motion",
                state="unavailable",
                available=False,
                last_changed="2026-02-06T08:00:00Z",
                integration="zha",
                issues=[],
            ),
            EntityDiagnostic(
                entity_id="sensor.mqtt_temp",
                state="unavailable",
                available=False,
                last_changed="2026-02-06T09:00:00Z",
                integration="mqtt",
                issues=[],
            ),
        ]

        correlations = correlate_unavailability(diagnostics)

        assert len(correlations) == 2  # 2 integrations
        zha_group = next(c for c in correlations if c["integration"] == "zha")
        assert zha_group["count"] == 2
        assert len(zha_group["entity_ids"]) == 2

    def test_identifies_common_cause(self):
        """Test that groups with many entities suggest a common cause."""
        diagnostics = [
            EntityDiagnostic(
                entity_id=f"sensor.zha_{i}",
                state="unavailable",
                available=False,
                last_changed="2026-02-06T08:00:00Z",
                integration="zha",
                issues=[],
            )
            for i in range(5)
        ]

        correlations = correlate_unavailability(diagnostics)

        assert len(correlations) == 1
        assert correlations[0]["likely_common_cause"] is True

    def test_empty_input(self):
        """Test empty diagnostics returns empty list."""
        assert correlate_unavailability([]) == []
