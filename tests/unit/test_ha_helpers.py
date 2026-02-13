"""Unit tests for HA helpers module.

Tests HelperMixin methods with mocked _request.
"""

from unittest.mock import AsyncMock

import pytest

from src.ha.base import HAClientError
from src.ha.helpers import HelperMixin


class MockHAClient(HelperMixin):
    """Mock HA client that inherits HelperMixin for testing."""

    def __init__(self):
        self._request = AsyncMock()
        self.list_entities = AsyncMock()


@pytest.fixture
def ha_client():
    """Create a mock HA client."""
    return MockHAClient()


class TestCreateInputBoolean:
    """Tests for create_input_boolean."""

    @pytest.mark.asyncio
    async def test_create_input_boolean_success(self, ha_client):
        """Test successful input_boolean creation."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_boolean(
            input_id="test_switch",
            name="Test Switch",
            initial=True,
        )

        assert result["success"] is True
        assert result["input_id"] == "test_switch"
        assert result["entity_id"] == "input_boolean.test_switch"
        ha_client._request.assert_called_once()
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/input_boolean/config/test_switch" in call_args[0][1]
        assert call_args[1]["json"]["name"] == "Test Switch"
        assert call_args[1]["json"]["initial"] is True

    @pytest.mark.asyncio
    async def test_create_input_boolean_with_icon(self, ha_client):
        """Test input_boolean creation with icon."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_boolean(
            input_id="test_switch",
            name="Test",
            icon="mdi:toggle-switch",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["icon"] == "mdi:toggle-switch"

    @pytest.mark.asyncio
    async def test_create_input_boolean_error(self, ha_client):
        """Test input_boolean creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_input_boolean")

        result = await ha_client.create_input_boolean(
            input_id="test_switch",
            name="Test",
        )

        assert result["success"] is False
        assert result["input_id"] == "test_switch"
        assert "error" in result


class TestCreateInputNumber:
    """Tests for create_input_number."""

    @pytest.mark.asyncio
    async def test_create_input_number_success(self, ha_client):
        """Test successful input_number creation."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_number(
            input_id="test_number",
            name="Test Number",
            min_value=0.0,
            max_value=100.0,
            initial=50.0,
        )

        assert result["success"] is True
        assert result["input_id"] == "test_number"
        assert result["entity_id"] == "input_number.test_number"
        ha_client._request.assert_called_once()
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/input_number/config/test_number" in call_args[0][1]
        assert call_args[1]["json"]["name"] == "Test Number"
        assert call_args[1]["json"]["min"] == 0.0
        assert call_args[1]["json"]["max"] == 100.0
        assert call_args[1]["json"]["initial"] == 50.0

    @pytest.mark.asyncio
    async def test_create_input_number_with_all_options(self, ha_client):
        """Test input_number creation with all options."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_number(
            input_id="test_number",
            name="Test",
            min_value=0.0,
            max_value=100.0,
            initial=25.0,
            step=5.0,
            unit_of_measurement="%",
            mode="box",
            icon="mdi:percent",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["step"] == 5.0
        assert call_args[1]["json"]["unit_of_measurement"] == "%"
        assert call_args[1]["json"]["mode"] == "box"
        assert call_args[1]["json"]["icon"] == "mdi:percent"

    @pytest.mark.asyncio
    async def test_create_input_number_without_initial(self, ha_client):
        """Test input_number creation without initial value."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_number(
            input_id="test_number",
            name="Test",
            min_value=0.0,
            max_value=100.0,
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert "initial" not in call_args[1]["json"]

    @pytest.mark.asyncio
    async def test_create_input_number_error(self, ha_client):
        """Test input_number creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_input_number")

        result = await ha_client.create_input_number(
            input_id="test_number",
            name="Test",
            min_value=0.0,
            max_value=100.0,
        )

        assert result["success"] is False
        assert result["input_id"] == "test_number"
        assert "error" in result


# ─── input_text ───────────────────────────────────────────────────────────────


class TestCreateInputText:
    """Tests for create_input_text."""

    @pytest.mark.asyncio
    async def test_create_input_text_success(self, ha_client):
        """Test successful input_text creation."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_text(
            input_id="test_text",
            name="Test Text",
        )

        assert result["success"] is True
        assert result["input_id"] == "test_text"
        assert result["entity_id"] == "input_text.test_text"
        ha_client._request.assert_called_once()
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/input_text/config/test_text" in call_args[0][1]
        assert call_args[1]["json"]["name"] == "Test Text"

    @pytest.mark.asyncio
    async def test_create_input_text_with_all_options(self, ha_client):
        """Test input_text creation with all options."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_text(
            input_id="test_text",
            name="Test",
            min_length=1,
            max_length=50,
            pattern="[a-z]+",
            mode="password",
            initial="hello",
            icon="mdi:text",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        json_data = call_args[1]["json"]
        assert json_data["min"] == 1
        assert json_data["max"] == 50
        assert json_data["pattern"] == "[a-z]+"
        assert json_data["mode"] == "password"
        assert json_data["initial"] == "hello"
        assert json_data["icon"] == "mdi:text"

    @pytest.mark.asyncio
    async def test_create_input_text_error(self, ha_client):
        """Test input_text creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_input_text")

        result = await ha_client.create_input_text(
            input_id="test_text",
            name="Test",
        )

        assert result["success"] is False
        assert result["input_id"] == "test_text"
        assert "error" in result


