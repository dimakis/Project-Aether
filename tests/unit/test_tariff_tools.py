"""Unit tests for electricity tariff tools.

TDD: Tests written first (red), then implementation (green).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestUpdateElectricityTariffs:
    """Tests for update_electricity_tariffs tool."""

    @pytest.mark.asyncio
    async def test_update_tariffs_calls_seek_approval(self):
        """Updating tariffs creates a HITL proposal via seek_approval."""
        from src.tools.tariff_tools import update_electricity_tariffs

        with patch(
            "src.tools.tariff_tools.seek_approval",
            new_callable=AsyncMock,
        ) as mock_seek:
            mock_seek.ainvoke = AsyncMock(return_value="Proposal submitted")

            await update_electricity_tariffs.ainvoke(
                {
                    "day_rate": 25.84,
                    "night_rate": 13.54,
                    "peak_rate": 29.18,
                    "plan_name": "Yuno ETV06",
                }
            )

        mock_seek.ainvoke.assert_called_once()
        call_args = mock_seek.ainvoke.call_args[0][0]
        assert call_args["action_type"] == "entity_command"
        assert "25.84" in call_args["description"]
        assert "13.54" in call_args["description"]
        assert "29.18" in call_args["description"]

    @pytest.mark.asyncio
    async def test_update_tariffs_includes_plan_name_in_description(self):
        """Plan name appears in the proposal description."""
        from src.tools.tariff_tools import update_electricity_tariffs

        with patch(
            "src.tools.tariff_tools.seek_approval",
            new_callable=AsyncMock,
        ) as mock_seek:
            mock_seek.ainvoke = AsyncMock(return_value="Proposal submitted")

            await update_electricity_tariffs.ainvoke(
                {
                    "day_rate": 26.37,
                    "night_rate": 15.73,
                    "peak_rate": 29.54,
                    "plan_name": "Yuno Rural Plan",
                }
            )

        call_args = mock_seek.ainvoke.call_args[0][0]
        assert "Yuno Rural Plan" in call_args["description"]

    @pytest.mark.asyncio
    async def test_update_tariffs_validates_positive_rates(self):
        """Negative rates are rejected without creating a proposal."""
        from src.tools.tariff_tools import update_electricity_tariffs

        with patch(
            "src.tools.tariff_tools.seek_approval",
            new_callable=AsyncMock,
        ) as mock_seek:
            mock_seek.ainvoke = AsyncMock(return_value="Proposal submitted")

            result = await update_electricity_tariffs.ainvoke(
                {
                    "day_rate": -5.0,
                    "night_rate": 13.54,
                    "peak_rate": 29.18,
                }
            )

        assert "must be positive" in result.lower() or "invalid" in result.lower()
        mock_seek.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_tariffs_default_plan_name(self):
        """Plan name defaults to a sensible value when omitted."""
        from src.tools.tariff_tools import update_electricity_tariffs

        with patch(
            "src.tools.tariff_tools.seek_approval",
            new_callable=AsyncMock,
        ) as mock_seek:
            mock_seek.ainvoke = AsyncMock(return_value="Proposal submitted")

            await update_electricity_tariffs.ainvoke(
                {
                    "day_rate": 25.84,
                    "night_rate": 13.54,
                    "peak_rate": 29.18,
                }
            )

        mock_seek.ainvoke.assert_called_once()
        call_args = mock_seek.ainvoke.call_args[0][0]
        assert call_args["description"]  # non-empty


class TestSetupElectricityTariffs:
    """Tests for setup_electricity_tariffs tool."""

    @pytest.mark.asyncio
    async def test_setup_creates_helpers_via_seek_approval(self):
        """Setup creates helper proposals for all tariff entities."""
        from src.tools.tariff_tools import setup_electricity_tariffs

        calls: list[dict] = []

        async def _capture_call(args: dict) -> str:
            calls.append(args)
            return "Proposal submitted"

        with patch(
            "src.tools.tariff_tools.seek_approval",
            new_callable=AsyncMock,
        ) as mock_seek:
            mock_seek.ainvoke = AsyncMock(side_effect=_capture_call)

            await setup_electricity_tariffs.ainvoke(
                {
                    "day_rate": 25.84,
                    "night_rate": 13.54,
                    "peak_rate": 29.18,
                    "plan_name": "Yuno ETV06",
                }
            )

        # Should create multiple proposals (helpers + automation)
        assert mock_seek.ainvoke.call_count >= 2
        action_types = {c["action_type"] for c in calls}
        assert "helper" in action_types
        assert "automation" in action_types

    @pytest.mark.asyncio
    async def test_setup_includes_automation_with_time_triggers(self):
        """Setup creates an automation with time-based triggers."""
        from src.tools.tariff_tools import setup_electricity_tariffs

        calls: list[dict] = []

        async def _capture_call(args: dict) -> str:
            calls.append(args)
            return "Proposal submitted"

        with patch(
            "src.tools.tariff_tools.seek_approval",
            new_callable=AsyncMock,
        ) as mock_seek:
            mock_seek.ainvoke = AsyncMock(side_effect=_capture_call)

            await setup_electricity_tariffs.ainvoke(
                {
                    "day_rate": 25.84,
                    "night_rate": 13.54,
                    "peak_rate": 29.18,
                }
            )

        automation_calls = [c for c in calls if c["action_type"] == "automation"]
        assert len(automation_calls) == 1
        auto = automation_calls[0]
        assert auto.get("trigger") is not None
        assert auto.get("actions") is not None


class TestGetTariffRatesFromHA:
    """Tests for reading tariff rates from HA entities."""

    @pytest.mark.asyncio
    async def test_get_tariff_rates_returns_configured_rates(self):
        """When tariff entities exist, returns structured rates."""
        from src.tools.tariff_tools import get_tariff_rates

        mock_ha = MagicMock()
        mock_ha.get_entity = AsyncMock(
            side_effect=lambda eid, **kw: {
                "input_number.electricity_rate_day": {
                    "entity_id": "input_number.electricity_rate_day",
                    "state": "25.84",
                },
                "input_number.electricity_rate_night": {
                    "entity_id": "input_number.electricity_rate_night",
                    "state": "13.54",
                },
                "input_number.electricity_rate_peak": {
                    "entity_id": "input_number.electricity_rate_peak",
                    "state": "29.18",
                },
                "input_number.electricity_rate_current": {
                    "entity_id": "input_number.electricity_rate_current",
                    "state": "25.84",
                },
                "input_text.electricity_plan_name": {
                    "entity_id": "input_text.electricity_plan_name",
                    "state": "Yuno ETV06",
                },
                "input_select.electricity_tariff_period": {
                    "entity_id": "input_select.electricity_tariff_period",
                    "state": "day",
                },
            }.get(eid)
        )

        result = await get_tariff_rates(mock_ha)

        assert result is not None
        assert result["configured"] is True
        assert result["rates"]["day"]["rate"] == 25.84
        assert result["rates"]["night"]["rate"] == 13.54
        assert result["rates"]["peak"]["rate"] == 29.18
        assert result["current_rate"] == 25.84
        assert result["current_period"] == "day"
        assert result["plan_name"] == "Yuno ETV06"

    @pytest.mark.asyncio
    async def test_get_tariff_rates_returns_not_configured(self):
        """When tariff entities don't exist, returns configured=False."""
        from src.tools.tariff_tools import get_tariff_rates

        mock_ha = MagicMock()
        mock_ha.get_entity = AsyncMock(return_value=None)

        result = await get_tariff_rates(mock_ha)

        assert result["configured"] is False
