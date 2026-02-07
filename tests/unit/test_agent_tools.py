"""Unit tests for agent delegation tools.

TDD: Testing tools that the Architect uses to delegate to specialist agents
and retrieve enriched data.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetEntityHistoryBasic:
    """Tests for get_entity_history tool — basic mode."""

    @pytest.mark.asyncio
    async def test_basic_history_returns_summary(self):
        """Test basic history returns last 5 changes."""
        from src.tools.agent_tools import get_entity_history

        mock_mcp = MagicMock()
        mock_mcp.get_history = AsyncMock(return_value={
            "states": [
                {"state": "22.5", "last_changed": "2026-02-06T10:00:00Z"},
                {"state": "23.0", "last_changed": "2026-02-06T11:00:00Z"},
                {"state": "22.8", "last_changed": "2026-02-06T12:00:00Z"},
            ],
            "count": 3,
        })

        with patch("src.ha.get_ha_client", return_value=mock_mcp):
            result = await get_entity_history.ainvoke({
                "entity_id": "sensor.temperature",
                "hours": 24,
            })

        assert "sensor.temperature" in result
        assert "3 state changes" in result
        assert "22.5" in result

    @pytest.mark.asyncio
    async def test_basic_history_no_data(self):
        """Test when no history is available."""
        from src.tools.agent_tools import get_entity_history

        mock_mcp = MagicMock()
        mock_mcp.get_history = AsyncMock(return_value={"states": [], "count": 0})

        with patch("src.ha.get_ha_client", return_value=mock_mcp):
            result = await get_entity_history.ainvoke({
                "entity_id": "sensor.missing",
                "hours": 24,
            })

        assert "no history" in result.lower()

    @pytest.mark.asyncio
    async def test_basic_caps_hours_at_168(self):
        """Test that hours are capped at 168 (1 week)."""
        from src.tools.agent_tools import get_entity_history

        mock_mcp = MagicMock()
        mock_mcp.get_history = AsyncMock(return_value={
            "states": [{"state": "on", "last_changed": "2026-02-06T10:00:00Z"}],
            "count": 1,
        })

        with patch("src.ha.get_ha_client", return_value=mock_mcp):
            await get_entity_history.ainvoke({
                "entity_id": "light.test",
                "hours": 500,
            })

        # Verify MCP was called with capped hours
        mock_mcp.get_history.assert_called_once_with(entity_id="light.test", hours=168)


class TestGetEntityHistoryDetailed:
    """Tests for get_entity_history tool — detailed mode."""

    @pytest.mark.asyncio
    async def test_detailed_includes_state_distribution(self):
        """Test detailed mode includes state distribution."""
        from src.tools.agent_tools import get_entity_history

        mock_mcp = MagicMock()
        mock_mcp.get_history = AsyncMock(return_value={
            "states": [
                {"state": "on", "last_changed": "2026-02-06T10:00:00Z"},
                {"state": "off", "last_changed": "2026-02-06T11:00:00Z"},
                {"state": "on", "last_changed": "2026-02-06T12:00:00Z"},
                {"state": "off", "last_changed": "2026-02-06T13:00:00Z"},
            ],
            "count": 4,
        })

        with patch("src.ha.get_ha_client", return_value=mock_mcp):
            result = await get_entity_history.ainvoke({
                "entity_id": "light.living_room",
                "hours": 24,
                "detailed": True,
            })

        assert "Detailed History" in result
        assert "State Distribution" in result
        assert "on: 2" in result
        assert "off: 2" in result

    @pytest.mark.asyncio
    async def test_detailed_shows_up_to_20_changes(self):
        """Test detailed mode shows up to 20 recent changes."""
        from src.tools.agent_tools import get_entity_history

        mock_mcp = MagicMock()
        states = [
            {"state": f"val_{i}", "last_changed": f"2026-02-06T{i:02d}:00:00Z"}
            for i in range(25)
        ]
        mock_mcp.get_history = AsyncMock(return_value={
            "states": states,
            "count": 25,
        })

        with patch("src.ha.get_ha_client", return_value=mock_mcp):
            result = await get_entity_history.ainvoke({
                "entity_id": "sensor.test",
                "hours": 48,
                "detailed": True,
            })

        assert "20 of 25" in result
        # Should show val_5 through val_24 (last 20)
        assert ": val_24" in result
        assert ": val_5" in result
        # First 5 should not appear (only last 20 of 25 shown)
        assert ": val_3\n" not in result and "val_3\n" not in result

    @pytest.mark.asyncio
    async def test_detailed_detects_gaps(self):
        """Test detailed mode detects data gaps."""
        from src.tools.agent_tools import get_entity_history

        mock_mcp = MagicMock()
        mock_mcp.get_history = AsyncMock(return_value={
            "states": [
                {"state": "22.0", "last_changed": "2026-02-01T10:00:00Z"},
                {"state": "22.5", "last_changed": "2026-02-01T10:30:00Z"},
                # 48-hour gap
                {"state": "23.0", "last_changed": "2026-02-03T10:30:00Z"},
                {"state": "22.8", "last_changed": "2026-02-03T11:00:00Z"},
            ],
            "count": 4,
        })

        with patch("src.ha.get_ha_client", return_value=mock_mcp):
            result = await get_entity_history.ainvoke({
                "entity_id": "sensor.energy",
                "hours": 72,
                "detailed": True,
            })

        assert "Data Gaps Detected" in result
        assert "no data" in result.lower()

    @pytest.mark.asyncio
    async def test_detailed_no_gaps_when_continuous(self):
        """Test that no gaps are reported for continuous data."""
        from src.tools.agent_tools import get_entity_history

        mock_mcp = MagicMock()
        mock_mcp.get_history = AsyncMock(return_value={
            "states": [
                {"state": "on", "last_changed": "2026-02-06T10:00:00Z"},
                {"state": "off", "last_changed": "2026-02-06T10:30:00Z"},
                {"state": "on", "last_changed": "2026-02-06T11:00:00Z"},
            ],
            "count": 3,
        })

        with patch("src.ha.get_ha_client", return_value=mock_mcp):
            result = await get_entity_history.ainvoke({
                "entity_id": "light.test",
                "hours": 24,
                "detailed": True,
            })

        assert "None detected" in result

    @pytest.mark.asyncio
    async def test_detailed_shows_first_last_timestamps(self):
        """Test detailed mode shows first and last recorded timestamps."""
        from src.tools.agent_tools import get_entity_history

        mock_mcp = MagicMock()
        mock_mcp.get_history = AsyncMock(return_value={
            "states": [
                {"state": "on", "last_changed": "2026-02-06T08:00:00Z"},
                {"state": "off", "last_changed": "2026-02-06T20:00:00Z"},
            ],
            "count": 2,
        })

        with patch("src.ha.get_ha_client", return_value=mock_mcp):
            result = await get_entity_history.ainvoke({
                "entity_id": "switch.pump",
                "hours": 24,
                "detailed": True,
            })

        assert "First recorded" in result
        assert "Last recorded" in result
        assert "08:00:00" in result
        assert "20:00:00" in result


class TestDiagnoseIssueTool:
    """Tests for diagnose_issue delegation tool."""

    @pytest.mark.asyncio
    async def test_diagnose_issue_delegates_to_ds(self):
        """Test that diagnose_issue correctly delegates to DataScientistWorkflow."""
        from unittest.mock import PropertyMock

        from src.tools.agent_tools import diagnose_issue

        # Mock AnalysisState returned by workflow
        mock_state = MagicMock()
        mock_state.insights = [
            {
                "title": "Data Gap Detected",
                "description": "Sensor stopped reporting for 12 hours",
                "impact": "high",
                "confidence": 0.9,
            }
        ]
        mock_state.recommendations = ["Check integration connection"]
        mock_state.entity_ids = ["sensor.energy_charger"]
        mock_state.automation_suggestion = None

        # Mock the workflow
        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_state)

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
        ):
            result = await diagnose_issue.ainvoke({
                "entity_ids": ["sensor.energy_charger"],
                "diagnostic_context": "HA logs show connection timeout errors",
                "instructions": "Analyze data gaps and identify root cause",
                "hours": 72,
            })

        assert "Data Gap Detected" in result
        assert "Check integration connection" in result
        mock_workflow.run_analysis.assert_called_once()

        # Verify diagnostic parameters were passed
        call_kwargs = mock_workflow.run_analysis.call_args[1]
        assert call_kwargs["diagnostic_context"] == "HA logs show connection timeout errors"
        assert call_kwargs["custom_query"] == "Analyze data gaps and identify root cause"

    @pytest.mark.asyncio
    async def test_diagnose_issue_no_findings(self):
        """Test diagnose_issue when no issues found."""
        from src.tools.agent_tools import diagnose_issue

        mock_state = MagicMock()
        mock_state.insights = []
        mock_state.recommendations = []
        mock_state.entity_ids = ["sensor.test"]
        mock_state.automation_suggestion = None

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
        ):
            result = await diagnose_issue.ainvoke({
                "entity_ids": ["sensor.test"],
                "diagnostic_context": "No errors in logs",
                "instructions": "Check for anomalies",
            })

        assert "functioning normally" in result.lower() or "didn't identify" in result.lower()

    @pytest.mark.asyncio
    async def test_diagnose_issue_handles_error(self):
        """Test diagnose_issue error handling."""
        from src.tools.agent_tools import diagnose_issue

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(side_effect=Exception("DB connection failed"))

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
        ):
            result = await diagnose_issue.ainvoke({
                "entity_ids": ["sensor.test"],
                "diagnostic_context": "Some context",
                "instructions": "Investigate",
            })

        assert "failed" in result.lower()

    @pytest.mark.asyncio
    async def test_diagnose_issue_caps_hours(self):
        """Test that hours are capped at 168."""
        from src.tools.agent_tools import diagnose_issue

        mock_state = MagicMock()
        mock_state.insights = []
        mock_state.recommendations = []
        mock_state.entity_ids = ["sensor.test"]
        mock_state.automation_suggestion = None

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
        ):
            await diagnose_issue.ainvoke({
                "entity_ids": ["sensor.test"],
                "diagnostic_context": "context",
                "instructions": "investigate",
                "hours": 500,
            })

        call_kwargs = mock_workflow.run_analysis.call_args[1]
        assert call_kwargs["hours"] == 168
