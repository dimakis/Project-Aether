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

    def test_inherits_parent_session_via_get_session_id(self):
        """Nested session_context(get_session_id()) reuses parent session."""
        clear_session()
        with session_context(session_id="parent-session") as outer_sid:
            assert outer_sid == "parent-session"
            # Simulate what nested workflows should do: pass get_session_id()
            with session_context(session_id=get_session_id()) as inner_sid:
                assert inner_sid == "parent-session"
                assert get_session_id() == "parent-session"
            # After inner exits, outer is restored
            assert get_session_id() == "parent-session"
        clear_session()

    def test_creates_new_session_when_no_parent_exists(self):
        """session_context(get_session_id()) creates new session when no parent."""
        clear_session()
        assert get_session_id() is None
        # get_session_id() returns None, so session_context(None) creates new
        with session_context(session_id=get_session_id()) as sid:
            assert isinstance(sid, str)
            assert len(sid) == 36  # UUID format
            assert get_session_id() == sid
        clear_session()

    def test_deeply_nested_sessions_all_share_parent(self):
        """Triple-nested session_context all share the same parent session."""
        clear_session()
        with session_context(session_id="root") as root_sid:
            with session_context(session_id=get_session_id()) as mid_sid:
                with session_context(session_id=get_session_id()) as inner_sid:
                    assert inner_sid == "root"
                assert mid_sid == "root"
            assert root_sid == "root"
        clear_session()
