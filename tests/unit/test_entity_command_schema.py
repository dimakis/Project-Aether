"""Unit tests for entity_command proposal schema validation.

Structural (Pydantic) and semantic (live HA) validation for
entity_command proposals containing service_call payloads.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_ha_client() -> MagicMock:
    """Mock HA client with entities and services for semantic checks."""
    client = MagicMock()

    client.list_entities = AsyncMock(
        return_value=[
            {"entity_id": "input_number.electricity_rate_day"},
            {"entity_id": "input_number.electricity_rate_night"},
            {"entity_id": "light.living_room"},
            {"entity_id": "switch.fan"},
        ]
    )

    client.list_services = AsyncMock(
        return_value=[
            {
                "domain": "input_number",
                "services": {
                    "set_value": {"fields": {"value": {}, "entity_id": {}}},
                },
            },
            {
                "domain": "light",
                "services": {
                    "turn_on": {"fields": {"brightness": {}}},
                    "turn_off": {"fields": {}},
                },
            },
            {
                "domain": "homeassistant",
                "services": {
                    "restart": {"fields": {}},
                    "turn_on": {"fields": {}},
                },
            },
        ]
    )

    client.get_area_registry = AsyncMock(return_value=[])

    client.get_entity = AsyncMock(
        side_effect=lambda eid: {
            "input_number.electricity_rate_day": {
                "entity_id": "input_number.electricity_rate_day",
                "state": "25.84",
                "attributes": {"min": 0, "max": 100, "step": 0.01},
            },
            "input_number.electricity_rate_night": {
                "entity_id": "input_number.electricity_rate_night",
                "state": "13.54",
                "attributes": {"min": 0, "max": 100, "step": 0.01},
            },
        }.get(eid)
    )

    return client


@pytest.fixture
def cache(mock_ha_client: MagicMock):
    """Registry cache from mock client."""
    from src.schema.ha.registry_cache import HARegistryCache

    return HARegistryCache(ha_client=mock_ha_client)


# =============================================================================
# STRUCTURAL VALIDATION
# =============================================================================


class TestEntityCommandPayloadStructural:
    """Structural validation of EntityCommandPayload via Pydantic."""

    def test_valid_minimal_payload(self) -> None:
        """Minimal entity_command payload with domain, service, entity_id."""
        from src.schema.ha.entity_command import EntityCommandPayload

        payload = EntityCommandPayload(
            domain="input_number",
            service="set_value",
            entity_id="input_number.electricity_rate_day",
        )
        assert payload.domain == "input_number"
        assert payload.service == "set_value"
        assert payload.entity_id == "input_number.electricity_rate_day"

    def test_valid_without_entity_id(self) -> None:
        """entity_id is optional (some service calls target via data)."""
        from src.schema.ha.entity_command import EntityCommandPayload

        payload = EntityCommandPayload(
            domain="homeassistant",
            service="restart",
        )
        assert payload.entity_id is None
        assert payload.data is None

    def test_valid_with_entity_updates_batch(self) -> None:
        """Payload with data.entity_updates batch list."""
        from src.schema.ha.entity_command import EntityCommandPayload

        payload = EntityCommandPayload(
            domain="input_number",
            service="set_value",
            entity_id="input_number.electricity_rate_day",
            data={
                "entity_updates": [
                    {"entity_id": "input_number.electricity_rate_day", "value": 25.84},
                    {"entity_id": "input_number.electricity_rate_night", "value": 13.54},
                ],
                "rates": {"day": 25.84, "night": 13.54},
                "plan_name": "Yuno ETV06",
            },
        )
        assert payload.data is not None
        assert len(payload.data.entity_updates) == 2
        assert payload.data.entity_updates[0].value == 25.84

    def test_extra_data_keys_allowed(self) -> None:
        """Metadata keys (rates, plan_name) are allowed in data."""
        from src.schema.ha.entity_command import EntityCommandPayload

        payload = EntityCommandPayload(
            domain="input_number",
            service="set_value",
            entity_id="input_number.electricity_rate_day",
            data={
                "entity_updates": [
                    {"entity_id": "input_number.electricity_rate_day", "value": 25.84},
                ],
                "custom_metadata": "allowed",
            },
        )
        assert payload.data is not None

    def test_missing_domain_rejected(self) -> None:
        """domain is required."""
        from pydantic import ValidationError

        from src.schema.ha.entity_command import EntityCommandPayload

        with pytest.raises(ValidationError, match="domain"):
            EntityCommandPayload(service="set_value", entity_id="input_number.x")

    def test_missing_service_rejected(self) -> None:
        """service is required."""
        from pydantic import ValidationError

        from src.schema.ha.entity_command import EntityCommandPayload

        with pytest.raises(ValidationError, match="service"):
            EntityCommandPayload(domain="input_number", entity_id="input_number.x")

    def test_malformed_entity_id_rejected(self) -> None:
        """entity_id must match domain.object_id pattern."""
        from pydantic import ValidationError

        from src.schema.ha.entity_command import EntityCommandPayload

        with pytest.raises(ValidationError, match="entity_id"):
            EntityCommandPayload(
                domain="input_number",
                service="set_value",
                entity_id="INVALID",
            )

    def test_entity_update_missing_entity_id_rejected(self) -> None:
        """EntityUpdate requires entity_id."""
        from pydantic import ValidationError

        from src.schema.ha.entity_command import EntityUpdate

        with pytest.raises(ValidationError, match="entity_id"):
            EntityUpdate(value=25.0)

    def test_entity_update_missing_value_rejected(self) -> None:
        """EntityUpdate requires value."""
        from pydantic import ValidationError

        from src.schema.ha.entity_command import EntityUpdate

        with pytest.raises(ValidationError, match="value"):
            EntityUpdate(entity_id="input_number.test")

    def test_entity_update_malformed_entity_id_rejected(self) -> None:
        """EntityUpdate entity_id must match pattern."""
        from pydantic import ValidationError

        from src.schema.ha.entity_command import EntityUpdate

        with pytest.raises(ValidationError, match="entity_id"):
            EntityUpdate(entity_id="BAD_FORMAT", value=10)

    def test_entity_update_accepts_string_value(self) -> None:
        """EntityUpdate value can be a string."""
        from src.schema.ha.entity_command import EntityUpdate

        eu = EntityUpdate(entity_id="input_text.name", value="hello")
        assert eu.value == "hello"

    def test_entity_update_accepts_int_value(self) -> None:
        """EntityUpdate value can be an int."""
        from src.schema.ha.entity_command import EntityUpdate

        eu = EntityUpdate(entity_id="counter.visitors", value=42)
        assert eu.value == 42


class TestEntityCommandSchemaRegistry:
    """Validate entity_command through the SchemaRegistry (JSON Schema)."""

    def test_registry_validates_valid_payload(self) -> None:
        """Valid entity_command dict passes registry validation."""
        import src.schema.ha  # noqa: F401
        from src.schema.core import registry

        result = registry.validate(
            "ha.entity_command",
            {
                "domain": "input_number",
                "service": "set_value",
                "entity_id": "input_number.electricity_rate_day",
            },
        )
        assert result.valid is True

    def test_registry_rejects_missing_domain(self) -> None:
        """Missing domain caught by JSON Schema validation."""
        import src.schema.ha  # noqa: F401
        from src.schema.core import registry

        result = registry.validate(
            "ha.entity_command",
            {"service": "set_value", "entity_id": "input_number.x"},
        )
        assert result.valid is False
        assert any("domain" in e.message for e in result.errors)

    def test_registry_rejects_missing_service(self) -> None:
        """Missing service caught by JSON Schema validation."""
        import src.schema.ha  # noqa: F401
        from src.schema.core import registry

        result = registry.validate(
            "ha.entity_command",
            {"domain": "input_number", "entity_id": "input_number.x"},
        )
        assert result.valid is False
        assert any("service" in e.message for e in result.errors)


# =============================================================================
# SEMANTIC VALIDATION
# =============================================================================


class TestEntityCommandSemantic:
    """Semantic validation of entity_command against live HA state."""

    @pytest.mark.asyncio
    async def test_valid_entity_command(self, cache) -> None:
        """Valid entity_command with existing entity and service passes."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "domain": "input_number",
            "service": "set_value",
            "entity_id": "input_number.electricity_rate_day",
        }
        result = await validator.validate(data, schema_name="ha.entity_command")
        assert result.valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_nonexistent_entity_id_rejected(self, cache) -> None:
        """Top-level entity_id that doesn't exist is caught."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "domain": "input_number",
            "service": "set_value",
            "entity_id": "input_number.nonexistent",
        }
        result = await validator.validate(data, schema_name="ha.entity_command")
        assert result.valid is False
        assert any("input_number.nonexistent" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_nonexistent_service_rejected(self, cache) -> None:
        """domain.service that doesn't exist is caught."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "domain": "input_number",
            "service": "nonexistent_action",
            "entity_id": "input_number.electricity_rate_day",
        }
        result = await validator.validate(data, schema_name="ha.entity_command")
        assert result.valid is False
        assert any("nonexistent_action" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_batch_entity_updates_all_exist(self, cache) -> None:
        """entity_updates with all existing entities passes."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "domain": "input_number",
            "service": "set_value",
            "entity_id": "input_number.electricity_rate_day",
            "data": {
                "entity_updates": [
                    {"entity_id": "input_number.electricity_rate_day", "value": 25.84},
                    {"entity_id": "input_number.electricity_rate_night", "value": 13.54},
                ],
            },
        }
        result = await validator.validate(data, schema_name="ha.entity_command")
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_batch_entity_updates_nonexistent_entity(self, cache) -> None:
        """entity_updates with a nonexistent entity_id is caught."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "domain": "input_number",
            "service": "set_value",
            "entity_id": "input_number.electricity_rate_day",
            "data": {
                "entity_updates": [
                    {"entity_id": "input_number.electricity_rate_day", "value": 25.84},
                    {"entity_id": "input_number.ghost_rate", "value": 99.0},
                ],
            },
        }
        result = await validator.validate(data, schema_name="ha.entity_command")
        assert result.valid is False
        assert any("input_number.ghost_rate" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_input_number_value_out_of_range(self, cache) -> None:
        """Value exceeding input_number max attribute is caught."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "domain": "input_number",
            "service": "set_value",
            "entity_id": "input_number.electricity_rate_day",
            "data": {
                "entity_updates": [
                    {"entity_id": "input_number.electricity_rate_day", "value": 999.0},
                ],
            },
        }
        result = await validator.validate(data, schema_name="ha.entity_command")
        assert result.valid is False
        assert any(
            "range" in e.message.lower() or "max" in e.message.lower() for e in result.errors
        )

    @pytest.mark.asyncio
    async def test_input_number_value_below_min(self, cache) -> None:
        """Value below input_number min attribute is caught."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "domain": "input_number",
            "service": "set_value",
            "entity_id": "input_number.electricity_rate_day",
            "data": {
                "entity_updates": [
                    {"entity_id": "input_number.electricity_rate_day", "value": -5.0},
                ],
            },
        }
        result = await validator.validate(data, schema_name="ha.entity_command")
        assert result.valid is False
        assert any(
            "range" in e.message.lower() or "min" in e.message.lower() for e in result.errors
        )

    @pytest.mark.asyncio
    async def test_no_entity_id_still_checks_service(self, cache) -> None:
        """Command without entity_id still validates service exists."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "domain": "homeassistant",
            "service": "restart",
        }
        result = await validator.validate(data, schema_name="ha.entity_command")
        assert result.valid is True
