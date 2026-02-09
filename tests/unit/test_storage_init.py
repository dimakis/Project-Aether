"""Unit tests for src/storage/__init__.py.

Tests get_engine, get_session_factory, get_session, close_db.

The unit conftest autouse fixture guards get_engine/get_session/etc.
To test the REAL implementations of these functions without hitting a
DB, we temporarily restore the originals and mock the low-level
SQLAlchemy factories (create_async_engine, async_sessionmaker).
"""

import importlib
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _reload_storage():
    """Reload the storage module to get pristine functions."""
    import src.storage as mod

    # Save the guard functions that conftest installed
    guards = {
        "get_engine": mod.get_engine,
        "get_session_factory": mod.get_session_factory,
        "get_session": mod.get_session,
    }

    # Reset singletons
    mod._engine = None
    mod._session_factory = None
    mod._init_lock = threading.Lock()

    # Reload to get the real implementations
    importlib.reload(mod)
    real = {
        "get_engine": mod.get_engine,
        "get_session_factory": mod.get_session_factory,
        "get_session": mod.get_session,
        "close_db": mod.close_db,
        "init_db": mod.init_db,
    }

    # Restore the guards (conftest expects them)
    mod.get_engine = guards["get_engine"]
    mod.get_session_factory = guards["get_session_factory"]
    mod.get_session = guards["get_session"]

    return real


@pytest.fixture
def real_funcs():
    """Get real storage functions bypassing the DB guard."""
    funcs = _reload_storage()
    yield funcs
    # Cleanup: reset singletons
    import src.storage as mod

    mod._engine = None
    mod._session_factory = None


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.database_url = "postgresql+asyncpg://test:test@localhost/test"
    s.database_pool_size = 5
    s.database_max_overflow = 10
    s.database_pool_timeout = 30
    s.debug = False
    return s


class TestGetEngine:
    """Tests for get_engine."""

    def test_creates_engine(self, real_funcs, mock_settings):
        import src.storage as mod

        mock_engine = MagicMock()
        mod._engine = None  # ensure fresh

        with (
            patch("src.storage.get_settings", return_value=mock_settings),
            patch("src.storage.create_async_engine", return_value=mock_engine),
        ):
            engine = real_funcs["get_engine"]()

        assert engine is mock_engine

    def test_returns_same_instance(self, real_funcs, mock_settings):
        import src.storage as mod

        mock_engine = MagicMock()
        mod._engine = None

        with (
            patch("src.storage.get_settings", return_value=mock_settings),
            patch("src.storage.create_async_engine", return_value=mock_engine),
        ):
            engine1 = real_funcs["get_engine"]()
            engine2 = real_funcs["get_engine"]()

        assert engine1 is engine2

    def test_uses_provided_settings(self, real_funcs, mock_settings):
        import src.storage as mod

        mock_engine = MagicMock()
        mod._engine = None

        with patch("src.storage.create_async_engine", return_value=mock_engine) as mock_create:
            real_funcs["get_engine"](settings=mock_settings)

        mock_create.assert_called_once()
        assert mock_create.call_args[0][0] == str(mock_settings.database_url)


class TestGetSessionFactory:
    """Tests for get_session_factory."""

    def test_creates_factory(self, real_funcs, mock_settings):
        import src.storage as mod

        mock_engine = MagicMock()
        mock_factory = MagicMock()
        mod._engine = None
        mod._session_factory = None

        with (
            patch("src.storage.get_engine", return_value=mock_engine),
            patch("src.storage.async_sessionmaker", return_value=mock_factory),
        ):
            factory = real_funcs["get_session_factory"]()

        assert factory is mock_factory

    def test_returns_same_instance(self, real_funcs, mock_settings):
        import src.storage as mod

        mock_engine = MagicMock()
        mock_factory = MagicMock()
        mod._engine = None
        mod._session_factory = None

        with (
            patch("src.storage.get_engine", return_value=mock_engine),
            patch("src.storage.async_sessionmaker", return_value=mock_factory),
        ):
            f1 = real_funcs["get_session_factory"]()
            f2 = real_funcs["get_session_factory"]()

        assert f1 is f2


class TestGetSession:
    """Tests for get_session async context manager."""

    async def test_yields_session(self, real_funcs):
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("src.storage.get_session_factory", return_value=mock_factory):
            async with real_funcs["get_session"]() as session:
                assert session is mock_session

        mock_session.close.assert_called_once()

    async def test_closes_on_exception(self, real_funcs):
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("src.storage.get_session_factory", return_value=mock_factory):
            with pytest.raises(ValueError):
                async with real_funcs["get_session"]() as session:
                    raise ValueError("test error")

        mock_session.close.assert_called_once()


class TestCloseDB:
    """Tests for close_db."""

    async def test_close_disposes_engine(self, real_funcs):
        import src.storage as mod

        mock_engine = AsyncMock()
        mod._engine = mock_engine
        mod._session_factory = MagicMock()

        await real_funcs["close_db"]()

        mock_engine.dispose.assert_called_once()
        assert mod._engine is None
        assert mod._session_factory is None

    async def test_close_no_engine(self, real_funcs):
        import src.storage as mod

        mod._engine = None
        await real_funcs["close_db"]()  # Should not raise
