"""Unit tests for src/tracing/context.py (session context management)."""

from src.tracing.context import (
    clear_session,
    get_session_id,
    session_context,
    set_session_id,
    start_session,
)


class TestStartSession:
    def test_returns_uuid(self):
        sid = start_session()
        assert isinstance(sid, str)
        assert len(sid) == 36  # UUID format

    def test_sets_context(self):
        sid = start_session()
        assert get_session_id() == sid


class TestGetSessionId:
    def test_returns_none_by_default(self):
        clear_session()
        assert get_session_id() is None


class TestSetSessionId:
    def test_sets_custom_id(self):
        set_session_id("custom-123")
        assert get_session_id() == "custom-123"
        clear_session()


class TestClearSession:
    def test_clears_session(self):
        start_session()
        clear_session()
        assert get_session_id() is None


class TestSessionContext:
    def test_creates_new_session(self):
        clear_session()
        with session_context() as sid:
            assert isinstance(sid, str)
            assert get_session_id() == sid
        assert get_session_id() is None

    def test_uses_provided_id(self):
        clear_session()
        with session_context(session_id="my-session") as sid:
            assert sid == "my-session"
            assert get_session_id() == "my-session"

    def test_restores_previous(self):
        set_session_id("outer")
        with session_context(session_id="inner"):
            assert get_session_id() == "inner"
        assert get_session_id() == "outer"
        clear_session()

    def test_restores_on_exception(self):
        set_session_id("outer")
        try:
            with session_context(session_id="inner"):
                raise ValueError("test")
        except ValueError:
            pass
        assert get_session_id() == "outer"
        clear_session()