# ─── input_select ─────────────────────────────────────────────────────────────


class TestCreateInputSelect:
    """Tests for create_input_select."""

    @pytest.mark.asyncio
    async def test_create_input_select_success(self, ha_client):
        """Test successful input_select creation."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_select(
            input_id="test_select",
            name="Test Select",
            options=["option1", "option2", "option3"],
        )

        assert result["success"] is True
        assert result["input_id"] == "test_select"
        assert result["entity_id"] == "input_select.test_select"
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/input_select/config/test_select" in call_args[0][1]
        json_data = call_args[1]["json"]
        assert json_data["options"] == ["option1", "option2", "option3"]

    @pytest.mark.asyncio
    async def test_create_input_select_with_initial(self, ha_client):
        """Test input_select creation with initial value."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_select(
            input_id="test_select",
            name="Test",
            options=["a", "b"],
            initial="b",
            icon="mdi:menu",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        json_data = call_args[1]["json"]
        assert json_data["initial"] == "b"
        assert json_data["icon"] == "mdi:menu"

    @pytest.mark.asyncio
    async def test_create_input_select_error(self, ha_client):
        """Test input_select creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_input_select")

        result = await ha_client.create_input_select(
            input_id="test_select",
            name="Test",
            options=["a"],
        )

        assert result["success"] is False
        assert result["input_id"] == "test_select"
        assert "error" in result


# ─── input_datetime ───────────────────────────────────────────────────────────


class TestCreateInputDatetime:
    """Tests for create_input_datetime."""

    @pytest.mark.asyncio
    async def test_create_input_datetime_success(self, ha_client):
        """Test successful input_datetime creation."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_datetime(
            input_id="test_datetime",
            name="Test Datetime",
        )

        assert result["success"] is True
        assert result["input_id"] == "test_datetime"
        assert result["entity_id"] == "input_datetime.test_datetime"
        call_args = ha_client._request.call_args
        json_data = call_args[1]["json"]
        assert json_data["has_date"] is True
        assert json_data["has_time"] is True

    @pytest.mark.asyncio
    async def test_create_input_datetime_date_only(self, ha_client):
        """Test input_datetime creation with date only."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_datetime(
            input_id="test_date",
            name="Test",
            has_date=True,
            has_time=False,
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        json_data = call_args[1]["json"]
        assert json_data["has_date"] is True
        assert json_data["has_time"] is False

    @pytest.mark.asyncio
    async def test_create_input_datetime_with_initial(self, ha_client):
        """Test input_datetime creation with initial value."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_datetime(
            input_id="test_datetime",
            name="Test",
            initial="2024-01-01 12:00:00",
            icon="mdi:clock",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        json_data = call_args[1]["json"]
        assert json_data["initial"] == "2024-01-01 12:00:00"
        assert json_data["icon"] == "mdi:clock"

    @pytest.mark.asyncio
    async def test_create_input_datetime_error(self, ha_client):
        """Test input_datetime creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_input_datetime")

        result = await ha_client.create_input_datetime(
            input_id="test_datetime",
            name="Test",
        )

        assert result["success"] is False
        assert result["input_id"] == "test_datetime"
        assert "error" in result


# ─── input_button ─────────────────────────────────────────────────────────────


class TestCreateInputButton:
    """Tests for create_input_button."""

    @pytest.mark.asyncio
    async def test_create_input_button_success(self, ha_client):
        """Test successful input_button creation."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_button(
            input_id="test_button",
            name="Test Button",
        )

        assert result["success"] is True
        assert result["input_id"] == "test_button"
        assert result["entity_id"] == "input_button.test_button"
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/input_button/config/test_button" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_input_button_with_icon(self, ha_client):
        """Test input_button creation with icon."""
        ha_client._request.return_value = {}

        result = await ha_client.create_input_button(
            input_id="test_button",
            name="Test",
            icon="mdi:gesture-tap-button",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        assert call_args[1]["json"]["icon"] == "mdi:gesture-tap-button"

    @pytest.mark.asyncio
    async def test_create_input_button_error(self, ha_client):
        """Test input_button creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_input_button")

        result = await ha_client.create_input_button(
            input_id="test_button",
            name="Test",
        )

        assert result["success"] is False
        assert result["input_id"] == "test_button"
        assert "error" in result


# ─── counter ──────────────────────────────────────────────────────────────────


class TestCreateCounter:
    """Tests for create_counter."""

    @pytest.mark.asyncio
    async def test_create_counter_success(self, ha_client):
        """Test successful counter creation."""
        ha_client._request.return_value = {}

        result = await ha_client.create_counter(
            input_id="test_counter",
            name="Test Counter",
        )

        assert result["success"] is True
        assert result["input_id"] == "test_counter"
        assert result["entity_id"] == "counter.test_counter"
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/counter/config/test_counter" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_counter_with_all_options(self, ha_client):
        """Test counter creation with all options."""
        ha_client._request.return_value = {}

        result = await ha_client.create_counter(
            input_id="test_counter",
            name="Test",
            initial=5,
            minimum=0,
            maximum=100,
            step=2,
            restore=False,
            icon="mdi:counter",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        json_data = call_args[1]["json"]
        assert json_data["initial"] == 5
        assert json_data["minimum"] == 0
        assert json_data["maximum"] == 100
        assert json_data["step"] == 2
        assert json_data["restore"] is False
        assert json_data["icon"] == "mdi:counter"

    @pytest.mark.asyncio
    async def test_create_counter_error(self, ha_client):
        """Test counter creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_counter")

        result = await ha_client.create_counter(
            input_id="test_counter",
            name="Test",
        )

        assert result["success"] is False
        assert result["input_id"] == "test_counter"
        assert "error" in result


# ─── timer ────────────────────────────────────────────────────────────────────


class TestCreateTimer:
    """Tests for create_timer."""

    @pytest.mark.asyncio
    async def test_create_timer_success(self, ha_client):
        """Test successful timer creation."""
        ha_client._request.return_value = {}

        result = await ha_client.create_timer(
            input_id="test_timer",
            name="Test Timer",
        )

        assert result["success"] is True
        assert result["input_id"] == "test_timer"
        assert result["entity_id"] == "timer.test_timer"
        call_args = ha_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/api/config/timer/config/test_timer" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_timer_with_all_options(self, ha_client):
        """Test timer creation with all options."""
        ha_client._request.return_value = {}

        result = await ha_client.create_timer(
            input_id="test_timer",
            name="Test",
            duration="00:05:00",
            restore=True,
            icon="mdi:timer",
        )

        assert result["success"] is True
        call_args = ha_client._request.call_args
        json_data = call_args[1]["json"]
        assert json_data["duration"] == "00:05:00"
        assert json_data["restore"] is True
        assert json_data["icon"] == "mdi:timer"

    @pytest.mark.asyncio
    async def test_create_timer_error(self, ha_client):
        """Test timer creation error handling."""
        ha_client._request.side_effect = HAClientError("API error", "create_timer")

        result = await ha_client.create_timer(
            input_id="test_timer",
            name="Test",
        )

        assert result["success"] is False
        assert result["input_id"] == "test_timer"
        assert "error" in result


# ─── delete_helper ────────────────────────────────────────────────────────────


class TestDeleteHelper:
    """Tests for delete_helper."""

    @pytest.mark.asyncio
    async def test_delete_helper_success(self, ha_client):
        """Test successful helper deletion."""
        ha_client._request.return_value = {}

        result = await ha_client.delete_helper("input_boolean", "test_switch")

        assert result["success"] is True
        assert result["entity_id"] == "input_boolean.test_switch"
        ha_client._request.assert_called_once_with(
            "DELETE",
            "/api/config/input_boolean/config/test_switch",
        )

    @pytest.mark.asyncio
    async def test_delete_helper_counter(self, ha_client):
        """Test deleting a counter helper."""
        ha_client._request.return_value = {}

        result = await ha_client.delete_helper("counter", "my_counter")

        assert result["success"] is True
        assert result["entity_id"] == "counter.my_counter"

    @pytest.mark.asyncio
    async def test_delete_helper_error(self, ha_client):
        """Test helper deletion error handling."""
        ha_client._request.side_effect = HAClientError("Not found", "delete_helper")

        result = await ha_client.delete_helper("input_text", "nonexistent")

        assert result["success"] is False
        assert result["entity_id"] == "input_text.nonexistent"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_helper_invalid_domain(self, ha_client):
        """Test deletion with invalid helper domain."""
        result = await ha_client.delete_helper("light", "my_light")

        assert result["success"] is False
        assert "error" in result
        assert "not a valid helper domain" in result["error"].lower()


# ─── list_helpers ─────────────────────────────────────────────────────────────


class TestListHelpers:
    """Tests for list_helpers."""

    @pytest.mark.asyncio
    async def test_list_helpers_returns_only_helper_entities(self, ha_client):
        """Test that list_helpers filters to helper domains only."""
        ha_client.list_entities.return_value = [
            {
                "entity_id": "input_boolean.vacation_mode",
                "state": "off",
                "name": "Vacation Mode",
                "attributes": {"friendly_name": "Vacation Mode", "icon": "mdi:beach"},
            },
            {
                "entity_id": "light.living_room",
                "state": "on",
                "name": "Living Room",
                "attributes": {},
            },
            {
                "entity_id": "counter.visitors",
                "state": "5",
                "name": "Visitors",
                "attributes": {"friendly_name": "Visitors"},
            },
        ]

        result = await ha_client.list_helpers()

        assert len(result) == 2
        entity_ids = [h["entity_id"] for h in result]
        assert "input_boolean.vacation_mode" in entity_ids
        assert "counter.visitors" in entity_ids
        assert "light.living_room" not in entity_ids

    @pytest.mark.asyncio
    async def test_list_helpers_empty(self, ha_client):
        """Test list_helpers with no helper entities."""
        ha_client.list_entities.return_value = [
            {
                "entity_id": "light.kitchen",
                "state": "off",
                "name": "Kitchen",
                "attributes": {},
            },
        ]

        result = await ha_client.list_helpers()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_helpers_includes_domain_field(self, ha_client):
        """Test that each helper entry includes a domain field."""
        ha_client.list_entities.return_value = [
            {
                "entity_id": "timer.cooking",
                "state": "idle",
                "name": "Cooking Timer",
                "attributes": {"friendly_name": "Cooking Timer", "duration": "00:30:00"},
            },
        ]

        result = await ha_client.list_helpers()

        assert len(result) == 1
        assert result[0]["domain"] == "timer"
        assert result[0]["entity_id"] == "timer.cooking"
        assert result[0]["name"] == "Cooking Timer"
