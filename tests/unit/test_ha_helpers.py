"""Unit tests for HA helpers module.

Tests HelperMixin methods with mocked ws_command.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ha.base import HAClientError
from src.ha.helpers import HelperMixin

WS_COMMAND_PATH = "src.ha.helpers.ws_command"


class MockHAClient(HelperMixin):
    """Mock HA client that inherits HelperMixin for testing."""

    def __init__(self):
        self._request = AsyncMock()
        self.list_entities = AsyncMock()
        self.config = MagicMock()
        self.config.ha_token = "fake-token"

    def _get_ws_url(self) -> str:
        return "ws://ha.local:8123/api/websocket"


@pytest.fixture
def ha_client():
    """Create a mock HA client."""
    return MockHAClient()


class TestCreateInputBoolean:
    """Tests for create_input_boolean."""

    @pytest.mark.asyncio
    async def test_create_input_boolean_success(self, ha_client):
        """Test successful input_boolean creation via WS."""
        ws_result = {"id": "test_switch", "name": "Test Switch", "initial": True}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_boolean(
                input_id="test_switch",
                name="Test Switch",
                initial=True,
            )

        assert result["success"] is True
        assert result["input_id"] == "test_switch"
        assert result["entity_id"] == "input_boolean.test_switch"
        mock_ws.assert_called_once()
        call_kwargs = mock_ws.call_args
        assert call_kwargs[0][2] == "input_boolean/create"
        assert call_kwargs[1]["name"] == "Test Switch"
        assert call_kwargs[1]["initial"] is True
        assert "id" not in call_kwargs[1]

    @pytest.mark.asyncio
    async def test_create_input_boolean_uses_ha_slug(self, ha_client):
        """Test that entity_id uses the slug HA returns, not the caller's input_id."""
        ws_result = {"id": "ha_generated_slug", "name": "Test Switch"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result):
            result = await ha_client.create_input_boolean(
                input_id="my_custom_id",
                name="Test Switch",
            )

        assert result["input_id"] == "ha_generated_slug"
        assert result["entity_id"] == "input_boolean.ha_generated_slug"

    @pytest.mark.asyncio
    async def test_create_input_boolean_with_icon(self, ha_client):
        """Test input_boolean creation with icon."""
        ws_result = {"id": "test_switch", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_boolean(
                input_id="test_switch",
                name="Test",
                icon="mdi:toggle-switch",
            )

        assert result["success"] is True
        assert mock_ws.call_args[1]["icon"] == "mdi:toggle-switch"

    @pytest.mark.asyncio
    async def test_create_input_boolean_error(self, ha_client):
        """Test input_boolean creation error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("API error", "ws_command"),
        ):
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
        """Test successful input_number creation via WS."""
        ws_result = {"id": "test_number", "name": "Test Number", "min": 0.0, "max": 100.0}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_number(
                input_id="test_number",
                name="Test Number",
                min=0.0,
                max=100.0,
                initial=50.0,
            )

        assert result["success"] is True
        assert result["input_id"] == "test_number"
        assert result["entity_id"] == "input_number.test_number"
        mock_ws.assert_called_once()
        kw = mock_ws.call_args[1]
        assert kw["name"] == "Test Number"
        assert kw["min"] == 0.0
        assert kw["max"] == 100.0
        assert kw["initial"] == 50.0
        assert "id" not in kw

    @pytest.mark.asyncio
    async def test_create_input_number_with_all_options(self, ha_client):
        """Test input_number creation with all options."""
        ws_result = {"id": "test_number", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_number(
                input_id="test_number",
                name="Test",
                min=0.0,
                max=100.0,
                initial=25.0,
                step=5.0,
                unit_of_measurement="%",
                mode="box",
                icon="mdi:percent",
            )

        assert result["success"] is True
        kw = mock_ws.call_args[1]
        assert kw["step"] == 5.0
        assert kw["unit_of_measurement"] == "%"
        assert kw["mode"] == "box"
        assert kw["icon"] == "mdi:percent"

    @pytest.mark.asyncio
    async def test_create_input_number_without_initial(self, ha_client):
        """Test input_number creation without initial value."""
        ws_result = {"id": "test_number", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_number(
                input_id="test_number",
                name="Test",
                min=0.0,
                max=100.0,
            )

        assert result["success"] is True
        assert "initial" not in mock_ws.call_args[1]

    @pytest.mark.asyncio
    async def test_create_input_number_error(self, ha_client):
        """Test input_number creation error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("API error", "ws_command"),
        ):
            result = await ha_client.create_input_number(
                input_id="test_number",
                name="Test",
                min=0.0,
                max=100.0,
            )

        assert result["success"] is False
        assert result["input_id"] == "test_number"
        assert "error" in result


