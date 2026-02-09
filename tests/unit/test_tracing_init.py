"""Unit tests for src/tracing/__init__.py lazy-import machinery."""

import pytest

import src.tracing as tracing_pkg


class TestLazyImport:
    def test_getattr_valid_export(self):
        # Access an export that should work
        func = tracing_pkg.start_session
        assert callable(func)

    def test_getattr_invalid_raises(self):
        with pytest.raises(AttributeError, match="no attribute"):
            _ = tracing_pkg.nonexistent_symbol

    def test_dir_lists_exports(self):
        names = dir(tracing_pkg)
        assert "init_mlflow" in names
        assert "start_session" in names

    def test_cache_hit(self):
        # First access populates cache
        _ = tracing_pkg.get_session_id
        # Second access should come from cache
        func = tracing_pkg.get_session_id
        assert callable(func)
