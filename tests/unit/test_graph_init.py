"""Unit tests for src/graph/__init__.py helper functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetWorkflow:
    def test_delegates_to_workflows_module(self):
        with patch("src.graph.workflows.get_workflow", return_value="mock_wf") as mock:
            from src.graph import get_workflow

            result = get_workflow("discovery", some_kwarg=42)

            mock.assert_called_once_with("discovery", some_kwarg=42)
            assert result == "mock_wf"


class TestRunDiscoveryWorkflow:
    @pytest.mark.asyncio
    async def test_delegates_to_workflows_module(self):
        with patch(
            "src.graph.workflows.run_discovery_workflow",
            new_callable=AsyncMock,
            return_value={"status": "done"},
        ) as mock:
            from src.graph import run_discovery_workflow

            result = await run_discovery_workflow(zone_id="z1")

            mock.assert_called_once_with(zone_id="z1")
            assert result == {"status": "done"}


class TestGetLLM:
    def test_returns_configured_llm(self):
        settings = MagicMock()
        settings.llm_api_key.get_secret_value.return_value = "sk-test"
        settings.llm_model = "gpt-4o"

        with patch("src.graph.get_settings", return_value=settings):
            from src.graph import get_llm

            llm = get_llm(temperature=0.5)

        assert llm is not None

    def test_raises_on_missing_api_key(self):
        settings = MagicMock()
        settings.llm_api_key.get_secret_value.return_value = ""

        with patch("src.graph.get_settings", return_value=settings):
            from src.graph import get_llm

            with pytest.raises(ValueError, match="LLM_API_KEY not configured"):
                get_llm()


class TestCreateGraph:
    def test_creates_state_graph(self):
        from pydantic import BaseModel

        from src.graph import create_graph

        class FakeState(BaseModel):
            messages: list[str] = []

        graph = create_graph(FakeState)
        assert graph is not None
