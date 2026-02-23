"""Tests for dual-mode agent invocation (Phase 3).

When DEPLOYMENT_MODE=monolith, agents are instantiated in-process.
When DEPLOYMENT_MODE=distributed, agents are called via A2ARemoteClient.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.state import AnalysisState


class TestResolveAgentInvoker:
    """resolve_agent_invoker() returns local or remote based on mode."""

    def test_monolith_returns_local_agent(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_settings:
            mock_settings.return_value.deployment_mode = "monolith"
            invoker = resolve_agent_invoker("energy_analyst")

        assert invoker.mode == "local"

    def test_distributed_returns_remote_client(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_settings:
            mock_settings.return_value.deployment_mode = "distributed"
            mock_settings.return_value.ds_service_url = "http://ds:8000"
            invoker = resolve_agent_invoker("energy_analyst")

        assert invoker.mode == "remote"

    def test_monolith_invoker_calls_agent_directly(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_settings:
            mock_settings.return_value.deployment_mode = "monolith"
            invoker = resolve_agent_invoker("energy_analyst")

        assert invoker.agent_cls is not None

    def test_distributed_invoker_has_service_url(self):
        from src.agents.dual_mode import resolve_agent_invoker

        with patch("src.settings.get_settings") as mock_settings:
            mock_settings.return_value.deployment_mode = "distributed"
            mock_settings.return_value.ds_service_url = "http://ds:8000"
            invoker = resolve_agent_invoker("energy_analyst")

        assert invoker.service_url == "http://ds:8000"


class TestAgentInvokerExecution:
    """AgentInvoker.invoke() dispatches correctly in both modes."""

    @pytest.mark.asyncio()
    async def test_local_invoke_creates_and_calls_agent(self):
        from src.agents.dual_mode import AgentInvoker

        mock_agent_cls = type("MockAgent", (), {"__init__": lambda self: None})
        mock_agent_cls.__call__ = lambda self: self

        invoker = AgentInvoker(mode="local", agent_cls=mock_agent_cls)

        with patch.object(
            invoker, "_invoke_local", new_callable=AsyncMock, return_value={"result": "ok"}
        ):
            result = await invoker.invoke(AnalysisState())

        assert result == {"result": "ok"}

    @pytest.mark.asyncio()
    async def test_remote_invoke_calls_a2a_client(self):
        from src.agents.dual_mode import AgentInvoker

        invoker = AgentInvoker(mode="remote", service_url="http://ds:8000")

        with patch("src.agents.a2a_client.A2ARemoteClient") as mock_client_cls:
            mock_client_cls.return_value.invoke = AsyncMock(return_value={"result": "remote"})
            result = await invoker.invoke(AnalysisState())

        assert result == {"result": "remote"}
