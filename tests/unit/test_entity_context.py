"""Unit tests for entity_context — session-per-task concurrency.

Verifies that _build_base_context uses independent sessions (not a shared one)
so asyncio.gather works without InvalidConcurrentOperationError,
and that mentioned entities use the batch get_by_entity_ids method.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.architect.entity_context import (
    _build_base_context,
    _invalidate_entity_context_cache,
    get_entity_context,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the entity context cache before each test."""
    _invalidate_entity_context_cache()
    yield
    _invalidate_entity_context_cache()


def _make_mock_session_factory():
    """Create a mock session factory that returns separate session mocks.

    Each call to factory() returns a fresh AsyncMock session so we can
    verify that gather tasks get independent sessions.
    """
    sessions_created: list[AsyncMock] = []

    def factory():
        session = AsyncMock()
        session.execute = AsyncMock()
        session.close = AsyncMock()
        sessions_created.append(session)
        return session

    return factory, sessions_created


class TestBuildBaseContextUsesSeparateSessions:
    """_build_base_context must create independent sessions per gather task."""

    @pytest.mark.asyncio
    async def test_creates_multiple_sessions(self):
        """Each parallel query gets its own session (not a shared one)."""
        factory, sessions_created = _make_mock_session_factory()

        # Mock the repository calls to return realistic data
        with patch(
            "src.agents.architect.entity_context.get_session_factory",
            return_value=factory,
        ):
            # Set up each session to return plausible data
            # Sessions are created on-demand by _query(), so we need to
            # patch the repos to return data through whatever session they get.
            with (
                patch("src.agents.architect.entity_context.EntityRepository") as MockEntityRepo,
                patch("src.agents.architect.entity_context.AreaRepository") as MockAreaRepo,
                patch("src.agents.architect.entity_context.DeviceRepository") as MockDeviceRepo,
                patch("src.agents.architect.entity_context.ServiceRepository") as MockServiceRepo,
            ):
                # get_domain_counts returns a dict
                MockEntityRepo.return_value.get_domain_counts = AsyncMock(
                    return_value={"light": 5, "sensor": 10}
                )
                MockAreaRepo.return_value.list_all = AsyncMock(return_value=[])
                MockDeviceRepo.return_value.list_all = AsyncMock(return_value=[])
                MockServiceRepo.return_value.list_all = AsyncMock(return_value=[])
                # list_by_domains for detailed entities
                MockEntityRepo.return_value.list_by_domains = AsyncMock(return_value={})

                await _build_base_context()

            # At least 4 sessions should have been created (one per gather task)
            # plus potentially one more for list_by_domains
            assert len(sessions_created) >= 4, (
                f"Expected at least 4 independent sessions, got {len(sessions_created)}"
            )
            # Every session should have been closed
            for i, s in enumerate(sessions_created):
                s.close.assert_awaited_once(), f"Session {i} was not closed"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_counts(self):
        """Returns None when get_domain_counts returns empty."""
        factory, _ = _make_mock_session_factory()

        with patch(
            "src.agents.architect.entity_context.get_session_factory",
            return_value=factory,
        ):
            with (
                patch("src.agents.architect.entity_context.EntityRepository") as MockEntityRepo,
                patch("src.agents.architect.entity_context.AreaRepository") as MockAreaRepo,
                patch("src.agents.architect.entity_context.DeviceRepository") as MockDeviceRepo,
                patch("src.agents.architect.entity_context.ServiceRepository") as MockServiceRepo,
            ):
                MockEntityRepo.return_value.get_domain_counts = AsyncMock(return_value={})
                MockAreaRepo.return_value.list_all = AsyncMock(return_value=[])
                MockDeviceRepo.return_value.list_all = AsyncMock(return_value=[])
                MockServiceRepo.return_value.list_all = AsyncMock(return_value=[])

                result = await _build_base_context()

            assert result is None


class TestGetEntityContextMentionedEntities:
    """get_entity_context uses batch lookup for mentioned entities."""

    @pytest.mark.asyncio
    async def test_uses_batch_get_by_entity_ids(self):
        """Mentioned entities are fetched via get_by_entity_ids, not individual queries."""
        mock_state = MagicMock()
        mock_state.entities_mentioned = ["light.a", "light.b"]

        mock_e1 = MagicMock(entity_id="light.a", name="A", state="on")
        mock_e2 = MagicMock(entity_id="light.b", name="B", state="off")

        factory, _sessions = _make_mock_session_factory()

        with (
            patch(
                "src.agents.architect.entity_context.get_session_factory",
                return_value=factory,
            ),
            patch("src.agents.architect.entity_context.EntityRepository") as MockEntityRepo,
            patch("src.agents.architect.entity_context.AreaRepository") as MockAreaRepo,
            patch("src.agents.architect.entity_context.DeviceRepository") as MockDeviceRepo,
            patch("src.agents.architect.entity_context.ServiceRepository") as MockServiceRepo,
        ):
            # Base context returns something
            MockEntityRepo.return_value.get_domain_counts = AsyncMock(return_value={"light": 2})
            MockAreaRepo.return_value.list_all = AsyncMock(return_value=[])
            MockDeviceRepo.return_value.list_all = AsyncMock(return_value=[])
            MockServiceRepo.return_value.list_all = AsyncMock(return_value=[])
            MockEntityRepo.return_value.list_by_domains = AsyncMock(return_value={})

            # Batch lookup for mentioned entities
            MockEntityRepo.return_value.get_by_entity_ids = AsyncMock(
                return_value=[mock_e1, mock_e2]
            )

            context, warning = await get_entity_context(mock_state)

        assert context is not None
        assert warning is None
        assert "light.a" in context
        assert "light.b" in context
        # get_by_entity_ids should have been called (not individual get_by_entity_id)
        MockEntityRepo.return_value.get_by_entity_ids.assert_awaited_once_with(
            ["light.a", "light.b"]
        )

    @pytest.mark.asyncio
    async def test_no_session_param_required(self):
        """get_entity_context no longer requires a session parameter."""
        import inspect

        sig = inspect.signature(get_entity_context)
        params = list(sig.parameters.keys())
        # Should only have 'state', no 'session'
        assert "session" not in params, "get_entity_context should not require a session parameter"
        assert "state" in params
