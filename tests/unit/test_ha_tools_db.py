"""Tests for DB-backed HA tools.

Verifies that list_entities_by_domain, search_entities, get_domain_summary,
list_automations, get_automation_config, and get_script_config read from the
database rather than calling HA directly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_entity(entity_id: str, domain: str, name: str, state: str = "on") -> MagicMock:
    """Create a mock HAEntity."""
    e = MagicMock()
    e.entity_id = entity_id
    e.domain = domain
    e.name = name
    e.state = state
    return e


def _mock_automation(
    entity_id: str, alias: str, state: str = "on", has_config: bool = True,
) -> MagicMock:
    """Create a mock HAAutomation."""
    a = MagicMock()
    a.entity_id = entity_id
    a.alias = alias
    a.state = state
    a.mode = "single"
    a.config = {"trigger": [{"platform": "sun"}]} if has_config else None
    return a


@pytest.mark.asyncio
class TestListEntitiesByDomainDB:
    """list_entities_by_domain should read from EntityRepository."""

    async def test_returns_entity_ids(self):
        from src.tools.ha_tools import list_entities_by_domain

        mock_repo = AsyncMock()
        mock_repo.list_by_domain = AsyncMock(return_value=[
            _mock_entity("light.living_room", "light", "Living Room"),
            _mock_entity("light.bedroom", "light", "Bedroom"),
        ])

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.EntityRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await list_entities_by_domain.ainvoke({"domain": "light"})

        assert "light.living_room" in result
        assert "light.bedroom" in result
        mock_repo.list_by_domain.assert_called_once_with("light")

    async def test_state_filter(self):
        from src.tools.ha_tools import list_entities_by_domain

        mock_repo = AsyncMock()
        mock_repo.list_by_domain = AsyncMock(return_value=[
            _mock_entity("light.living_room", "light", "Living Room", "on"),
            _mock_entity("light.bedroom", "light", "Bedroom", "off"),
        ])

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.EntityRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await list_entities_by_domain.ainvoke({"domain": "light", "state_filter": "off"})

        assert "light.bedroom" in result
        assert "light.living_room" not in result


@pytest.mark.asyncio
class TestSearchEntitiesDB:
    """search_entities should read from EntityRepository."""

    async def test_returns_matches(self):
        from src.tools.ha_tools import search_entities

        mock_repo = AsyncMock()
        mock_repo.search = AsyncMock(return_value=[
            _mock_entity("light.living_room", "light", "Living Room"),
        ])

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.EntityRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await search_entities.ainvoke({"query": "living"})

        assert "light.living_room" in result
        mock_repo.search.assert_called_once_with("living")


@pytest.mark.asyncio
class TestGetDomainSummaryDB:
    """get_domain_summary should read from EntityRepository."""

    async def test_returns_counts(self):
        from src.tools.ha_tools import get_domain_summary

        mock_repo = AsyncMock()
        mock_repo.count = AsyncMock(return_value=5)
        mock_repo.list_all = AsyncMock(return_value=[
            _mock_entity("light.a", "light", "A", "on"),
            _mock_entity("light.b", "light", "B", "on"),
            _mock_entity("light.c", "light", "C", "off"),
            _mock_entity("light.d", "light", "D", "off"),
            _mock_entity("light.e", "light", "E", "on"),
        ])

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.EntityRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_domain_summary.ainvoke({"domain": "light"})

        assert "5" in result
        assert "light" in result


@pytest.mark.asyncio
class TestListAutomationsDB:
    """list_automations should read from AutomationRepository."""

    async def test_returns_automations(self):
        from src.tools.ha_tools import list_automations

        mock_repo = AsyncMock()
        mock_repo.list_all = AsyncMock(return_value=[
            _mock_automation("automation.sunset", "Sunset Lights", "on", True),
            _mock_automation("automation.motion", "Motion Lights", "off", False),
        ])

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.AutomationRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await list_automations.ainvoke({})

        assert "Sunset Lights" in result
        assert "Motion Lights" in result


def _mock_script(entity_id: str, alias: str, sequence: list | None = None, fields: dict | None = None) -> MagicMock:
    """Create a mock Script."""
    s = MagicMock()
    s.entity_id = entity_id
    s.alias = alias
    s.sequence = sequence
    s.fields = fields
    return s


@pytest.mark.asyncio
class TestGetAutomationConfigDB:
    """get_automation_config should return YAML from the DB."""

    async def test_returns_yaml_when_config_exists(self):
        from src.tools.ha_tools import get_automation_config

        config = {
            "id": "sunset_lights",
            "alias": "Sunset Lights",
            "trigger": [{"platform": "sun", "event": "sunset"}],
            "action": [{"service": "light.turn_on"}],
        }
        auto = _mock_automation("automation.sunset_lights", "Sunset Lights", "on", True)
        auto.config = config
        auto.ha_automation_id = "sunset_lights"

        mock_repo = AsyncMock()
        mock_repo.get_by_entity_id = AsyncMock(return_value=auto)

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.AutomationRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_automation_config.ainvoke({"entity_id": "automation.sunset_lights"})

        assert "trigger" in result
        assert "sunset" in result
        mock_repo.get_by_entity_id.assert_called_once_with("automation.sunset_lights")

    async def test_returns_message_when_config_is_null(self):
        from src.tools.ha_tools import get_automation_config

        auto = _mock_automation("automation.broken", "Broken", "on", False)
        auto.config = None

        mock_repo = AsyncMock()
        mock_repo.get_by_entity_id = AsyncMock(return_value=auto)

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.AutomationRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_automation_config.ainvoke({"entity_id": "automation.broken"})

        assert "discovery" in result.lower() or "sync" in result.lower()

    async def test_returns_not_found_when_missing(self):
        from src.tools.ha_tools import get_automation_config

        mock_repo = AsyncMock()
        mock_repo.get_by_entity_id = AsyncMock(return_value=None)

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.AutomationRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_automation_config.ainvoke({"entity_id": "automation.nonexist"})

        assert "not found" in result.lower()


@pytest.mark.asyncio
class TestGetScriptConfigDB:
    """get_script_config should return YAML from the DB."""

    async def test_returns_yaml_when_sequence_exists(self):
        from src.tools.ha_tools import get_script_config

        sequence = [
            {"service": "light.turn_on", "data": {"brightness": 255}},
            {"service": "media_player.turn_on"},
        ]
        script = _mock_script("script.movie_mode", "Movie Mode", sequence=sequence)

        mock_repo = AsyncMock()
        mock_repo.get_by_entity_id = AsyncMock(return_value=script)

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.ScriptRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_script_config.ainvoke({"entity_id": "script.movie_mode"})

        assert "light.turn_on" in result
        assert "brightness" in result
        mock_repo.get_by_entity_id.assert_called_once_with("script.movie_mode")

    async def test_returns_message_when_sequence_is_null(self):
        from src.tools.ha_tools import get_script_config

        script = _mock_script("script.broken", "Broken", sequence=None)

        mock_repo = AsyncMock()
        mock_repo.get_by_entity_id = AsyncMock(return_value=script)

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.ScriptRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_script_config.ainvoke({"entity_id": "script.broken"})

        assert "discovery" in result.lower() or "sync" in result.lower()

    async def test_returns_not_found_when_missing(self):
        from src.tools.ha_tools import get_script_config

        mock_repo = AsyncMock()
        mock_repo.get_by_entity_id = AsyncMock(return_value=None)

        with (
            patch("src.tools.ha_tools.get_session") as mock_get_session,
            patch("src.tools.ha_tools.ScriptRepository", return_value=mock_repo),
        ):
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_script_config.ainvoke({"entity_id": "script.nonexist"})

        assert "not found" in result.lower()