# ─── input_text ───────────────────────────────────────────────────────────────


class TestCreateInputText:
    """Tests for create_input_text."""

    @pytest.mark.asyncio
    async def test_create_input_text_success(self, ha_client):
        """Test successful input_text creation via WS."""
        ws_result = {"id": "test_text", "name": "Test Text"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_text(
                input_id="test_text",
                name="Test Text",
            )

        assert result["success"] is True
        assert result["input_id"] == "test_text"
        assert result["entity_id"] == "input_text.test_text"
        assert mock_ws.call_args[0][2] == "input_text/create"
        assert mock_ws.call_args[1]["name"] == "Test Text"
        assert "id" not in mock_ws.call_args[1]

    @pytest.mark.asyncio
    async def test_create_input_text_with_all_options(self, ha_client):
        """Test input_text creation with all options."""
        ws_result = {"id": "test_text", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
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
        kw = mock_ws.call_args[1]
        assert kw["min"] == 1
        assert kw["max"] == 50
        assert kw["pattern"] == "[a-z]+"
        assert kw["mode"] == "password"
        assert kw["initial"] == "hello"
        assert kw["icon"] == "mdi:text"

    @pytest.mark.asyncio
    async def test_create_input_text_error(self, ha_client):
        """Test input_text creation error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("API error", "ws_command"),
        ):
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
        """Test successful input_select creation via WS."""
        ws_result = {"id": "test_select", "name": "Test Select"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_select(
                input_id="test_select",
                name="Test Select",
                options=["option1", "option2", "option3"],
            )

        assert result["success"] is True
        assert result["entity_id"] == "input_select.test_select"
        assert mock_ws.call_args[0][2] == "input_select/create"
        assert mock_ws.call_args[1]["options"] == ["option1", "option2", "option3"]
        assert "id" not in mock_ws.call_args[1]

    @pytest.mark.asyncio
    async def test_create_input_select_with_initial(self, ha_client):
        """Test input_select creation with initial value."""
        ws_result = {"id": "test_select", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_select(
                input_id="test_select",
                name="Test",
                options=["a", "b"],
                initial="b",
                icon="mdi:menu",
            )

        assert result["success"] is True
        kw = mock_ws.call_args[1]
        assert kw["initial"] == "b"
        assert kw["icon"] == "mdi:menu"

    @pytest.mark.asyncio
    async def test_create_input_select_error(self, ha_client):
        """Test input_select creation error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("API error", "ws_command"),
        ):
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
        """Test successful input_datetime creation via WS."""
        ws_result = {"id": "test_datetime", "name": "Test Datetime"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_datetime(
                input_id="test_datetime",
                name="Test Datetime",
            )

        assert result["success"] is True
        assert result["entity_id"] == "input_datetime.test_datetime"
        kw = mock_ws.call_args[1]
        assert kw["has_date"] is True
        assert kw["has_time"] is True
        assert "id" not in kw

    @pytest.mark.asyncio
    async def test_create_input_datetime_date_only(self, ha_client):
        """Test input_datetime creation with date only."""
        ws_result = {"id": "test_date", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_datetime(
                input_id="test_date",
                name="Test",
                has_date=True,
                has_time=False,
            )

        assert result["success"] is True
        kw = mock_ws.call_args[1]
        assert kw["has_date"] is True
        assert kw["has_time"] is False

    @pytest.mark.asyncio
    async def test_create_input_datetime_with_initial(self, ha_client):
        """Test input_datetime creation with initial value."""
        ws_result = {"id": "test_datetime", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_datetime(
                input_id="test_datetime",
                name="Test",
                initial="2024-01-01 12:00:00",
                icon="mdi:clock",
            )

        assert result["success"] is True
        kw = mock_ws.call_args[1]
        assert kw["initial"] == "2024-01-01 12:00:00"
        assert kw["icon"] == "mdi:clock"

    @pytest.mark.asyncio
    async def test_create_input_datetime_error(self, ha_client):
        """Test input_datetime creation error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("API error", "ws_command"),
        ):
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
        """Test successful input_button creation via WS."""
        ws_result = {"id": "test_button", "name": "Test Button"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_button(
                input_id="test_button",
                name="Test Button",
            )

        assert result["success"] is True
        assert result["entity_id"] == "input_button.test_button"
        assert mock_ws.call_args[0][2] == "input_button/create"
        assert "id" not in mock_ws.call_args[1]

    @pytest.mark.asyncio
    async def test_create_input_button_with_icon(self, ha_client):
        """Test input_button creation with icon."""
        ws_result = {"id": "test_button", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_input_button(
                input_id="test_button",
                name="Test",
                icon="mdi:gesture-tap-button",
            )

        assert result["success"] is True
        assert mock_ws.call_args[1]["icon"] == "mdi:gesture-tap-button"

    @pytest.mark.asyncio
    async def test_create_input_button_error(self, ha_client):
        """Test input_button creation error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("API error", "ws_command"),
        ):
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
        """Test successful counter creation via WS."""
        ws_result = {"id": "test_counter", "name": "Test Counter"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_counter(
                input_id="test_counter",
                name="Test Counter",
            )

        assert result["success"] is True
        assert result["entity_id"] == "counter.test_counter"
        assert mock_ws.call_args[0][2] == "counter/create"
        assert "id" not in mock_ws.call_args[1]

    @pytest.mark.asyncio
    async def test_create_counter_with_all_options(self, ha_client):
        """Test counter creation with all options."""
        ws_result = {"id": "test_counter", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
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
        kw = mock_ws.call_args[1]
        assert kw["initial"] == 5
        assert kw["minimum"] == 0
        assert kw["maximum"] == 100
        assert kw["step"] == 2
        assert kw["restore"] is False
        assert kw["icon"] == "mdi:counter"

    @pytest.mark.asyncio
    async def test_create_counter_error(self, ha_client):
        """Test counter creation error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("API error", "ws_command"),
        ):
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
        """Test successful timer creation via WS."""
        ws_result = {"id": "test_timer", "name": "Test Timer"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_timer(
                input_id="test_timer",
                name="Test Timer",
            )

        assert result["success"] is True
        assert result["entity_id"] == "timer.test_timer"
        assert mock_ws.call_args[0][2] == "timer/create"
        assert "id" not in mock_ws.call_args[1]

    @pytest.mark.asyncio
    async def test_create_timer_with_all_options(self, ha_client):
        """Test timer creation with all options."""
        ws_result = {"id": "test_timer", "name": "Test"}
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=ws_result) as mock_ws:
            result = await ha_client.create_timer(
                input_id="test_timer",
                name="Test",
                duration="00:05:00",
                restore=True,
                icon="mdi:timer",
            )

        assert result["success"] is True
        kw = mock_ws.call_args[1]
        assert kw["duration"] == "00:05:00"
        assert kw["restore"] is True
        assert kw["icon"] == "mdi:timer"

    @pytest.mark.asyncio
    async def test_create_timer_error(self, ha_client):
        """Test timer creation error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("API error", "ws_command"),
        ):
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
        """Test successful helper deletion via WS list+delete."""
        list_result = [{"id": "test_switch", "name": "Test Switch"}]
        with patch(
            WS_COMMAND_PATH, new_callable=AsyncMock, side_effect=[list_result, None]
        ) as mock_ws:
            result = await ha_client.delete_helper("input_boolean", "test_switch")

        assert result["success"] is True
        assert result["entity_id"] == "input_boolean.test_switch"
        assert mock_ws.call_count == 2
        assert mock_ws.call_args_list[0][0][2] == "input_boolean/list"
        assert mock_ws.call_args_list[1][0][2] == "input_boolean/delete"
        assert mock_ws.call_args_list[1][1]["input_boolean_id"] == "test_switch"

    @pytest.mark.asyncio
    async def test_delete_helper_counter(self, ha_client):
        """Test deleting a counter helper."""
        list_result = [{"id": "my_counter", "name": "My Counter"}]
        with patch(
            WS_COMMAND_PATH, new_callable=AsyncMock, side_effect=[list_result, None]
        ) as mock_ws:
            result = await ha_client.delete_helper("counter", "my_counter")

        assert result["success"] is True
        assert result["entity_id"] == "counter.my_counter"
        assert mock_ws.call_args_list[1][1]["counter_id"] == "my_counter"

    @pytest.mark.asyncio
    async def test_delete_helper_not_found(self, ha_client):
        """Test deletion when helper not found in WS list."""
        with patch(WS_COMMAND_PATH, new_callable=AsyncMock, return_value=[]):
            result = await ha_client.delete_helper("input_text", "nonexistent")

        assert result["success"] is False
        assert result["entity_id"] == "input_text.nonexistent"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_delete_helper_error(self, ha_client):
        """Test helper deletion WS error handling."""
        with patch(
            WS_COMMAND_PATH,
            new_callable=AsyncMock,
            side_effect=HAClientError("WS error", "ws_command"),
        ):
            result = await ha_client.delete_helper("input_text", "broken")

        assert result["success"] is False
        assert result["entity_id"] == "input_text.broken"
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
