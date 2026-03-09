"""Unit tests for lazy __init__.py __getattr__ and __dir__ across modules.

Covers the AttributeError path and __dir__() return for modules that use
lazy imports for deferred loading.
"""

import importlib

import pytest


@pytest.mark.parametrize(
    "module_path",
    [
        "src.tools",
        "src.agents",
        "src.dal",
        "src.ha",
        "src.graph.nodes",
        "src.graph.state",
        "src.graph.workflows",
        "src.llm",
        "src.diagnostics",
    ],
)
def test_lazy_init_dir_returns_non_empty_list(module_path: str) -> None:
    """dir(module) returns a non-empty list of exported names."""
    module = importlib.import_module(module_path)
    result = dir(module)
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.parametrize(
    "module_path",
    [
        "src.tools",
        "src.agents",
        "src.dal",
        "src.ha",
        "src.graph.nodes",
        "src.graph.state",
        "src.graph.workflows",
        "src.llm",
        "src.diagnostics",
    ],
)
def test_lazy_init_getattr_raises_for_nonexistent(module_path: str) -> None:
    """Accessing nonexistent attribute raises AttributeError (exercises __getattr__)."""
    module = importlib.import_module(module_path)
    with pytest.raises(AttributeError, match="has no attribute 'nonexistent_attr_xyz'"):
        _ = module.nonexistent_attr_xyz


@pytest.mark.parametrize(
    "module_path,export_name",
    [
        ("src.tools", "get_all_tools"),
        ("src.agents", "BaseAgent"),
        ("src.dal", "AreaRepository"),
        ("src.ha", "HAClient"),
        ("src.graph.nodes", "run_discovery_node"),
        ("src.graph.state", "BaseState"),
        ("src.graph.workflows", "get_workflow"),
        ("src.llm", "get_llm"),
        ("src.diagnostics", "parse_error_log"),
    ],
)
def test_lazy_init_valid_export_cached(module_path: str, export_name: str) -> None:
    """Accessing valid export twice returns same object (exercises cache path)."""
    module = importlib.import_module(module_path)
    first = getattr(module, export_name)
    second = getattr(module, export_name)
    assert first is second
