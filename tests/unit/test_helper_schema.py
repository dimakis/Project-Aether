"""Unit tests for helper proposal schema validation.

Structural (Pydantic) and semantic (live HA) validation for
helper proposals that create HA input_* / counter / timer helpers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_ha_client() -> MagicMock:
    """Mock HA client with entity registry for helper semantic checks."""
    client = MagicMock()

    client.list_entities = AsyncMock(
        return_value=[
            {"entity_id": "input_number.existing_rate"},
            {"entity_id": "input_boolean.vacation"},
            {"entity_id": "light.living_room"},
        ]
    )

    client.list_services = AsyncMock(return_value=[])
    client.get_area_registry = AsyncMock(return_value=[])

    return client


@pytest.fixture
def cache(mock_ha_client: MagicMock):
    """Registry cache from mock client."""
    from src.schema.ha.registry_cache import HARegistryCache

    return HARegistryCache(ha_client=mock_ha_client)


# =============================================================================
# STRUCTURAL VALIDATION
# =============================================================================


class TestHelperPayloadStructural:
    """Structural validation of HelperPayload discriminated union."""

    def test_valid_input_number(self) -> None:
        """Valid input_number helper with required fields."""
        from src.schema.ha.helper import InputNumberHelper

        h = InputNumberHelper(
            input_id="electricity_rate_day",
            name="Electricity Rate Day",
            min=0,
            max=100,
            step=0.01,
        )
        assert h.helper_type == "input_number"
        assert h.min == 0
        assert h.max == 100
        assert h.step == 0.01

    def test_valid_input_number_with_unit(self) -> None:
        """input_number with optional unit_of_measurement."""
        from src.schema.ha.helper import InputNumberHelper

        h = InputNumberHelper(
            input_id="rate",
            name="Rate",
            min=0,
            max=100,
            step=1,
            unit_of_measurement="c/kWh",
        )
        assert h.unit_of_measurement == "c/kWh"

    def test_valid_input_text(self) -> None:
        """Valid input_text helper."""
        from src.schema.ha.helper import InputTextHelper

        h = InputTextHelper(input_id="user_note", name="User Note")
        assert h.helper_type == "input_text"

    def test_valid_input_select(self) -> None:
        """Valid input_select helper with options list."""
        from src.schema.ha.helper import InputSelectHelper

        h = InputSelectHelper(
            input_id="tariff_plan",
            name="Tariff Plan",
            options=["Plan A", "Plan B"],
        )
        assert h.helper_type == "input_select"
        assert h.options == ["Plan A", "Plan B"]

    def test_valid_input_boolean(self) -> None:
        """Valid input_boolean helper."""
        from src.schema.ha.helper import InputBooleanHelper

        h = InputBooleanHelper(input_id="vacation_mode", name="Vacation Mode")
        assert h.helper_type == "input_boolean"

    def test_valid_input_datetime(self) -> None:
        """Valid input_datetime helper."""
        from src.schema.ha.helper import InputDatetimeHelper

        h = InputDatetimeHelper(
            input_id="wakeup_time",
            name="Wakeup Time",
            has_date=False,
            has_time=True,
        )
        assert h.helper_type == "input_datetime"
        assert h.has_date is False
        assert h.has_time is True

    def test_valid_input_button(self) -> None:
        """Valid input_button helper."""
        from src.schema.ha.helper import InputButtonHelper

        h = InputButtonHelper(input_id="reset_counter", name="Reset Counter")
        assert h.helper_type == "input_button"

    def test_valid_counter(self) -> None:
        """Valid counter helper with optional fields."""
        from src.schema.ha.helper import CounterHelper

        h = CounterHelper(
            input_id="visitors",
            name="Visitors",
            initial=0,
            step=1,
        )
        assert h.helper_type == "counter"
        assert h.initial == 0

    def test_valid_timer(self) -> None:
        """Valid timer helper with duration."""
        from src.schema.ha.helper import TimerHelper

        h = TimerHelper(
            input_id="cooking",
            name="Cooking Timer",
            duration="00:30:00",
        )
        assert h.helper_type == "timer"
        assert h.duration == "00:30:00"

    def test_input_number_missing_min_rejected(self) -> None:
        """input_number requires min."""
        from pydantic import ValidationError

        from src.schema.ha.helper import InputNumberHelper

        with pytest.raises(ValidationError, match="min"):
            InputNumberHelper(input_id="rate", name="Rate", max=100, step=1)

    def test_input_number_missing_max_rejected(self) -> None:
        """input_number requires max."""
        from pydantic import ValidationError

        from src.schema.ha.helper import InputNumberHelper

        with pytest.raises(ValidationError, match="max"):
            InputNumberHelper(input_id="rate", name="Rate", min=0, step=1)

    def test_input_number_missing_step_rejected(self) -> None:
        """input_number requires step."""
        from pydantic import ValidationError

        from src.schema.ha.helper import InputNumberHelper

        with pytest.raises(ValidationError, match="step"):
            InputNumberHelper(input_id="rate", name="Rate", min=0, max=100)

    def test_input_select_missing_options_rejected(self) -> None:
        """input_select requires options."""
        from pydantic import ValidationError

        from src.schema.ha.helper import InputSelectHelper

        with pytest.raises(ValidationError, match="options"):
            InputSelectHelper(input_id="plan", name="Plan")

    def test_input_select_empty_options_rejected(self) -> None:
        """input_select options must not be empty."""
        from pydantic import ValidationError

        from src.schema.ha.helper import InputSelectHelper

        with pytest.raises(ValidationError, match="options"):
            InputSelectHelper(input_id="plan", name="Plan", options=[])

    def test_missing_input_id_rejected(self) -> None:
        """All helpers require input_id."""
        from pydantic import ValidationError

        from src.schema.ha.helper import InputBooleanHelper

        with pytest.raises(ValidationError, match="input_id"):
            InputBooleanHelper(name="Test")

    def test_missing_name_rejected(self) -> None:
        """All helpers require name."""
        from pydantic import ValidationError

        from src.schema.ha.helper import InputBooleanHelper

        with pytest.raises(ValidationError, match="name"):
            InputBooleanHelper(input_id="test")

    def test_extra_keys_allowed(self) -> None:
        """Extra fields are allowed (forward-compat with new HA params)."""
        from src.schema.ha.helper import InputBooleanHelper

        h = InputBooleanHelper(
            input_id="test",
            name="Test",
            icon="mdi:test",
        )
        assert h.input_id == "test"


class TestHelperPayloadDiscriminator:
    """Test HelperPayload discriminated union dispatch."""

    def test_discriminates_input_number(self) -> None:
        """Discriminator routes to InputNumberHelper."""
        from pydantic import TypeAdapter

        from src.schema.ha.helper import HelperPayload

        adapter = TypeAdapter(HelperPayload)
        h = adapter.validate_python(
            {
                "helper_type": "input_number",
                "input_id": "rate",
                "name": "Rate",
                "min": 0,
                "max": 100,
                "step": 1,
            }
        )
        assert type(h).__name__ == "InputNumberHelper"

    def test_discriminates_input_boolean(self) -> None:
        """Discriminator routes to InputBooleanHelper."""
        from pydantic import TypeAdapter

        from src.schema.ha.helper import HelperPayload

        adapter = TypeAdapter(HelperPayload)
        h = adapter.validate_python(
            {
                "helper_type": "input_boolean",
                "input_id": "test",
                "name": "Test",
            }
        )
        assert type(h).__name__ == "InputBooleanHelper"

    def test_unknown_helper_type_rejected(self) -> None:
        """Unknown helper_type is rejected by discriminator."""
        from pydantic import TypeAdapter, ValidationError

        from src.schema.ha.helper import HelperPayload

        adapter = TypeAdapter(HelperPayload)
        with pytest.raises(ValidationError):
            adapter.validate_python(
                {
                    "helper_type": "unknown_type",
                    "input_id": "test",
                    "name": "Test",
                }
            )

    def test_missing_helper_type_rejected(self) -> None:
        """Missing helper_type is rejected."""
        from pydantic import TypeAdapter, ValidationError

        from src.schema.ha.helper import HelperPayload

        adapter = TypeAdapter(HelperPayload)
        with pytest.raises(ValidationError):
            adapter.validate_python(
                {
                    "input_id": "test",
                    "name": "Test",
                }
            )


class TestHelperSchemaRegistry:
    """Validate helper through the SchemaRegistry (JSON Schema)."""

    def test_registry_validates_valid_input_number(self) -> None:
        """Valid input_number dict passes registry validation."""
        import src.schema.ha  # noqa: F401
        from src.schema.core import registry

        result = registry.validate(
            "ha.helper",
            {
                "helper_type": "input_number",
                "input_id": "rate",
                "name": "Rate",
                "min": 0,
                "max": 100,
                "step": 1,
            },
        )
        assert result.valid is True

    def test_registry_validates_valid_input_boolean(self) -> None:
        """Valid input_boolean dict passes registry validation."""
        import src.schema.ha  # noqa: F401
        from src.schema.core import registry

        result = registry.validate(
            "ha.helper",
            {
                "helper_type": "input_boolean",
                "input_id": "test",
                "name": "Test",
            },
        )
        assert result.valid is True


# =============================================================================
# SEMANTIC VALIDATION
# =============================================================================


class TestHelperSemantic:
    """Semantic validation of helper proposals against live HA state."""

    @pytest.mark.asyncio
    async def test_no_conflict_passes(self, cache) -> None:
        """Helper with a new unique ID passes semantic check."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "helper_type": "input_number",
            "input_id": "new_rate",
            "name": "New Rate",
            "min": 0,
            "max": 100,
            "step": 1,
        }
        result = await validator.validate(data, schema_name="ha.helper")
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_name_conflict_detected(self, cache) -> None:
        """Helper whose composed entity_id already exists is caught."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "helper_type": "input_number",
            "input_id": "existing_rate",
            "name": "Existing Rate",
            "min": 0,
            "max": 100,
            "step": 1,
        }
        result = await validator.validate(data, schema_name="ha.helper")
        assert result.valid is False
        assert any("already exists" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_input_boolean_conflict_detected(self, cache) -> None:
        """input_boolean helper conflicting with existing entity."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "helper_type": "input_boolean",
            "input_id": "vacation",
            "name": "Vacation",
        }
        result = await validator.validate(data, schema_name="ha.helper")
        assert result.valid is False
        assert any("input_boolean.vacation" in e.message for e in result.errors)

    @pytest.mark.asyncio
    async def test_no_conflict_different_domain(self, cache) -> None:
        """Helper type differs from existing entity domain -- no conflict."""
        from src.schema.semantic import SemanticValidator

        validator = SemanticValidator(cache=cache)
        data = {
            "helper_type": "input_text",
            "input_id": "existing_rate",
            "name": "Existing Rate Text",
        }
        result = await validator.validate(data, schema_name="ha.helper")
        assert result.valid is True
