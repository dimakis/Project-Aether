"""Unit-test conftest — DB isolation safety net.

Provides an ``autouse`` fixture that prevents any unit test from
accidentally opening a real Postgres connection.  This catches the
class of bugs where ``create_app()`` or ``get_session()`` is called
without mocking the database layer first.

Constitution Principle V: "Tests MUST be fast, isolated, and deterministic.
Use mocking/stubbing for external dependencies."

The approach:
1. Before every unit test, reset the storage module's global engine and
   session-factory singletons so they start from scratch.
2. Monkey-patch ``get_engine()`` to raise immediately if any code path
   attempts a real DB connection.

Individual tests that intentionally need DB access (e.g. integration tests)
live in ``tests/integration/`` and are unaffected.
"""

from __future__ import annotations

import pytest

import src.storage as _storage_mod


def _install_db_guard(monkeypatch: pytest.MonkeyPatch | None = None) -> None:
    """Install guard functions that prevent real DB access in unit tests."""

    def _guarded_get_engine(settings=None):
        raise RuntimeError(
            "Unit test attempted a real DB connection via get_engine(). "
            "Mock the database dependency or use tests/integration/ for DB tests."
        )

    def _guarded_get_session_factory(settings=None):
        raise RuntimeError(
            "Unit test attempted a real DB connection via get_session_factory(). "
            "Mock the database dependency or use tests/integration/ for DB tests."
        )

    def _guarded_get_session():
        raise RuntimeError(
            "Unit test attempted a real DB connection via get_session(). "
            "Mock the database dependency or use tests/integration/ for DB tests."
        )

    if monkeypatch:
        monkeypatch.setattr(_storage_mod, "get_engine", _guarded_get_engine)
        monkeypatch.setattr(_storage_mod, "get_session_factory", _guarded_get_session_factory)
        monkeypatch.setattr(_storage_mod, "get_session", _guarded_get_session)
    else:
        _storage_mod.get_engine = _guarded_get_engine
        _storage_mod.get_session_factory = _guarded_get_session_factory
        _storage_mod.get_session = _guarded_get_session


def pytest_configure() -> None:
    """Install DB guards before unit test modules are imported."""
    _storage_mod._engine = None  # type: ignore[attr-defined]
    _storage_mod._session_factory = None  # type: ignore[attr-defined]
    _install_db_guard()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent unit tests from reaching a real Postgres connection.

    Resets storage singletons and replaces ``get_engine`` with a guard
    that raises immediately.  Any test that accidentally triggers a DB
    call will get a clear error instead of hanging forever.
    """
    # 1. Reset the module-level singletons so tests don't see stale engines
    #    from a previous test that may have called create_async_engine.
    monkeypatch.setattr(_storage_mod, "_engine", None)
    monkeypatch.setattr(_storage_mod, "_session_factory", None)

    # 2. Patch storage accessors to raise on accidental invocation.
    _install_db_guard(monkeypatch)
